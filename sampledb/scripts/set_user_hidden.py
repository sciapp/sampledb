# coding: utf-8
"""
Script for setting whether a user should be hidden from user lists.

Usage: python -m sampledb set_user_hidden <user_id> <yes_or_no>
"""

import sys
from .. import create_app
from ..logic.users import get_user, set_user_hidden
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
    is_hidden = yes_or_no == 'yes'
    app = create_app()
    with app.app_context():
        try:
            user = get_user(user_id)
        except UserDoesNotExistError:
            print("Error: No user with this ID exists", file=sys.stderr)
            exit(1)
        if user.is_hidden == is_hidden:
            print("Success: no change necessary")
        else:
            set_user_hidden(user.id, is_hidden)
            if is_hidden:
                print("Success: the user is hidden")
            else:
                print("Success: the user is not hidden")
