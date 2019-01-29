# coding: utf-8
"""
Script for creating an action in SampleDB.

Usage: python -m sampledb create_action <instrument_id> <type: sample or measurement > <name> <description> <schema_file_name>
"""

import json
import sys
from .. import create_app
from ..logic.actions import create_action, ActionType
from ..logic.instruments import get_instrument
from ..logic.schemas import validate_schema
from ..logic.errors import InstrumentDoesNotExistError, ValidationError


def main(arguments):
    if len(arguments) != 5:
        print(__doc__)
        exit(1)
    instrument_id, action_type, name, description, schema_file_name = arguments
    if instrument_id == 'None':
        instrument_id = None
    else:
        try:
            instrument_id = int(instrument_id)
        except ValueError:
            print("Error: instrument_id must be an integer or 'None'", file=sys.stderr)
            exit(1)
    if action_type == 'sample':
        action_type = ActionType.SAMPLE_CREATION
    elif action_type == 'measurement':
        action_type = ActionType.MEASUREMENT
    elif action_type == 'simulation':
        action_type = ActionType.SIMULATION
    else:
        print('Error: action type must be "sample" or "measurement"', file=sys.stderr)
        exit(1)
    app = create_app()
    with app.app_context():
        if instrument_id is not None:
            try:
                get_instrument(instrument_id)
            except InstrumentDoesNotExistError:
                print('Error: no instrument with this id exists', file=sys.stderr)
                exit(1)
        with open(schema_file_name, 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        try:
            validate_schema(schema)
        except ValidationError as e:
            print('Error: invalid schema: {}'.format(str(e)), file=sys.stderr)
            exit(1)
        action = create_action(
            instrument_id=instrument_id,
            action_type=action_type,
            name=name,
            description=description,
            schema=schema
        )
        print("Success: the action has been created in SampleDB (#{})".format(action.id))
