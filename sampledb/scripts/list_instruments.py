# coding: utf-8
"""
Script for listing all instruments in SampleDB.

Usage: sampledb list_instruments
"""
import sys
import typing

from .. import create_app
from ..logic.instruments import get_instruments


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 0:
        print(__doc__)
        sys.exit(1)
    app = create_app()
    with app.app_context():
        if not app.config['DISABLE_INSTRUMENTS']:
            instruments = get_instruments()
            for instrument in instruments:
                print(f"- #{instrument.id}: {instrument.name.get('en', 'Unnamed Instrument')}")
