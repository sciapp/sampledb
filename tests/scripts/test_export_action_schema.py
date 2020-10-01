# coding: utf-8
"""

"""

import json
import os
import pytest
import tempfile
import sampledb
from sampledb import db
from sampledb.logic import instruments, actions
import sampledb.__main__ as scripts


@pytest.fixture
def instrument():
    instrument = instruments.create_instrument('Example Instrument', 'Example Instrument Description')
    assert instrument.id is not None
    db.session.expunge(instrument)
    return instrument


@pytest.fixture
def schema_file_name():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))


@pytest.fixture
def action(instrument, schema_file_name):
    with open(schema_file_name) as schema_file:
        schema = json.load(schema_file)
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
        description='Example Action Description',
        schema=schema,
        instrument_id=instrument.id
    )
    assert action.id is not None
    db.session.expunge(action)
    return action


def test_export_action_schema(action, capsys):
    with tempfile.NamedTemporaryFile('r') as schema_file:
        scripts.main([scripts.__file__, 'export_action_schema', str(action.id), schema_file.name])
        schema = json.load(schema_file)
        assert action.schema == schema
    assert 'Success' in capsys.readouterr()[0]


def test_export_action_schema_missing_arguments(action, capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'export_action_schema', str(action.id)])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]


def test_export_action_schema_invalid_action_id(action, capsys):
    with tempfile.NamedTemporaryFile('r') as schema_file:
        with pytest.raises(SystemExit) as exc_info:
            scripts.main([scripts.__file__, 'export_action_schema', action.name, schema_file.name])
        assert exc_info.value != 0
        assert schema_file.read() == ''
    assert 'Error: action_id must be an integer' in capsys.readouterr()[1]


def test_export_action_schema_missing_action(capsys):
    with tempfile.NamedTemporaryFile('r') as schema_file:
        with pytest.raises(SystemExit) as exc_info:
            scripts.main([scripts.__file__, 'export_action_schema', 1, schema_file.name])
        assert exc_info.value != 0
        assert schema_file.read() == ''
    assert 'Error: no action with this id exists' in capsys.readouterr()[1]
