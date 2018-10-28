# heimdallr-monitor

A simple monitoring script with no dependencies.

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
usage: heimdallr monitor [-h] [-i INTERVAL] [-g LOGFILE] [-t LOGFILE]
                         [-c LOGFILE] [-q] [-p PID]

optional arguments:
  -h, --help            show this help message and exit
  -i INTERVAL, --interval INTERVAL
                        Interval between measurements. Syntax is:
                        \d+(\.\d+)?(s|m|h).
  -g LOGFILE, --gpu LOGFILE
                        Monitor GPU usage
  -t LOGFILE, --temperatures LOGFILE
                        Monitor temperatures of CPU
  -c LOGFILE, --cpu LOGFILE, --cpu-and-ram LOGFILE
                        Monitor processes, CPU & RAM usage via top
  -q, --quiet           Don't write error messages to stdout
  -p PID, --pid PID     Pid of the process to monitor for CPU&GPU usage.
```

### Launching and monitoring a command

You can use `heimdallr` to launch and monitor a command from the start.
To do this use the `launch` command and provide the commandline to execute as
a single argument.

The syntax of `launch` is the following:

```
$ python3 heimdallr launch -h
usage: heimdallr launch [-h] [-i INTERVAL] [-g LOGFILE] [-t LOGFILE]
                        [-c LOGFILE] [-q] [-o OUTPUT] [-e ERROR]
                        [--input INPUT] [--keep-alive]
                        cmdline [cmdline ...]

positional arguments:
  cmdline               The command to launch and monitor.

optional arguments:
  -h, --help            show this help message and exit
  -i INTERVAL, --interval INTERVAL
                        Interval between measurements. Syntax is:
                        \d+(\.\d+)?(s|m|h).
  -g LOGFILE, --gpu LOGFILE
                        Monitor GPU usage
  -t LOGFILE, --temperatures LOGFILE
                        Monitor temperatures of CPU
  -c LOGFILE, --cpu LOGFILE, --cpu-and-ram LOGFILE
                        Monitor processes, CPU & RAM usage via top
  -q, --quiet           Don't write error messages to stdout
  -o OUTPUT, --output OUTPUT
                        Subprocess stdout
  -e ERROR, --error ERROR
                        Subprocess stderr
  --input INPUT         Subprocess stdin
  --keep-alive          Keep running task when monitor process exits
```

It has all the options of `monitor` but in addition you can control the `stdout`, `stderr` and `stdin`
of the subprocess launched.

Stopping the Heimdallr process will kill the task. If this is not the wanted behaviour
you can specify `--keep-alive` and Heimdallr will try its best to keep the task alive.