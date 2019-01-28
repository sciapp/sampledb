# coding: utf-8
"""
Script for updating an instrument in SampleDB.

Usage: python -m sampledb update_instrument <instrument_id> <name> <description>
"""

import sys
from .. import create_app
from ..logic.instruments import update_instrument, get_instrument
from ..logic.errors import InstrumentDoesNotExistError


def main(arguments):
    if len(arguments) != 3:
        print(__doc__)
        exit(1)
    instrument_id, name, description = arguments
    try:
        instrument_id = int(instrument_id)
    except ValueError:
        print("Error: instrument_id must be an integer", file=sys.stderr)
        exit(1)
    app = create_app()
    with app.app_context():
        try:
            get_instrument(instrument_id)
        except InstrumentDoesNotExistError:
            print('Error: no instrument with this id exists', file=sys.stderr)
            exit(1)
        update_instrument(instrument_id, name, description)
        print("Success: the instrument has been updated in SampleDB")
