#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import atexit
import signal
import argparse
import subprocess
import configparser
from contextlib import suppress

from .utils import _pid_exists, name_of_temporary_file, create_gentle_killer


def parse_interval(interval):
    """Parse a time interval into the equivalent number of seconds:

        >>> parse_interval("5s")
        5
        >>> parse_interval("2m")
        120
        >>> parse_interval("1.5h")
        5472.0

    """
    match = re.fullmatch(r'(\d+(?:\.\d+)?)([smh])', interval)
    return float(match[1]) * ({'s': 1, 'm': 60, 'h': 60 * 60}[match[2]])


def parse_configuration(config_file):
    parser = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    parser.read_file(config_file)
    configuration = {}
    resources = parser.sections()
    for resource in resources:
        config = {key: parser.get(resource, key) for key in parser[resource]}
        if 'logfile' not in config:
            raise ValueError('You must specify a logfile for resource: {!r}'.format(resource))
        configuration['resource'] = config
    return configuration


def run(configuration, global_configuration, plugins):
    """Mainloop that calls the `monitor_*` function and then sleeps for `interval` seconds."""
    resources_instances = []
    for resource, config in configuration.items():
        resources_instances.append((plugins[resource].create_resource(config['logfile']), config))

    pid = global_configuration['pid']
    write_header = global_configuration['write_header']
    interval = global_configuration['interval']

    with suppress(KeyboardInterrupt):
        while pid is None or _pid_exists(pid):
            for resource, config in resources_instances:
                resource.monitor(config, header=write_header)
            write_header = False
            time.sleep(interval)


def _make_parser():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('-c', '--config', type=argparse.FileType('r'), default=None,
                               help='A configuration file.')
    parent_parser.add_argument('-i', '--interval', type=parse_interval, default='30s',
                               help='Interval between measurements.\nSyntax is: \d+(\.\d+)?(s|m|h).')
    parent_parser.add_argument('-r', '--resource', nargs=2, metavar=('NAME', 'LOGFILE'), action='append', default=[],
                               dest='resources', help='Monitor the given resource')
    parent_parser.add_argument('-q', '--quiet', action='store_false', dest='verbose',
                               help="Don't write error messages to stdout")
    parent_parser.add_argument('--no-header', action='store_false', dest='write_header',
                               help='Do not write the header to the log files when starting.')
    parent_parser.add_argument('-b', '--backup-bad-output-dir', default=None, metavar='DIR',
                               help='Directory where the backup outputs will be saved.')

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    monitor_parser = subparsers.add_parser('monitor', parents=[parent_parser])
    monitor_parser.add_argument('-p', '--pid', type=int, help='Pid of the process to monitor.')

    launch_parser = subparsers.add_parser('launch', parents=[parent_parser])
    launch_parser.add_argument('-o', '--output', dest='stdout', default='-', help='Subprocess stdout')
    launch_parser.add_argument('-e', '--error', dest='stderr', default='-', help='Subprocess stderr')
    launch_parser.add_argument('-I', '--input', dest='stdin', default='-', help='Subprocess stdin')
    launch_parser.add_argument('--keep-alive', action='store_true', help='Keep running task when monitor process exits')
    launch_parser.add_argument('cmdline', nargs='+', metavar='CMD', help='The command to launch and monitor.')

    return parser


def monitor(configuration, global_configuration, plugins):
    run(configuration, global_configuration, plugins)


def _run_subprocess(cmdline, in_filename, out_filename, err_filename, preexec_fn=lambda: None):
    in_filename = argparse.FileType('rb')(in_filename)
    outer = argparse.FileType('wb')
    return subprocess.Popen(
        cmdline,
        stdin=in_filename,
        stdout=outer(out_filename),
        stderr=outer(err_filename),
        preexec_fn=preexec_fn
    )


def _middle_process(tmp_filename, config):
    # setsid needed to make sure we don't get killed when our parent dies.
    os.setsid()
    os.umask(0)
    # spawn the background task
    proc = _run_subprocess(config['cmdline'], config['stdin'], config['stdout'], config['stderr'])
    proc_pid = proc.pid
    # store the pid of the background task in the temporary file
    with open(tmp_filename, 'wb') as f:
        f.write(str(proc_pid).encode('ascii') + b'\n')
    # quit this process immediately. No cleanup (the file above should have already flushed everything.
    os._exit(0)


def launch(configuration, global_configuration, plugins):
    """Spawns a background process and then monitors it.

    If `args.keep_alive` is `True`, then it ensures that the background task is not killed when this process exits,
    while if `args.keep_alive` is `False` it ensures that the background task is killed when this process exits.

    """
    verbose = global_configuration['verbose']
    if global_configuration['keep_alive']:
        try:
            # make sure that monitor can be killed without killing the background task
            # to achieve this we have to fork twice, so that the background task gets inherited by
            # the process 1 (either init or systemd or whatever).
            # We need its pid so we create a temporary file where the middle-process writes the task's pid.
            with name_of_temporary_file(verbose) as tmp_filename:
                cpid = os.fork()
                if cpid == 0:
                    # we are the child process
                    _middle_process(tmp_filename, global_configuration)
                else:
                    # we are the original Heimdallr process. Wait for the middle process to die
                    os.waitpid(cpid, 0)
                    # get the pid of the background process we have to monitor.
                    with open(tmp_filename) as pid_file:
                        global_configuration['pid'] = int(pid_file.read())
                        if verbose:
                            sys.stderr.write('Background task has PID: {}\n'.format(global_configuration['pid']))
        except Exception as e:
            if 'pid' in global_configuration:
                # probably an issue with deleting the temporary file?
                sys.stderr.write('Error after starting background task.\n{0.__class__.__name__}: {0}'.format(e))
            else:
                msg = (
                    "Error during or after starting the background task. It may or may not have started successfully.\n"
                    "{0.__class__.__name__}: {0}\n"
                )
                sys.stderr.write(msg.format(e))
                sys.exit(1)
    else:
        # in this case we want to ensure that the background task gets killed with us.
        # we register an atexit function that kills it, first via SIGTERM and after 5 seconds SIGKILL.
        proc = _run_subprocess(
            global_configuration['cmdline'],
            global_configuration['stdin'],
            global_configuration['stdout'],
            global_configuration['stderr'],
            preexec_fn=os.setsid,
        )
        global_configuration['pid'] = proc.pid
        kill_gently = create_gentle_killer(proc, verbose)
        victim_id = os.getpgid(proc.pid)
        atexit.register(kill_gently, victim_id)
        signal.signal(signal.SIGTERM, lambda _: kill_gently(victim_id))
        signal.signal(signal.SIGABRT, lambda _: kill_gently(victim_id))

    monitor(configuration, global_configuration, plugins)


def main():
    plugins = load_plugins()

    parser = _make_parser()
    args = parser.parse_args()
    global_config = {
        'pid': args.pid,
        'backup_bad_output': args.backup_bad_output,
        'interval': args.interval,
        'write_header': args.write_header,
        'verbose': args.verbose,
    }
    if args.config is not None:
        configuration = parse_configuration(args.config)
        global_config_file = configuration.get('global_configuration', {})
        global_config.update(global_config_file)
    else:
        configuration = {}
        for resource, logfile in args.resources:
            configuration[resource] = {
                'logfile': logfile,
            }
    if args.command == 'launch':
        global_config.update({
            'keep_alive': args.keep_alive,
            'cmdline': args.cmdline,
            'stdin': args.stdin,
            'stdout': args.stdout,
            'stderr': args.stderr,
        })
        launch(configuration, global_config, plugins)
    elif args.command == 'monitor':
        monitor(configuration, global_config, plugins)
    else:
        parser.error('You must select a sub-command to run.')


def load_plugins():
    from . import plugins as builtin_plugins
    plugins = {mod_name: getattr(builtin_plugins, mod_name) for mod_name in builtin_plugins.__all__}
    try:
        import pkg_resources
        for entry_point in pkg_resources.iter_entry_points('heimdallr.plugins'):
            try:
                plugins[entry_point.name] = entry_point.load()
            except Exception:
                pass
    except ImportError:
        # no setuptools. Plugins are not supported.
        pass
    for mod in list(plugins.values()):
        for alias in getattr(mod, 'aliases', ()):
            plugins[alias] = mod
    return plugins


if __name__ == '__main__':
    main()
