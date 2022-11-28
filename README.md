# heimdallr-monitor

A simple monitoring script with only [`curio`](https://curio.readthedocs.io/en/latest/) as dependency.

Mostly to investigate a little bit of asynch programming with curio and the newer `await`/`async` syntax.

## Installation

1. Clone the repository:

    ```bash
    $ git clone https://github.com/Bakuriu/heimdallr-monitor
    ```

2. Go inside `heimdallr-monitor`

    ```bash
    $ cd heimdallr-monitor
    ```

3. Run install:

    ```bash
    $ python3 setup.py install
    ```
    
    If you prefer to install only for your current user add the `--user` switch:

    ```bash
    $ python3 setup.py install --user
    ```

## Execution

Heimdallr provides two commands: `monitor` and `launch`.

### Monitoring system or existing process

Using the command `monitor` it's possible to monitor an existing process or the whole system.

The syntax of the command is the following:

```
$ heimdallr monitor -h
usage: heimdallr monitor [-h] [-i INTERVAL] [-r NAME LOGFILE] [-q]
                         [--no-header] [-b DIR] [-p PID]

optional arguments:
  -h, --help            show this help message and exit
  -i INTERVAL, --interval INTERVAL
                        Interval between measurements. Syntax is:
                        \d+(\.\d+)?(s|m|h).
  -r NAME LOGFILE, --resource NAME LOGFILE
                        Monitor the given resource
  -q, --quiet           Don't write error messages to stdout
  --no-header           Do not write the header to the log files when
                        starting.
  -b DIR, --backup-bad-output-dir DIR
                        Directory where the backup outputs will be saved.
  -p PID, --pid PID     Pid of the process to monitor.
```

You can specify a resource to monitor using the `-r` / `--resource` option.
It takes a name of a resource, for example `gpu`, and the logfile where you wish to write
the data.


### Launching and monitoring a command

You can use `heimdallr` to launch and monitor a command from the start.
To do this use the `launch` command and provide the commandline to execute as
a single argument.

The syntax of `launch` is the following:

```
$ heimdallr launch -h
usage: heimdallr launch [-h] [-i INTERVAL] [-r NAME LOGFILE] [-q]
                        [--no-header] [-b DIR] [-o STDOUT] [-e STDERR]
                        [-I STDIN] [--keep-alive]
                        CMD [CMD ...]

positional arguments:
  CMD                   The command to launch and monitor.

optional arguments:
  -h, --help            show this help message and exit
  -i INTERVAL, --interval INTERVAL
                        Interval between measurements. Syntax is:
                        \d+(\.\d+)?(s|m|h).
  -r NAME LOGFILE, --resource NAME LOGFILE
                        Monitor the given resource
  -q, --quiet           Don't write error messages to stdout
  --no-header           Do not write the header to the log files when
                        starting.
  -b DIR, --backup-bad-output-dir DIR
                        Directory where the backup outputs will be saved.
  -o STDOUT, --output STDOUT
                        Subprocess stdout
  -e STDERR, --error STDERR
                        Subprocess stderr
  -I STDIN, --input STDIN
                        Subprocess stdin
  --keep-alive          Keep running task when monitor process exits

```

It has all the options of `monitor` but in addition you can control the `stdout`, `stderr` and `stdin`
of the subprocess launched.

Stopping the Heimdallr process will kill the task. If this is not the wanted behaviour
you can specify `--keep-alive` and Heimdallr will try its best to keep the task alive.
