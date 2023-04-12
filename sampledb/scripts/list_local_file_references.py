# coding: utf-8
"""
Script for listing all files with "local_reference" storage in SampleDB.

Usage: sampledb list_local_file_references
"""
import sys
import typing

from .. import create_app
from ..models.files import File


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 0:
        print(__doc__)
        sys.exit(1)
    app = create_app()
    with app.app_context():
        files = File.query.all()
        for file in files:
            if file.data is None:
                continue
            if file.data.get('storage') == 'local_reference':
                print(f" - object #{file.object_id} / file #{file.id}: {file.data.get('filepath')} ({'' if file.data.get('valid') else 'invalid, '}uploaded by user #{file.user_id})")
