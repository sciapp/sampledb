# coding: utf-8
"""
Script for listing all instruments in SampleDB.

Usage: python -m sampledb list_instruments
"""

from .. import create_app
from ..logic.instruments import get_instruments


def main(arguments):
    if len(arguments) != 0:
        print(__doc__)
        exit(1)
    app = create_app()
    with app.app_context():
        instruments = get_instruments()
        for instrument in instruments:
            print(" - #{0.id}: {0.name}".format(instrument))
