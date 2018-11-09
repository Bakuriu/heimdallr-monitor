import re
import os
from typing import List, Set

from ..resource import SimpleCommandResource


class FilesSize(SimpleCommandResource):

    def __init__(self, output_file):
        super().__init__(output_file, table_output=True)

    @property
    def column_names(self) -> List[str]:
        return ['datetime', 'path', 'size']

    def make_cmdline(self, config):
         return ['du', '-sb'] + list(config['files'])

    def make_regex(self, config):
        return re.compile(r'(?P<size>\d+)\s*(?P<path>.*)')

    @classmethod
    def required_options(cls) -> Set[str]:
        return {'files'}


create_resource = FilesSize
aliases = ['files']