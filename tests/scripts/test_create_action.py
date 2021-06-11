# coding: utf-8
"""

"""

import os
import pytest
import sampledb
from sampledb import db
from sampledb.logic import instruments, actions, languages, action_translations
import sampledb.__main__ as scripts


@pytest.fixture
def instrument():
    instrument = instruments.create_instrument()
    assert instrument.id is not None
    db.session.expunge(instrument)
    return instrument


def test_create_sample_action(instrument, capsys):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert 'Success' in capsys.readouterr()[0]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.instrument_id == instrument.id
    assert action.type_id == sampledb.models.ActionType.SAMPLE_CREATION
    action = action_translations.get_action_with_translation_in_language(
        action_id=action.id,
        language_id=languages.Language.ENGLISH
    )
    assert action.translation.name == name
    assert action.translation.description == description


def test_create_measurement_action(instrument, capsys):
    action_type = 'measurement'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert 'Success' in capsys.readouterr()[0]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.instrument_id == instrument.id
    assert action.type_id == sampledb.models.ActionType.MEASUREMENT
    action = action_translations.get_action_with_translation_in_language(
        action_id=action.id,
        language_id=languages.Language.ENGLISH
    )
    assert action.translation.name == name
    assert action.translation.description == description


def test_create_action_with_action_type_id(instrument, capsys):
    action_type = '-98'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert 'Success' in capsys.readouterr()[0]

    assert len(actions.get_actions()) == 1
    action = actions.get_actions()[0]
    assert action.instrument_id == instrument.id
    assert action.type_id == sampledb.models.ActionType.MEASUREMENT
    action = action_translations.get_action_with_translation_in_language(
        action_id=action.id,
        language_id=languages.Language.ENGLISH
    )
    assert action.translation.name == name
    assert action.translation.description == description


def test_create_action_missing_arguments(instrument, capsys):
    assert len(actions.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', str(instrument.id)])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
    assert len(actions.get_actions()) == 0


def test_create_action_invalid_instrument_id(capsys):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'schemas', 'minimal.json'))
    assert len(actions.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', "instrument", action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert 'Error: instrument_id must be an integer' in capsys.readouterr()[1]
    assert len(actions.get_actions()) == 0


def test_create_action_missing_instrument(capsys):
    action_type = 'sample'
    name = 'Example Action'
    description = 'Example Action Description'
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'schemas', 'minimal.json'))
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
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'schemas', 'minimal.json'))
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
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(sampledb.__file__), 'schemas', 'action.json'))
    assert len(actions.get_actions()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_action', str(instrument.id), action_type, name, description, schema_file_name])
    assert exc_info.value != 0
    assert 'Error: invalid schema:' in capsys.readouterr()[1]
    assert len(actions.get_actions()) == 0
