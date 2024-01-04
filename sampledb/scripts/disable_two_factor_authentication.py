# coding: utf-8
"""
Script for disabling two-factor authentication for a user.

Usage: sampledb disable_two_factor_authentication <user_id>
"""

import sys
import typing

from .. import create_app
from ..logic.authentication import get_active_two_factor_authentication_methods, deactivate_two_factor_authentication_method


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 1 or not all(arguments):
        print(__doc__)
        sys.exit(1)
    try:
        user_id = int(arguments[0])
    except ValueError:
        print("Error: user_id must be a valid user_id", file=sys.stderr)
        sys.exit(1)
    app = create_app()
    with app.app_context():
        active_methods = get_active_two_factor_authentication_methods(user_id)
        if not active_methods:
            print("Error: the user does not have two-factor authentication enabled", file=sys.stderr)
            sys.exit(1)
        for active_method in active_methods:
            deactivate_two_factor_authentication_method(active_method.id)
        print("Success: two-factor authentication has been disabled for the user")
