# coding: utf-8
"""

"""

import pytest
import sampledb
from sampledb.logic import actions, errors, instruments, components

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

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'


@pytest.fixture
def component():
    component = components.add_component(address=None, uuid=UUID_1, name='Example component', description='')
    return component


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


def test_create_action_missing_schema():
    with pytest.raises(TypeError):
        actions.create_action(
            schema=SCHEMA
        )


def test_create_action_missing_action_type():
    with pytest.raises(TypeError):
        actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION
        )


def test_create_action_fed(component):
    assert len(actions.get_actions()) == 0
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA,
        fed_id=3,
        component_id=component.id
    )
    assert action.schema == SCHEMA
    assert len(actions.get_actions()) == 1
    assert action == actions.get_action(action_id=action.id)


def test_create_action_fed_missing_action_type(component):
    assert len(actions.get_actions()) == 0
    action = actions.create_action(
        action_type_id=None,
        schema=SCHEMA,
        fed_id=3,
        component_id=component.id
    )
    assert action.schema == SCHEMA
    assert action.type_id is None
    assert len(actions.get_actions()) == 1
    assert action == actions.get_action(action_id=action.id)


def test_create_action_fed_missing_schema(component):
    assert len(actions.get_actions()) == 0
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=None,
        fed_id=3,
        component_id=component.id
    )
    assert action.schema is None
    assert len(actions.get_actions()) == 1
    assert action == actions.get_action(action_id=action.id)


def test_create_action_fed_invalid_component(component):
    with pytest.raises(errors.ComponentDoesNotExistError):
        actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema=SCHEMA,
            fed_id=3,
            component_id=component.id + 1
        )


def test_create_action_fed_missing_fed_id(component):
    with pytest.raises(TypeError):
        actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema=SCHEMA,
            component_id=component.id + 1
        )


def test_create_action_fed_missing_component():
    with pytest.raises(TypeError):
        actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema=SCHEMA,
            fed_id=3
        )


def test_create_action_type_fed(component):
    count = len(actions.get_action_types())
    action_type = actions.create_action_type(
        False, True, True, True, True, True, True, True, True, True, True, False, False,
        fed_id=1,
        component_id=component.id
    )
    assert len(actions.get_action_types()) == count + 1
    assert action_type.fed_id == 1
    assert action_type.component_id == component.id


def test_create_action_type_fed_missing_component():
    with pytest.raises(TypeError):
        actions.create_action_type(
            False, True, True, True, True, True, True, True, True, True, True, False, False,
            fed_id=1
        )


def test_create_action_type_fed_missing_fed_id(component):
    with pytest.raises(TypeError):
        actions.create_action_type(
            False, True, True, True, True, True, True, True, True, True, True, False, False,
            component_id=component.id + 1
        )


def test_create_action_type_fed_invalid_component(component):
    with pytest.raises(errors.ComponentDoesNotExistError):
        actions.create_action_type(
            False, True, True, True, True, True, True, True, True, True, True, False, False,
            fed_id=1,
            component_id=component.id + 1
        )


def test_get_missing_action():
    assert len(actions.get_actions()) == 0
    action = actions.create_action(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION, schema=SCHEMA)
    with pytest.raises(errors.ActionDoesNotExistError):
        actions.get_action(action.id + 1)


def test_get_fed_action(component):
    assert len(actions.get_actions()) == 0
    action = actions.create_action(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION, schema=SCHEMA, fed_id=3, component_id=component.id)
    assert action == actions.get_action(3, component.id)


def test_get_fed_action_missing_component(component):
    with pytest.raises(errors.ComponentDoesNotExistError):
        assert actions.get_action(3, component.id + 1)


def test_get_missing_fed_action(component):
    assert len(actions.get_actions()) == 0
    with pytest.raises(errors.ActionDoesNotExistError):
        assert actions.get_action(3, component.id)


def test_get_fed_action_type(component):
    action_type = actions.create_action_type(
        False, True, True, True, True, True, True, True, True, True, True, False, False,
        fed_id=1,
        component_id=component.id
    )
    assert action_type == actions.get_action_type(1, component.id)


def test_get_fed_action_type_missing_component(component):
    with pytest.raises(errors.ComponentDoesNotExistError):
        assert actions.get_action_type(1, component.id + 1)


def test_get_missing_fed_action_type(component):
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        assert actions.get_action_type(1, component.id)


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
        actions.update_action(action_id=action.id + 1, schema=SCHEMA)


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
    assert actions.get_actions(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION) == [sample_action]
    assert actions.get_actions(action_type_id=sampledb.models.ActionType.MEASUREMENT) == [measurement_action]

    instrument = instruments.create_instrument()
    instrument_action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA,
        instrument_id=instrument.id
    )
    assert actions.get_actions(
        instrument_id=instrument.id
    ) == [instrument_action]
    assert actions.get_actions(
        instrument_id=instrument.id,
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION
    ) == [instrument_action]
    assert actions.get_actions(
        instrument_id=instrument.id,
        action_type_id=sampledb.models.ActionType.MEASUREMENT
    ) == []


def test_create_user_action():
    user = sampledb.models.User(name="Testuser", email="example@example.com", type=sampledb.models.UserType.PERSON)
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


def test_check_action_exists():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA
    )
    actions.check_action_exists(action.id)
    with pytest.raises(errors.ActionDoesNotExistError):
        actions.check_action_exists(action.id + 1)


def test_get_action_owner_id():
    user = sampledb.logic.users.create_user(
        name="User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )
    action1 = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA
    )
    action2 = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=SCHEMA,
        user_id=user.id
    )
    assert actions.get_action_owner_id(action1.id) is None
    assert actions.get_action_owner_id(action2.id) == user.id
    with pytest.raises(errors.ActionDoesNotExistError):
        actions.get_action_owner_id(action2.id + 1)
