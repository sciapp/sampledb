# coding: utf-8
"""
Script for listing all actions in SampleDB.

Usage: python -m sampledb list_actions
"""

from .. import create_app
from ..logic.actions import get_actions


def main(arguments):
    if len(arguments) != 0:
        print(__doc__)
        exit(1)
    app = create_app()
    with app.app_context():
        actions = get_actions()
        for action in actions:
            print(" - #{0.id}: {0.name}".format(action))
