import datetime as dt
import io
import os
import csv
import signal
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime

import curio

LOCAL_TIMEZONE = datetime.now(dt.timezone.utc).astimezone().tzinfo


def to_local_str(date: datetime):
    """Convert a datetime into a string with local timezone."""
    return date.replace(tzinfo=LOCAL_TIMEZONE).strftime('%Y-%m-%dT%H:%M:%S%Z')


def _pid_exists(pid):
    """Return True if a process with the given pid exists. False otherwise."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@contextmanager
def name_of_temporary_file(verbose=False):
    # best-effort to remove the temporary file when we are done
    fd, tmp_filename = tempfile.mkstemp(suffix='.main.py')
    os.close(fd)
    try:
        yield tmp_filename
    finally:
        try:
            os.remove(tmp_filename)
        except Exception as e:
            if verbose:
                msg = "Failed to delete temporary file {0}.\n{1.__class__.__name__}: {1}"
                sys.stderr.write(msg.format(tmp_filename, e))


def create_gentle_killer(proc, verbose):
    """Returns a function that will try to kill the given process and corresponding process group."""
    proc_pid = proc.pid
    if verbose:
        log = sys.stderr.write
    else:
        def log(_):
            """noop"""

    def kill_gently(victim_id):
        """Kills the process group `victim_id` and then terminates the current process with exit code 1."""
        # try with SIGTERM
        try:
            log("Killing background task gently. ")
            try:
                os.killpg(victim_id, signal.SIGTERM)
                if proc.poll() is None:
                    log("Waiting up to 5 seconds ")
                    for i in range(25):
                        time.sleep(0.2)
                        if i % 5 == 0:
                            log('.')
                        if proc.poll() is not None:
                            log(' Process completed.\n')
                            break
                else:
                    log("Task killed.\n")
            except Exception as e:
                log("got an exception: {0.__class__.__name__}: {0}\n".format(e))

            if proc.poll() is None:
                # stop being gentle. Go with SIGKILL
                log("killing background task BRUTALLY...")
                try:
                    os.killpg(victim_id, signal.SIGKILL)
                    log("Task brutally killed.\n")
                except Exception as e:
                    msg = (
                        "got an exception: {0.__class__.__name__}: {0}\n"
                        "The background task with pid: {1} might still be alive!\n"
                    )
                    log(msg.format(e, proc_pid))
        finally:
            log('Exiting main process.\n')
            sys.exit(1)

    return kill_gently


def grouper(n, iterable):
    iterator = iter(iterable)
    yield from iter(lambda: [x for _,x in zip(range(n), iterator)], [])


class AsyncCsvWriter:
    def __init__(self, async_file: curio.file.AsyncFile, *args, **kwargs):
        self._async_file = async_file
        self._csv_args = args
        self._csv_kwargs = kwargs

    def _buffer(self):
        return io.BytesIO() if 'b' in self._async_file.mode else io.StringIO()

    def _writer(self, buffer):
        return csv.writer(buffer, *self._csv_args, **self._csv_kwargs)

    async def writerow(self, row):
        buffer = self._buffer()
        self._writer(buffer).writerow(row)
        await self._async_file.write(buffer.getvalue())

    async def writerows(self, rows):
        for row_group in grouper(1000, rows):
            buffer = self._buffer()
            self._writer(buffer).writerows(row_group)
            await self._async_file.write(buffer.getvalue())


class AsyncDictCsvWriter:
    def __init__(self, async_file, fieldnames, restval="", extrasaction="raise", dialect="excel", *args, **kwds):
        self.fieldnames = fieldnames    # list of keys for the dict
        self.restval = restval          # for writing short dicts
        if extrasaction.lower() not in ("raise", "ignore"):
            raise ValueError("extrasaction (%s) must be 'raise' or 'ignore'" % extrasaction)
        self.extrasaction = extrasaction
        self.writer = AsyncCsvWriter(async_file, dialect, *args, **kwds)

    async def writeheader(self):
        header = dict(zip(self.fieldnames, self.fieldnames))
        await self.writerow(header)

    def _dict_to_list(self, rowdict):
        if self.extrasaction == "raise":
            wrong_fields = rowdict.keys() - self.fieldnames
            if wrong_fields:
                raise ValueError("dict contains fields not in fieldnames: " + ", ".join(map(repr, wrong_fields)))
        return (rowdict.get(key, self.restval) for key in self.fieldnames)

    async def writerow(self, rowdict):
        await self.writer.writerow(self._dict_to_list(rowdict))

    async def writerows(self, rowdicts):
        await self.writer.writerows(map(self._dict_to_list, rowdicts))