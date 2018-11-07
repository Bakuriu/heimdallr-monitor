import re

from ..resource import SimpleCommandResource


class NvidiaGpu(SimpleCommandResource):
    """Resource associated with the `nvidia-smi` command output."""

    NVIDIA_SMI_REGEX = re.compile(
        r'''
            .*\s*
            NVIDIA-SMI\s*(?P<nvidia_smi_version>\d+\.\d+)\s*
                Driver\sVersion:\s*(?P<driver_version>\d+\.\d+)\s*
                CUDA\sVersion:\s*(?P<cuda_version>\d+\.\d+)\s*
            GPU\s*Name\s*
                Persistence-M+\s*\|\s*
                Bus-Id\s*Disp.A\s*\|\s*
                Volatile\s*Uncorr.\s*ECC\s*
            Fan\s* Temp\s* Perf\s* Pwr:Usage/Cap\|\s*
                Memory-Usage\s*\|\s*
                GPU-Util\s*Compute\s*M.\s*
            (?P<gpu_number>\d+)\s* (?P<gpu_name>[\w\s]+(?=\s+\w+\s+))\s+ (?P<persistence_m>\w+)\s* \|\s*
                (?P<bus_id>\d+:\d+:\d+\.\d+)\s* (?P<disp_a>\w+)\s*\|\s*
                (?P<ecc>\S*)\s*
            (?P<gpu_fan>\d+[%])\s* (?P<gpu_temp>\d+[C])\s* (?P<gpu_perf>\w+)\s*
                (?P<gpu_power_usage>\d+[W])\s* / \s*(?P<gpu_power_cap>\d+[W])\s* \|\s*
                (?P<gpu_ram_usage>\d+MiB)\s*/\s*(?P<gpu_total_ram>\d+MiB)\s*\|\s*
                (?P<gpu_util>\d+[%])\s*(?P<compute_m>\w+)\s*
            Processes:\s*
            GPU\s* Memory\s* GPU\s* PID\s* Type\s* Process\s* name\s* Usage\s*
            (?P<proc_info>(?:\n|.)*)
        ''',
        flags=re.VERBOSE
    )

    def clean_output(self, output, config):
        output = re.sub(r'^[+|][+=-]+[|+]\n', '', output, flags=re.MULTILINE)
        output = re.sub(r'^\|\s*', '', output, flags=re.MULTILINE)
        output = re.sub(r'\s*\|$', '', output, flags=re.MULTILINE)
        return re.sub(r'^\s*\n', '', output, flags=re.MULTILINE)

    def clean_data(self, info, config):
        pid = str(config.get('pid')) if 'pid' in config else None
        procs = []
        for line in info['proc_info'].splitlines():
            proc_m = re.fullmatch(
                r'\s*(?P<gpu>\d+)\s*(?P<pid>\d+)\s*(?P<type>\w+)\s*(?P<name>.+)\s+(?P<mem_usage>\d+MiB)\s*',
                line
            )
            procs.append({k: v.strip() for k, v in proc_m.groupdict().items()})
        proc_order = ('pid', 'gpu', 'mem_usage', 'type', 'name')
        proc_info = '|'.join(
            ','.join(proc[k] for k in proc_order) for proc in procs if pid is None or proc['pid'] == pid
        )
        info['proc_info'] = proc_info
        yield info

    def make_cmdline(self, config):
        return ['nvidia-smi']

    def make_regex(self, config):
        return self.NVIDIA_SMI_REGEX


create_resource = NvidiaGpu
aliases = ('gpu', 'graphics-card')
