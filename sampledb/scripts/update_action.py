# coding: utf-8
"""
Script for updating an action in SampleDB.

Usage: sampledb update_action <action_id> <name> <description> <schema_file_name>
"""

import json
import sys
import typing

from .. import create_app
from ..logic.actions import check_action_exists
from ..logic.action_translations import set_action_translation
from ..logic.schemas import validate_schema
from ..logic.errors import ActionDoesNotExistError, ValidationError
from ..logic.languages import Language


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 4:
        print(__doc__)
        sys.exit(1)
    action_id_str, name, description, schema_file_name = arguments
    try:
        action_id = int(action_id_str)
    except ValueError:
        print("Error: action_id must be an integer", file=sys.stderr)
        sys.exit(1)

    app = create_app()
    with app.app_context():
        try:
            check_action_exists(action_id)
        except ActionDoesNotExistError:
            print('Error: no action with this id exists', file=sys.stderr)
            sys.exit(1)
        with open(schema_file_name, 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        try:
            validate_schema(schema)
        except ValidationError as e:
            print(f'Error: invalid schema: {str(e)}', file=sys.stderr)
            sys.exit(1)
        set_action_translation(
            language_id=Language.ENGLISH,
            action_id=action_id,
            name=name,
            description=description
        )
        print("Success: the action has been updated in SampleDB")
