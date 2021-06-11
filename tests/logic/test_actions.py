# coding: utf-8
"""

"""

import pytest
import sampledb
from sampledb.logic import actions, errors, instruments, users

SCHEMA = {
        'title': 'Example Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Example Attribute',
                'type': 'text'
            }
        },
        'required': ['name']
    }


def test_create_independent_action():
    assert len(actions.get_actions()) == 0
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA
    )
    assert action.schema == SCHEMA
    assert len(actions.get_actions()) == 1
    assert action == actions.get_action(action_id=action.id)


def test_create_instrument_action():
    instrument = instruments.create_instrument()
    assert len(actions.get_actions()) == 0
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA,
        instrument_id=instrument.id
    )
    assert action.schema == SCHEMA
    assert len(actions.get_actions()) == 1
    assert action == actions.get_action(action_id=action.id)
    assert action.instrument == instrument


def test_create_missing_instrument_action():
    instrument = instruments.create_instrument()
    assert len(actions.get_actions()) == 0
    with pytest.raises(errors.InstrumentDoesNotExistError):
        actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema=SCHEMA,
            instrument_id=instrument.id + 1
        )


def test_create_action_invalid_schema():
    schema = {
        'type': 'invalid'
    }
    with pytest.raises(errors.ValidationError):
        actions.create_action(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION, schema=schema)


def test_get_missing_action():
    assert len(actions.get_actions()) == 0
    action = actions.create_action(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION, schema=SCHEMA)
    with pytest.raises(errors.ActionDoesNotExistError):
        actions.get_action(action.id+1)


def test_update_action():
    action = actions.create_action(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION, schema=SCHEMA)
    actions.update_action(
        action_id=action.id,
        schema=SCHEMA
    )
    action = actions.get_action(action_id=action.id)
    assert action.schema == SCHEMA


def test_update_missing_action():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA
    )
    with pytest.raises(errors.ActionDoesNotExistError):
        actions.update_action(action_id=action.id+1, schema=SCHEMA)


def test_get_actions():
    measurement_action = actions.create_action(
        action_type_id=sampledb.models.ActionType.MEASUREMENT,
        schema=SCHEMA
    )
    sample_action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA
    )
    assert actions.get_actions() == [measurement_action, sample_action] or actions.get_actions() == [sample_action, measurement_action]
    assert actions.get_actions(sampledb.models.ActionType.SAMPLE_CREATION) == [sample_action]
    assert actions.get_actions(sampledb.models.ActionType.MEASUREMENT) == [measurement_action]


def test_create_user_action():
    user = users.User(name="Testuser", email="example@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(actions.get_actions()) == 0
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA,
        user_id=user.id
    )
    assert action.schema == SCHEMA
    assert action.user_id == user.id
    assert len(actions.get_actions()) == 1
    assert action == actions.get_action(action_id=action.id)
