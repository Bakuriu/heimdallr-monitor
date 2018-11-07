import re

from ..resource import SimpleCommandResource


class Top(SimpleCommandResource):
    """Usage of CPU, Ram, swap etc. Implemented by parsing the output of `top`."""

    TOP_REGEX = re.compile(
        r'''
            top\s*-\s*(?P<time>\d+:\d+:\d+)\s*
                up\s*(?P<uptime>[^,]+),\s*
                (?P<num_users>\d+)\s*users,\s*
                load\s*average:\s*(?P<load_avg_1>[\d,]+),\s*(?P<load_avg_2>[\d,]+),\s*(?P<load_avg_3>[\d,]+)\s*
            Tasks:\s*(?P<num_tasks>\d+)\s*total,\s*
                (?P<num_running_tasks>\d+)\s*running,\s*
                (?P<num_sleeping_tasks>\d+)\s*sleeping,\s*
                (?P<num_stopped_tasks>\d+)\s*stopped,\s*
                (?P<num_zombie_tasks>\d+)\s*zombie\s*
            %Cpu\(s\):\s*(?P<user_cpu>[\d,]+)\s*us,\s*
                (?P<system_cpu>[\d,]+)\s*sy,\s*
                (?P<ni_cpu>[\d,]+)\s*ni,\s*
                (?P<id_cpu>[\d,]+)\s*id,\s*
                (?P<wa_cpu>[\d,]+)\s*wa,\s*
                (?P<hi_cpu>[\d,]+)\s*hi,\s*
                (?P<si_cpu>[\d,]+)\s*si,\s*
                (?P<st_cpu>[\d,]+)\s*st\s*
            (?P<ram_unit>\w+)\s*Mem\s*:\s*
                (?P<ram_total>\d+)\s*total,\s*
                (?P<free_ram>\d+)\s*free,\s*
                (?P<used_ram>\d+)\s*used,\s*
                (?P<ram_buff_cache>\d+)\s*buff/cache\s*
            (?P<swap_unit>\w+)\s*Swap:\s*
                (?P<swap_total>\d+)\s*total,\s*
                (?P<swap_free>\d+)\s*free,\s*
                (?P<swap_used>\d+)\s*used.\s*
                (?P<avail>\d+)\s*avail\s*Mem\s*.*\s*
            (?P<proc_info>(?:.|\n)+)
        ''', re.VERBOSE
    )

    def clean_data(self, info, config):
        pid = str(config.get('pid')) if 'pid' in config else None
        procs = []
        for line in info['proc_info'].splitlines():
            proc_m = re.fullmatch(
                r'\s*(?P<pid>\S+)\s*(?P<user>\S+)\s*(?P<priority>\S+)\s*(?P<nice>\S+)\s*'
                r'(?P<virtual_mem>\S+)\s*(?P<res_mem>\S+)\s*(?P<shared_mem>\S+)\s*\S+\s*'
                r'(?P<perc_cpu>[\d,]+)\s*(?P<perc_mem>[\d,]+)\s*'
                r'(?P<uptime>\S+)\s*(?P<command>.*)\s*',
                line
            )
            procs.append(proc_m.groupdict())
        proc_order = (
            'pid', 'perc_cpu', 'perc_mem', 'uptime', 'user', 'priority', 'nice', 'virtual_mem', 'res_mem',
            'shared_mem', 'command',
        )
        proc_info = '|'.join(
            ','.join(proc[k] for k in proc_order) for proc in procs if pid is None or proc['pid'] == pid
        )
        info['proc_info'] = proc_info
        yield info

    def make_cmdline(self, config):
        return ['top', '-n', '1', '-b'] + (['-p', str(config['pid'])] if config.get('pid') is not None else [])

    def make_regex(self, config):
        return self.TOP_REGEX


create_resource = Top
aliases = ('cpu-and-ram', 'cpu')