# coding: utf-8
"""
Script for setting whether a user is an administrator or not.

Usage: python -m sampledb set_administrator <user_id> <yes_or_no>
"""

import sys
from .. import create_app, db
from ..logic.users import get_user
from ..logic.errors import UserDoesNotExistError


def main(arguments):
    if len(arguments) != 2 or not all(arguments) or arguments[1] not in ('yes', 'no'):
        print(__doc__)
        exit(1)
    user_id, yes_or_no = arguments
    try:
        user_id = int(user_id)
    except ValueError:
        print("Error: user_id must be an integer", file=sys.stderr)
        exit(1)
    is_admin = yes_or_no == 'yes'
    app = create_app()
    with app.app_context():
        try:
            user = get_user(user_id)
        except UserDoesNotExistError:
            print("Error: No user with this ID exists", file=sys.stderr)
            exit(1)
        if user.is_admin == is_admin:
            print("Success: no change necessary")
        else:
            user.is_admin = is_admin
            db.session.add(user)
            db.session.commit()
            if is_admin:
                print("Success: the user is an administrator now")
            else:
                print("Success: the user is a regular user now")
