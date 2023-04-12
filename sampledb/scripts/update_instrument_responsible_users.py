# coding: utf-8
"""
Script for updating the users responsible for an instrument in SampleDB.

Usage: sampledb update_instrument_responsible_users <instrument_id> <instrument_reponsible_user_ids...>
"""

import sys
import typing

from .. import create_app
from ..logic.instruments import get_instrument, add_instrument_responsible_user, remove_instrument_responsible_user
from ..logic.users import check_user_exists
from ..logic.errors import UserDoesNotExistError, InstrumentDoesNotExistError


def main(arguments: typing.List[str]) -> None:
    if len(arguments) == 0:
        print(__doc__)
        sys.exit(1)
    try:
        instrument_id = int(arguments[0])
    except ValueError:
        print("Error: instrument_id must be an integer", file=sys.stderr)
        sys.exit(1)
    instrument_responsible_user_ids = []
    for user_id_str in arguments[1:]:
        try:
            user_id = int(user_id_str)
        except ValueError:
            print("Error: instrument_reponsible_user_ids must be integer", file=sys.stderr)
            sys.exit(1)
        instrument_responsible_user_ids.append(user_id)
    app = create_app()
    with app.app_context():
        if app.config['DISABLE_INSTRUMENTS']:
            print('Error: instruments are disabled', file=sys.stderr)
            sys.exit(1)
        try:
            instrument = get_instrument(instrument_id)
        except InstrumentDoesNotExistError:
            print('Error: no instrument with this id exists', file=sys.stderr)
            sys.exit(1)
        for user_id in instrument_responsible_user_ids:
            try:
                check_user_exists(user_id)
            except UserDoesNotExistError:
                print(f'Error: no user with the id #{user_id} exists', file=sys.stderr)
                sys.exit(1)
        previous_instrument_responsible_user_ids = [user.id for user in instrument.responsible_users]
        for user_id in instrument_responsible_user_ids:
            if user_id not in previous_instrument_responsible_user_ids:
                add_instrument_responsible_user(instrument.id, user_id)
        for user_id in previous_instrument_responsible_user_ids:
            if user_id not in instrument_responsible_user_ids:
                remove_instrument_responsible_user(instrument.id, user_id)
        print("Success: the instrument responsible users have been updated in SampleDB")
