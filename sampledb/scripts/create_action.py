# coding: utf-8
"""
Script for creating an action in SampleDB.

Usage: sampledb create_action <instrument_id> <type: sample or measurement > <name> <description> <schema_file_name>
"""

import json
import sys
import typing

from .. import create_app
from ..logic.action_types import check_action_type_exists, get_action_type, get_action_types
from ..logic.actions import create_action
from ..logic.action_translations import set_action_translation
from ..logic.instruments import check_instrument_exists
from ..logic.languages import Language
from ..logic.schemas import validate_schema
from ..logic.errors import InstrumentDoesNotExistError, ValidationError, ActionTypeDoesNotExistError
from ..logic.utils import get_translated_text
from .. import models


def main(arguments: typing.List[str]) -> None:
    if len(arguments) != 5:
        print(__doc__)
        sys.exit(1)
    instrument_id_str, action_type_id_str, name, description, schema_file_name = arguments
    if instrument_id_str == 'None':
        instrument_id: typing.Optional[int] = None
    else:
        try:
            instrument_id = int(instrument_id_str)
        except ValueError:
            print("Error: instrument_id must be an integer or 'None'", file=sys.stderr)
            sys.exit(1)
    try:
        action_type_id: typing.Optional[int] = int(action_type_id_str)
    except ValueError:
        action_type_id = {
            'sample': models.ActionType.SAMPLE_CREATION,
            'measurement': models.ActionType.MEASUREMENT,
            'simulation': models.ActionType.SIMULATION
        }.get(action_type_id_str, None)
    if action_type_id is not None:
        try:
            check_action_type_exists(action_type_id)
        except ActionTypeDoesNotExistError:
            action_type_id = None
    if action_type_id is None:
        print("Error: action type must be one of the following:", file=sys.stderr)
        print(f'- "sample" (for {get_translated_text(get_action_type(models.ActionType.SAMPLE_CREATION).name, "en")})', file=sys.stderr)
        print(f'- "measurement" (for {get_translated_text(get_action_type(models.ActionType.MEASUREMENT).name, "en")})', file=sys.stderr)
        print(f'- "simulation" (for {get_translated_text(get_action_type(models.ActionType.SIMULATION).name, "en")})', file=sys.stderr)
        for action_type in get_action_types():
            print(f'- "{action_type.id}" (for {get_translated_text(action_type.name, "en")})', file=sys.stderr)
        sys.exit(1)
    app = create_app()
    with app.app_context():
        if instrument_id is not None:
            if app.config['DISABLE_INSTRUMENTS']:
                print('Error: instruments are disabled', file=sys.stderr)
                sys.exit(1)
            try:
                check_instrument_exists(instrument_id)
            except InstrumentDoesNotExistError:
                print('Error: no instrument with this id exists', file=sys.stderr)
                sys.exit(1)
        with open(schema_file_name, 'r', encoding='utf-8') as schema_file:
            schema = json.load(schema_file)
        try:
            validate_schema(schema)
        except ValidationError as e:
            print(f'Error: invalid schema: {str(e)}', file=sys.stderr)
            sys.exit(1)
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
        print(f"Success: the action has been created in SampleDB (#{action.id})")
