# coding: utf-8
"""
Script for updating an instrument in SampleDB.

Usage: sampledb update_instrument <instrument_id> <name> <description>
"""

import sys
import typing

from .. import create_app
from ..logic.instruments import check_instrument_exists
from ..logic.instrument_translations import set_instrument_translation
from ..logic.errors import InstrumentDoesNotExistError
from ..logic.languages import Language


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 3:
        print(__doc__)
        sys.exit(1)
    instrument_id_str, name, description = arguments
    try:
        instrument_id = int(instrument_id_str)
    except ValueError:
        print("Error: instrument_id must be an integer", file=sys.stderr)
        sys.exit(1)
    app = create_app()
    with app.app_context():
        if app.config['DISABLE_INSTRUMENTS']:
            print('Error: instruments are disabled', file=sys.stderr)
            sys.exit(1)
        try:
            check_instrument_exists(instrument_id)
        except InstrumentDoesNotExistError:
            print('Error: no instrument with this id exists', file=sys.stderr)
            sys.exit(1)
        set_instrument_translation(
            language_id=Language.ENGLISH,
            instrument_id=instrument_id,
            name=name,
            description=description
        )
        print("Success: the instrument has been updated in SampleDB")
