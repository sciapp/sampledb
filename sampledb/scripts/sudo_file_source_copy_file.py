# coding: utf-8
"""
Script for running LocalFileSource.copy_file() as a different user.

Usage: sudo <username> python -m sampledb sudo_file_source_copy_file <user_id> <object_id> <directory> <file_name>
"""

from .. import create_app
from ..logic.files import LocalFileSource


def main(arguments):
    if len(arguments) != 4:
        print(__doc__)
        exit(1)
    user_id, object_id, directory, file_name = arguments
    try:
        user_id = int(user_id)
        object_id = int(object_id)
    except ValueError:
        print(__doc__)
        exit(1)

    app = create_app()
    with app.app_context():
        file_source = LocalFileSource(lambda _: directory)
        file_source.copy_file(user_id=user_id, object_id=object_id, file_name=file_name)
