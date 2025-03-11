# coding: utf-8
"""
Script for creating a user of type OTHER in SampleDB.

Usage: sampledb create_other_user <name> <email>
"""

import os
import string
import sys
import typing

from .. import create_app
from ..logic.users import create_user
from ..logic.authentication import add_other_authentication, is_login_available
from ..models import UserType


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 2 or not all(arguments):
        print(__doc__)
        sys.exit(1)
    name, email = arguments
    if not all(c in string.ascii_lowercase + string.digits + '_' for c in name):
        print("Error: name may only contain lower case characters, digits and underscores", file=sys.stderr)
        sys.exit(1)
    if not is_login_available(name):
        print('Error: name is already being used', file=sys.stderr)
        sys.exit(1)
    if '@' not in email[1:-1]:
        print("Error: email must be a valid email address", file=sys.stderr)
        sys.exit(1)
    password = ''.join([('00' + hex(c)[2:])[-2:] for c in os.urandom(16)])
    print(f"Note: the user will receive the password '{password}'")
    app = create_app()
    with app.app_context():
        user = create_user(name, email, UserType.OTHER)
        add_other_authentication(user.id, name, password)
        print(f"Success: the user has been created in SampleDB (#{user.id})")
