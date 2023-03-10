# coding: utf-8
"""
Scripts for administrating SampleDB

Usage: sampledb <script> [options]
"""

import sys
import typing

from .scripts import script_documentation, script_functions


def help_and_exit(return_code: int) -> None:
    available_scripts = sorted(script_functions.keys())
    print(
        __doc__,
        'Available scripts:',
        ' - ' + '\n - '.join(available_scripts),
        '',
        'To find out how more about a script, use:',
        '',
        'python -m sampledb help <script>',
        '',
        sep='\n'
    )
    sys.exit(return_code)


def main(argv: typing.List[str]) -> None:
    if len(argv) < 2:
        return help_and_exit(1)
    script = argv[1]
    arguments = argv[2:]
    if script in ('help', '--help', '-h'):
        if arguments and arguments[0] in script_documentation:
            print(script_documentation[arguments[0]])
            sys.exit(0)
        return help_and_exit(0)
    if any(argument in ('help', '--help', '-h') for argument in arguments):
        if script in script_documentation:
            print(script_documentation[script])
            sys.exit(0)
        return help_and_exit(0)
    if script not in script_functions:
        return help_and_exit(2)
    script_functions[script](arguments)
    return None


if __name__ == '__main__':
    main(sys.argv)
