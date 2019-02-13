# coding: utf-8
"""
Script for creating a user of type OTHER in SampleDB.

Usage: python -m sampledb create_other_user <name> <email>
"""

import os
import sys
from .. import create_app
from ..logic.users import create_user, UserType
from ..logic.authentication import add_other_authentication


def main(arguments):
    if len(arguments) != 2 or not all(arguments):
        print(__doc__)
        exit(1)
    name, email = arguments
    if '@' not in email[1:-1]:
        print("Error: email must be a valid email address", file=sys.stderr)
        exit(1)
    password = ''.join([('00' + hex(c)[2:])[-2:] for c in os.urandom(16)])
    print("Note: the user will receive the password '{}'".format(password))
    app = create_app()
    with app.app_context():
        user = create_user(name, email, UserType.OTHER)
        add_other_authentication(user.id, name, password)
        print("Success: the user has been created in SampleDB (#{})".format(user.id))
