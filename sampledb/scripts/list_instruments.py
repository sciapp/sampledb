# coding: utf-8
"""
Script for listing all instruments in SampleDB.

Usage: python -m sampledb list_instruments
"""

from .. import create_app
from ..logic.instrument_translations import get_instruments_with_translation_in_language
from ..logic.languages import Language


def main(arguments):
    if len(arguments) != 0:
        print(__doc__)
        exit(1)
    app = create_app()
    with app.app_context():
        instruments = get_instruments_with_translation_in_language(Language.ENGLISH)
        for instrument in instruments:
            print(" - #{0.id}: {0.translation.name}".format(instrument))
