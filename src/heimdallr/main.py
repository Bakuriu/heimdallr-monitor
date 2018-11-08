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


def run(interval, pid, resources, write_header, backup_bad_output_dir, plugins):
    """Mainloop that calls the `monitor_*` function and then sleeps for `interval` seconds."""
    config = {'backup_bad_output_dir': backup_bad_output_dir, 'pid': pid}
    resources_instances = [plugins[resource].create_resource(logfile) for resource, logfile in resources]

    with suppress(KeyboardInterrupt):
        while pid is None or _pid_exists(pid):
            for resource in resources_instances:
                resource.monitor(config, header=write_header)
            write_header = False
            time.sleep(interval)


def _make_parser():
    parent_parser = argparse.ArgumentParser(add_help=False)
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


def monitor(args, plugins):
    run(
        interval=args.interval,
        resources=args.resources,
        pid=args.pid,
        write_header=args.write_header,
        backup_bad_output_dir=args.backup_bad_output_dir,
        plugins=plugins,
    )


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


def _middle_process(tmp_filename, args):
    # setsid needed to make sure we don't get killed when our parent dies.
    os.setsid()
    os.umask(0)
    # spawn the background task
    proc = _run_subprocess(args.cmdline, args.stdin, args.stdout, args.stderr)
    proc_pid = proc.pid
    # store the pid of the background task in the temporary file
    with open(tmp_filename, 'wb') as f:
        f.write(str(proc_pid).encode('ascii') + b'\n')
    # quit this process immediately. No cleanup (the file above should have already flushed everything.
    os._exit(0)


def launch(args, plugins):
    """Spawns a background process and then monitors it.

    If `args.keep_alive` is `True`, then it ensures that the background task is not killed when this process exits,
    while if `args.keep_alive` is `False` it ensures that the background task is killed when this process exits.

    """
    if args.keep_alive:
        try:
            # make sure that monitor can be killed without killing the background task
            # to achieve this we have to fork twice, so that the background task gets inherited by
            # the process 1 (either init or systemd or whatever).
            # We need its pid so we create a temporary file where the middle-process writes the task's pid.
            with name_of_temporary_file(args.verbose) as tmp_filename:
                cpid = os.fork()
                if cpid == 0:
                    # we are the child process
                    _middle_process(tmp_filename, args)
                else:
                    # we are the original Heimdallr process. Wait for the middle process to die
                    os.waitpid(cpid, 0)
                    # get the pid of the background process we have to monitor.
                    with open(tmp_filename) as pid_file:
                        args.pid = int(pid_file.read())
                        if args.verbose:
                            sys.stderr.write('Background task has PID: {}\n'.format(args.pid))
        except Exception as e:
            if hasattr(args, 'pid'):
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
        proc = _run_subprocess(args.cmdline, args.stdin, args.stdout, args.stderr, preexec_fn=os.setsid)
        args.pid = proc.pid
        kill_gently = create_gentle_killer(proc, args.verbose)
        victim_id = os.getpgid(proc.pid)
        atexit.register(kill_gently, victim_id)
        signal.signal(signal.SIGTERM, lambda _: kill_gently(victim_id))
        signal.signal(signal.SIGABRT, lambda _: kill_gently(victim_id))

    monitor(args, plugins)


def main():
    from . import plugins as builtin_plugins
    plugins = {mod_name: getattr(builtin_plugins, mod_name) for mod_name in builtin_plugins.__all__}
    try:
        import pkg_resources
    except ImportError:
        # no setuptools. Plugins are not supported.
        pass
    else:
        for entry_point in pkg_resources.iter_entry_points('heimdallr.plugins'):
            try:
                plugins[entry_point.name] = entry_point.load()
            except ImportError:
                pass

    for mod in list(plugins.values()):
        for alias in getattr(mod, 'aliases', ()):
            plugins[alias] = mod

    parser = _make_parser()
    args = parser.parse_args()
    if args.command == 'launch':
        launch(args, plugins)
    elif args.command == 'monitor':
        monitor(args, plugins)
    else:
        parser.error('You must select a sub-command to run.')


if __name__ == '__main__':
    main()
