#
# Copyright (c) 2024 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from .source import SourceSplititNew

def run():
    source = SourceSplititNew()
    launch(source, sys.argv[1:])
