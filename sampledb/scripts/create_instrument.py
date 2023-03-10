# coding: utf-8
"""
Script for creating an instrument in SampleDB.

Usage: sampledb create_instrument <name> <description>
"""

import sys
import typing

from .. import create_app
from ..logic.instruments import create_instrument, get_instruments
from ..logic.instrument_translations import set_instrument_translation
from ..logic.languages import Language


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 2:
        print(__doc__)
        sys.exit(1)
    name, description = arguments
    app = create_app()
    with app.app_context():
        if app.config['DISABLE_INSTRUMENTS']:
            print('Error: instruments are disabled', file=sys.stderr)
            sys.exit(1)
        instruments = get_instruments()
        for instrument in instruments:
            if instrument.name.get('en') == name:
                print(f'Error: an instrument with this name already exists (#{instrument.id})', file=sys.stderr)
                sys.exit(1)
        instrument = create_instrument()
        set_instrument_translation(
            language_id=Language.ENGLISH,
            instrument_id=instrument.id,
            name=name,
            description=description
        )
        print(f"Success: the instrument has been created in SampleDB (#{instrument.id})")
