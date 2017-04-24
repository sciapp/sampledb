# coding: utf-8
"""
Script for creating an instrument in SampleDB.

Usage: python -m sampledb create_instrument <name> <description>
"""

import sys
from .. import create_app
from ..logic.instruments import create_instrument, get_instruments


def main(arguments):
    if len(arguments) != 2:
        print(__doc__)
        exit(1)
    name, description = arguments
    app = create_app()
    with app.app_context():
        instruments = get_instruments()
        for instrument in instruments:
            if instrument.name == name:
                print('Error: an instrument with this name already exists (#{})'.format(instrument.id), file=sys.stderr)
                exit(1)
        instrument = create_instrument(name, description)
        print("Success: the instrument has been created in SampleDB (#{})".format(instrument.id))
