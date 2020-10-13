# coding: utf-8
"""

"""

import os
import pytest
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


def test_create_sample_action(instrument, capsys):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert 'Success' in capsys.readouterr()[0]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.name == name
    assert action.description == description
    assert action.instrument_id == instrument.id
    assert action.type_id == sampledb.models.ActionType.SAMPLE_CREATION


def test_create_measurement_action(instrument, capsys):
    action_type = 'measurement'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert 'Success' in capsys.readouterr()[0]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.name == name
    assert action.description == description
    assert action.instrument_id == instrument.id
    assert action.type_id == sampledb.models.ActionType.MEASUREMENT


def test_create_action_with_action_type_id(instrument, capsys):
    action_type = '-98'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert 'Success' in capsys.readouterr()[0]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.name == name
    assert action.description == description
    assert action.instrument_id == instrument.id
    assert action.type_id == sampledb.models.ActionType.MEASUREMENT


def test_create_action_missing_arguments(instrument, capsys):
    assert len(actions.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', str(instrument.id)])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
    assert len(actions.get_actions()) == 0


def test_create_action_invalid_instrument_id(instrument, capsys):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', instrument.name, action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert 'Error: instrument_id must be an integer' in capsys.readouterr()[1]
    assert len(actions.get_actions()) == 0


def test_create_action_missing_instrument(capsys):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', '1', action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert 'Error: no instrument with this id exists' in capsys.readouterr()[1]
    assert len(actions.get_actions()) == 0


def test_create_action_invalid_type(instrument, capsys):
    action_type = 'sample_creation'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert 'Error: action type must be one of the following:\n- "sample" (for Sample Creation)\n- "measurement" (for Measurement)\n- "simulation" (for Simulation)\n- "-99" (for Sample Creation)\n- "-98" (for Measurement)\n- "-97" (for Simulation)\n' in capsys.readouterr()[1]
    assert len(actions.get_actions()) == 0


def test_create_action_invalid_schema(instrument, capsys):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'action.json'))
    assert len(actions.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert 'Error: invalid schema:' in capsys.readouterr()[1]
    assert len(actions.get_actions()) == 0
