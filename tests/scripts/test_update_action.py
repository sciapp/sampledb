# coding: utf-8
"""

"""

import json
import os
import pytest
import sampledb
from sampledb.logic import actions, instruments, action_translations, languages
import sampledb.__main__ as scripts


@pytest.fixture
def instrument():
    return instruments.create_instrument()


@pytest.fixture
def schema_file_name():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'schemas', 'minimal.json'))


@pytest.fixture
def action(instrument, schema_file_name):
    with open(schema_file_name) as schema_file:
        schema = json.load(schema_file)
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema,
        instrument_id=instrument.id
    )
    action_translations.set_action_translation(
        language_id=languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description='Example Action Description'
    )
    return action


def test_update_action(action, schema_file_name, capsys):
    name = 'Example Action'
    description = 'Example Action Description'
    assert len(actions.get_actions()) == 1

    scripts.main([scripts.__file__, 'update_action', str(action.id), name, description, schema_file_name])

    assert 'Success' in capsys.readouterr()[0]
    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.type_id == sampledb.models.ActionType.SAMPLE_CREATION
    action = actions.get_action(
        action_id=action.id
    )
    assert action.name['en'] == name
    assert action.description['en'] == description


def test_update_action_missing_arguments(action, capsys):
    name = 'Example Action'
    description = 'Example Action Description'
    assert len(actions.get_actions()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_action', str(action.id), name, ''])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.type_id == sampledb.models.ActionType.SAMPLE_CREATION
    action = actions.get_action(
        action_id=action.id
    )
    assert action.name['en'] == name
    assert action.description['en'] == description


def test_update_action_invalid_action_id(action, schema_file_name, capsys):
    name = 'Example Action'
    description = 'Example Action Description'
    assert len(actions.get_actions()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_action', name, name, '', schema_file_name])
    assert exc_info.value != 0
    assert 'Error: action_id must be an integer' in capsys.readouterr()[1]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.type_id == sampledb.models.ActionType.SAMPLE_CREATION
    action = actions.get_action(
        action_id=action.id
    )
    assert action.name['en'] == name
    assert action.description['en'] == description


def test_update_action_missing_action(action, schema_file_name, capsys):
    name = 'Example Action'
    description = 'Example Action Description'
    assert len(actions.get_actions()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_action', str(action.id+1), name, '', schema_file_name])
    assert exc_info.value != 0
    assert 'Error: no action with this id exists' in capsys.readouterr()[1]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.type_id == sampledb.models.ActionType.SAMPLE_CREATION
    action = actions.get_action(
        action_id=action.id
    )
    assert action.name['en'] == name
    assert action.description['en'] == description


def test_update_action_invalid_schema(action, capsys):
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'action.json'))
    assert len(actions.get_actions()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_action', str(action.id), name, '', schema_file_name])
    assert exc_info.value != 0
    assert 'Error: invalid schema:' in capsys.readouterr()[1]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.type_id == sampledb.models.ActionType.SAMPLE_CREATION
    action = actions.get_action(
        action_id=action.id
    )
    assert action.name['en'] == name
    assert action.description['en'] == description
