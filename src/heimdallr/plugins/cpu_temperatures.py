import re

from ..resource import SimpleCommandResource


class CpuTemps(SimpleCommandResource):
    """Temperatures of the CPU cores"""

    SENSORS_REGEX = re.compile(
        r'''
            (?P<core>Core\s+\d+):\s*(?P<temp>[-+]?\d+\.\d+°C)\s*
            \(high\s*=\s*(?P<high_temp>[-+]?\d+\.\d+°C),\s*crit\s*=\s*(?P<crit_temp>[-+]?\d+\.\d+°C)\)
        ''',
        re.VERBOSE
    )

    def __init__(self, output_file):
        super().__init__(output_file, table_output=True)

    def clean_data(self, info, config):
        columns = ('core', 'temp', 'high_temp', 'crit_temp')
        for value in info['values']:
            row_data = {col: value[col] for col in columns}
            row_data['datetime'] = info['datetime']
            yield row_data
        if not info['values']:
            row_data = dict.fromkeys(columns, 'N/A')
            row_data['datetime'] = info['datetime']
            yield row_data

    def make_cmdline(self, config):
        return ['sensors']

    def make_regex(self, config):
        return self.SENSORS_REGEX


create_resource = CpuTemps
aliases = ('temps', 'temperatures')