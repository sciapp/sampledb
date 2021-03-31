# coding: utf-8
"""
Script for creating an action in SampleDB.

Usage: python -m sampledb create_action <instrument_id> <type: sample or measurement > <name> <description> <schema_file_name>
"""

import json
import sys
from .. import create_app
from ..logic.actions import create_action, get_action_type
from ..logic.action_type_translations import get_action_types_with_translations_in_language, get_action_type_with_translation_in_language
from ..logic.action_translations import set_action_translation
from ..logic.instruments import get_instrument
from ..logic.languages import Language
from ..logic.schemas import validate_schema
from ..logic.errors import InstrumentDoesNotExistError, ValidationError, ActionTypeDoesNotExistError
from .. import models


def main(arguments):
    if len(arguments) != 5:
        print(__doc__)
        exit(1)
    instrument_id, action_type_id, name, description, schema_file_name = arguments
    if instrument_id == 'None':
        instrument_id = None
    else:
        try:
            instrument_id = int(instrument_id)
        except ValueError:
            print("Error: instrument_id must be an integer or 'None'", file=sys.stderr)
            exit(1)
    try:
        action_type_id = int(action_type_id)
    except ValueError:
        action_type_id = {
            'sample': models.ActionType.SAMPLE_CREATION,
            'measurement': models.ActionType.MEASUREMENT,
            'simulation': models.ActionType.SIMULATION
        }.get(action_type_id, None)
    try:
        get_action_type(action_type_id)
    except ActionTypeDoesNotExistError:
        action_type_id = None
    if action_type_id is None:
        print("Error: action type must be one of the following:", file=sys.stderr)
        print(f'- "sample" (for {get_action_type_with_translation_in_language(models.ActionType.SAMPLE_CREATION, Language.ENGLISH).translation.name})', file=sys.stderr)
        print(f'- "measurement" (for {get_action_type_with_translation_in_language(models.ActionType.MEASUREMENT, Language.ENGLISH).translation.name})', file=sys.stderr)
        print(f'- "simulation" (for {get_action_type_with_translation_in_language(models.ActionType.SIMULATION, Language.ENGLISH).translation.name})', file=sys.stderr)
        for action_type in get_action_types_with_translations_in_language(Language.ENGLISH):
            print(f'- "{action_type.id}" (for {action_type.translation.name})', file=sys.stderr)
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
            action_type_id=action_type_id,
            schema=schema
        )
        set_action_translation(
            language_id=Language.ENGLISH,
            action_id=action.id,
            name=name,
            description=description
        )
        print("Success: the action has been created in SampleDB (#{})".format(action.id))
