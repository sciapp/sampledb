# coding: utf-8
"""
Script for creating an instrument in SampleDB.

Usage: python -m sampledb create_instrument <name> <description>
"""

import sys
from .. import create_app
from ..logic.instruments import create_instrument, get_instruments
from ..logic.instrument_translations import set_instrument_translation, get_instrument_with_translation_in_language
from ..logic.languages import Language


def main(arguments):
    if len(arguments) != 2:
        print(__doc__)
        exit(1)
    name, description = arguments
    app = create_app()
    with app.app_context():
        instruments = get_instruments()
        for instrument in instruments:
            instrument = get_instrument_with_translation_in_language(
                instrument_id=instrument.id,
                language_id=Language.ENGLISH
            )
            if instrument.translation.name == name:
                print('Error: an instrument with this name already exists (#{})'.format(instrument.id), file=sys.stderr)
                exit(1)
        instrument = create_instrument()
        set_instrument_translation(
            language_id=Language.ENGLISH,
            instrument_id=instrument.id,
            name=name,
            description=description
        )
        print("Success: the instrument has been created in SampleDB (#{})".format(instrument.id))
