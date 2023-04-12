# coding: utf-8
"""
Script for exporting the schema of an action in SampleDB to a JSON file.

Usage: sampledb export_action_schema <action_id> <schema_file_name>
"""

import json
import sys
import typing

from .. import create_app
from ..logic.actions import get_action
from ..logic.errors import ActionDoesNotExistError


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 2:
        print(__doc__)
        sys.exit(1)
    action_id_str, schema_file_name = arguments
    try:
        action_id = int(action_id_str)
    except ValueError:
        print("Error: action_id must be an integer", file=sys.stderr)
        sys.exit(1)

    app = create_app()
    with app.app_context():
        try:
            action = get_action(action_id)
        except ActionDoesNotExistError:
            print('Error: no action with this id exists', file=sys.stderr)
            sys.exit(1)
        schema = action.schema
    with open(schema_file_name, 'w', encoding='utf-8') as schema_file:
        json.dump(schema, schema_file, indent=2)
    print(f"Success: the action schema has been exported to {schema_file_name}")
