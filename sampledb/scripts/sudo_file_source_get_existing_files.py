# coding: utf-8
"""
Script for running LocalFileSource.get_existing_files() as a different user.

Usage: sudo <username> python -m sampledb sudo_file_source_get_existing_files <directory> <relative_path> <max_depth>
"""


import json

from sampledb.logic.files import LocalFileSource


def main(arguments):
    if len(arguments) != 3:
        print(__doc__)
        exit(1)
    directory, relative_path, max_depth = arguments
    if max_depth == 'None':
        max_depth = None
    else:
        try:
            max_depth = int(max_depth)
        except ValueError:
            print(__doc__)
            exit(1)

    file_source = LocalFileSource(lambda _: directory)
    file_tree = file_source.get_existing_files(0, relative_path=relative_path, max_depth=max_depth)
    print(json.dumps(file_tree))
