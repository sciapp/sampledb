# coding: utf-8
"""
Script for listing all actions in SampleDB.

Usage: python -m sampledb list_actions
"""

from .. import create_app
from ..logic.action_translations import get_actions_with_translation_in_language
from ..logic.languages import Language


def main(arguments):
    if len(arguments) != 0:
        print(__doc__)
        exit(1)
    app = create_app()
    with app.app_context():
        actions = get_actions_with_translation_in_language(Language.ENGLISH)
        for action in actions:
            print(" - #{0.id}: {0.translation.name}".format(action))
