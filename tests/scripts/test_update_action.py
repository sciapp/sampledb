# coding: utf-8
"""

"""

import json
import os
import pytest
from sampledb.logic import instruments
import sampledb.__main__ as scripts
from ..test_utils import app_context


@pytest.fixture
def instrument():
    return instruments.create_instrument('Example Instrument', 'Example Instrument Description')


@pytest.fixture
def schema_file_name():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))


@pytest.fixture
def action(instrument, schema_file_name):
    with open(schema_file_name) as schema_file:
        schema = json.load(schema_file)
    return instruments.create_action(
        action_type=instruments.ActionType.SAMPLE_CREATION,
        name='Example Action',
        description='Example Action Description',
        schema=schema,
        instrument_id=instrument.id
    )


def test_update_action(action, schema_file_name):
    name = 'Example Action'
    description = 'Example Action Description'
    assert len(instruments.get_actions()) == 1

    scripts.main([scripts.__file__, 'update_action', str(action.id), name, '', schema_file_name])

    assert len(instruments.get_actions()) == 1
    action = instruments.get_actions()[0]
    assert action.name == name
    assert action.description == ''
    assert action.type == instruments.ActionType.SAMPLE_CREATION


def test_update_action_missing_arguments(action):
    name = 'Example Action'
    description = 'Example Action Description'
    assert len(instruments.get_actions()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_action', str(action.id), name, ''])
    assert exc_info.value != 0

    assert len(instruments.get_actions()) == 1
    action = instruments.get_actions()[0]
    assert action.name == name
    assert action.description == description
    assert action.type == instruments.ActionType.SAMPLE_CREATION


def test_update_action_invalid_action_id(action, schema_file_name):
    name = 'Example Action'
    description = 'Example Action Description'
    assert len(instruments.get_actions()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_action', name, name, '', schema_file_name])
    assert exc_info.value != 0

    assert len(instruments.get_actions()) == 1
    action = instruments.get_actions()[0]
    assert action.name == name
    assert action.description == description
    assert action.type == instruments.ActionType.SAMPLE_CREATION


def test_update_action_missing_action(action, schema_file_name):
    name = 'Example Action'
    description = 'Example Action Description'
    assert len(instruments.get_actions()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_action', str(action.id+1), name, '', schema_file_name])
    assert exc_info.value != 0

    assert len(instruments.get_actions()) == 1
    action = instruments.get_actions()[0]
    assert action.name == name
    assert action.description == description
    assert action.type == instruments.ActionType.SAMPLE_CREATION


def test_update_action_invalid_schema(action):
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'action.json'))
    assert len(instruments.get_actions()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_action', str(action.id), name, '', schema_file_name])
    assert exc_info.value != 0

    assert len(instruments.get_actions()) == 1
    action = instruments.get_actions()[0]
    assert action.name == name
    assert action.description == description
    assert action.type == instruments.ActionType.SAMPLE_CREATION
