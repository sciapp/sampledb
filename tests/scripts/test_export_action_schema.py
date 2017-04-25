# coding: utf-8
"""

"""

import json
import os
import pytest
import tempfile
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


def test_export_action_schema(action):
    with tempfile.NamedTemporaryFile('r') as schema_file:
        scripts.main([scripts.__file__, 'export_action_schema', str(action.id), schema_file.name])
        schema = json.load(schema_file)
        assert action.schema == schema


def test_export_action_schema_missing_arguments(action):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'export_action_schema', str(action.id)])
    assert exc_info.value != 0


def test_export_action_schema_invalid_action_id(action):
    with tempfile.NamedTemporaryFile('r') as schema_file:
        with pytest.raises(SystemExit) as exc_info:
            scripts.main([scripts.__file__, 'export_action_schema', action.name, schema_file.name])
        assert exc_info.value != 0
        assert schema_file.read() == ''


def test_export_action_schema_missing_action():
    with tempfile.NamedTemporaryFile('r') as schema_file:
        with pytest.raises(SystemExit) as exc_info:
            scripts.main([scripts.__file__, 'export_action_schema', 1, schema_file.name])
        assert exc_info.value != 0
        assert schema_file.read() == ''
