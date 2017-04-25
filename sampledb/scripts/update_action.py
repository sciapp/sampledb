# coding: utf-8
"""
Script for updating an action in SampleDB.

Usage: python -m sampledb update_action <action_id> <name> <description> <schema_file_name>
"""

import json
import sys
from .. import create_app
from ..logic.instruments import update_action, get_action
from ..logic.schemas import validate_schema, ValidationError


def main(arguments):
    if len(arguments) != 4:
        print(__doc__)
        exit(1)
    action_id, name, description, schema_file_name = arguments
    try:
        action_id = int(action_id)
    except ValueError:
        print("Error: action_id must be an integer", file=sys.stderr)
        exit(1)

    app = create_app()
    with app.app_context():
        action = get_action(action_id)
        if action is None:
            print('Error: no action with this id exists', file=sys.stderr)
            exit(1)
        with open(schema_file_name, 'r') as schema_file:
            schema = json.load(schema_file, encoding='utf-8')
        try:
            validate_schema(schema)
        except ValidationError as e:
            print('Error: invalid schema: {}'.format(str(e)), file=sys.stderr)
            exit(1)
        action = update_action(
            action_id=action.id,
            name=name,
            description=description,
            schema=schema
        )
        print("Success: the action has been updated in SampleDB")
