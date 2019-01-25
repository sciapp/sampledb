# coding: utf-8
"""
Scripts for administrating SampleDB

Usage: python -m sampledb <script> ...

Available scripts:
"""

import sys

from .scripts import script_functions


available_scripts = list(script_functions.keys())
available_scripts.sort()


def help_and_exit(return_code):
    print(__doc__ + ' - ' + '\n - '.join(available_scripts) + '\n')
    exit(return_code)


def main(argv):
    if len(argv) < 2:
        return help_and_exit(1)
    script = argv[1]
    arguments = argv[2:]
    if script in ('help', '--help', '-h'):
        return help_and_exit(0)
    if script not in script_functions:
        return help_and_exit(2)
    script_functions[script](arguments)


if __name__ == '__main__':
    main(sys.argv)
