import re
from collections import defaultdict
from typing import List

from ..resource import MultiCommandResource


class DiskUsage(MultiCommandResource):

    @property
    def column_names(self) -> List[str]:
        return ['datetime', 'filesystem', 'type',
                'size', 'memory used', 'memory available', 'perc memory used',
                'num inodes', 'inodes used', 'inodes available', 'perc inodes used',
                'mount point'
                ]

    def make_cmdlines(self, config):
        memory_usage = ['df', '-hT']
        inode_usage = ['df', '-hiT']
        return [memory_usage, inode_usage]

    def make_regexes(self, config):
        generic_regex = re.compile(
            r'''
                (?P<fs>\S+)\s+(?P<type>\S+)\s+(?P<size>\S+)\s+(?P<used>\S+)\s+(?P<available>\S+)\s+
                (?P<perc_used>\S+)\s+(?P<mount_point>.*)
            ''',
            re.VERBOSE
        )
        return [(generic_regex, True), (generic_regex, True)]

    def clean_output(self, output, command_name, config):
        return output[output.index('\n') + 1:]

    def combine_results(self, results, config):
        memory, inodes = results
        combined_outputs = defaultdict(dict)
        for mem in memory['values']:
            combined_outputs[mem['fs']] = {
                'type': mem['type'],
                'size': mem['size'],
                'memory used': mem['used'],
                'memory available': mem['available'],
                'perc memory used': mem['perc_used'],
                'mount point': mem['mount_point'],
            }
        for inode in inodes['values']:
            combined_outputs[inode['fs']].update({
                'type': inode['type'],
                'num inodes': inode['size'],
                'inodes used': inode['used'],
                'inodes available': inode['available'],
                'perc inodes used': inode['perc_used'],
                'mount point': inode['mount_point'],
            })

        for fs_name, values in combined_outputs.items():
            values['filesystem'] = fs_name
            values['datetime'] = memory['datetime']
            yield values


create_resource = DiskUsage
aliases = ['disk']