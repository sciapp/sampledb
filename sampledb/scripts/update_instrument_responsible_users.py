# coding: utf-8
"""
Script for updating the users responsible for an instrument in SampleDB.

Usage: python -m sampledb update_instrument_responsible_users <instrument_id> <instrument_reponsible_user_ids...>
"""

import sys
from .. import create_app
from ..logic.instruments import get_instrument, add_instrument_responsible_user, remove_instrument_responsible_user
from ..logic.users import get_user
from ..logic.errors import UserDoesNotExistError, InstrumentDoesNotExistError


def main(arguments):
    if len(arguments) == 0:
        print(__doc__)
        exit(1)
    instrument_id = arguments[0]
    instrument_responsible_user_ids = arguments[1:]
    try:
        instrument_id = int(instrument_id)
    except ValueError:
        print("Error: instrument_id must be an integer", file=sys.stderr)
        exit(1)
    for i, user_id in enumerate(instrument_responsible_user_ids):
        try:
            user_id = int(user_id)
        except ValueError:
            print("Error: instrument_reponsible_user_ids must be integer", file=sys.stderr)
            exit(1)
        instrument_responsible_user_ids[i] = user_id
    app = create_app()
    with app.app_context():
        try:
            instrument = get_instrument(instrument_id)
        except InstrumentDoesNotExistError:
            print('Error: no instrument with this id exists', file=sys.stderr)
            exit(1)
        for user_id in instrument_responsible_user_ids:
            try:
                get_user(user_id)
            except UserDoesNotExistError:
                print('Error: no user with the id #{} exists'.format(user_id), file=sys.stderr)
                exit(1)
        previous_instrument_responsible_user_ids = [user.id for user in instrument.responsible_users]
        for user_id in instrument_responsible_user_ids:
            if user_id not in previous_instrument_responsible_user_ids:
                add_instrument_responsible_user(instrument.id, user_id)
        for user_id in previous_instrument_responsible_user_ids:
            if user_id not in instrument_responsible_user_ids:
                remove_instrument_responsible_user(instrument.id, user_id)
        print("Success: the instrument responsible users have been updated in SampleDB")
