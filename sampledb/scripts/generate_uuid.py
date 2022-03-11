# coding: utf-8
"""
Script for generating an UUID to be used as database identifier in a federation.

Usage: python -m sampledb generate_uuid
"""

import uuid


def main(arguments):
    if len(arguments) != 0:
        print(__doc__)
        exit(1)
    print(uuid.uuid4())
