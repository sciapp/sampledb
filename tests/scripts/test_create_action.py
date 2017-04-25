# coding: utf-8
"""

"""

import os
import pytest
from sampledb.logic import instruments
import sampledb.__main__ as scripts
from ..test_utils import app_context


@pytest.fixture
def instrument():
    return instruments.create_instrument('Example Instrument', 'Example Instrument Description')


def test_create_sample_action(instrument):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(instruments.get_actions()) == 0

    scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])

    assert len(instruments.get_actions()) == 1
    action = instruments.get_actions()[0]
    assert action.name == name
    assert action.description == description
    assert action.instrument_id == instrument.id
    assert action.type == instruments.ActionType.SAMPLE_CREATION

def test_create_measurement_action(instrument):
    action_type = 'measurement'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(instruments.get_actions()) == 0

    scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])

    assert len(instruments.get_actions()) == 1
    action = instruments.get_actions()[0]
    assert action.name == name
    assert action.description == description
    assert action.instrument_id == instrument.id
    assert action.type == instruments.ActionType.MEASUREMENT


def test_create_action_missing_arguments(instrument):
    assert len(instruments.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', str(instrument.id)])
    assert exc_info.value != 0
    assert len(instruments.get_actions()) == 0


def test_create_action_invalid_instrument_id(instrument):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(instruments.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', instrument.name, action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert len(instruments.get_actions()) == 0


def test_create_action_missing_instrument():
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(instruments.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', '1', action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert len(instruments.get_actions()) == 0


def test_create_action_invalid_type(instrument):
    action_type = 'sample_creation'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(instruments.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert len(instruments.get_actions()) == 0


def test_create_action_invalid_schema(instrument):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'action.json'))
    assert len(instruments.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert len(instruments.get_actions()) == 0
