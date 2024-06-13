# coding: utf-8
"""

"""
import itertools
import uuid

import pytest
import sampledb
from sampledb.logic import actions, errors, instruments, components, action_types

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
    with pytest.raises(AssertionError):
        actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema=SCHEMA,
            component_id=component.id + 1
        )


def test_create_action_fed_missing_component():
    with pytest.raises(AssertionError):
        actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema=SCHEMA,
            fed_id=3
        )


def test_create_action_type_fed(component):
    count = len(action_types.get_action_types())
    action_type = action_types.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        show_in_object_filters=False,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
        enable_instrument_link=False,
        disable_create_objects=False,
        is_template=False,
        fed_id=1,
        component_id=component.id
    )
    assert len(action_types.get_action_types()) == count + 1
    assert action_type.fed_id == 1
    assert action_type.component_id == component.id


def test_create_action_type_fed_missing_component():
    with pytest.raises(AssertionError):
        action_types.create_action_type(
            admin_only=False,
            show_on_frontpage=True,
            show_in_navbar=True,
            show_in_object_filters=False,
            enable_labels=True,
            enable_files=True,
            enable_locations=True,
            enable_publications=True,
            enable_comments=True,
            enable_activity_log=True,
            enable_related_objects=True,
            enable_project_link=True,
            enable_instrument_link=False,
            disable_create_objects=False,
            is_template=False,
            fed_id=1
        )


def test_create_action_type_fed_missing_fed_id(component):
    with pytest.raises(AssertionError):
        action_types.create_action_type(
            admin_only=False,
            show_on_frontpage=True,
            show_in_navbar=True,
            show_in_object_filters=False,
            enable_labels=True,
            enable_files=True,
            enable_locations=True,
            enable_publications=True,
            enable_comments=True,
            enable_activity_log=True,
            enable_related_objects=True,
            enable_project_link=True,
            enable_instrument_link=False,
            disable_create_objects=False,
            is_template=False,
            component_id=component.id + 1
        )


def test_create_action_type_fed_invalid_component(component):
    with pytest.raises(errors.ComponentDoesNotExistError):
        action_types.create_action_type(
            admin_only=False,
            show_on_frontpage=True,
            show_in_navbar=True,
            show_in_object_filters=False,
            enable_labels=True,
            enable_files=True,
            enable_locations=True,
            enable_publications=True,
            enable_comments=True,
            enable_activity_log=True,
            enable_related_objects=True,
            enable_project_link=True,
            enable_instrument_link=False,
            disable_create_objects=False,
            is_template=False,
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
    action_type = action_types.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        show_in_object_filters=False,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
        enable_instrument_link=True,
        disable_create_objects=False,
        is_template=False,
        fed_id=1,
        component_id=component.id
    )
    assert action_type == action_types.get_action_type(1, component.id)


def test_get_fed_action_type_missing_component(component):
    with pytest.raises(errors.ComponentDoesNotExistError):
        assert action_types.get_action_type(1, component.id + 1)


def test_get_missing_fed_action_type(component):
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        assert action_types.get_action_type(1, component.id)


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


def test_sort_actions_for_user():
    component = sampledb.logic.components.add_component(
        uuid=str(uuid.uuid4())
    )
    test_user = sampledb.logic.users.create_user(
        name="User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )
    action_list = []
    fed_id_iter = itertools.count(start=1)
    for is_favorite, has_fed_id, user_name, instrument_name, action_name  in itertools.product(
        [True, False],
        [False, True],
        [None, 'User A', 'User B'],
        [None, 'Instrument A', 'Instrument B'],
        ['Action A', 'Action B']
    ):
        if instrument_name:
            instrument = sampledb.logic.instruments.create_instrument()
            sampledb.logic.instrument_translations.set_instrument_translation(
                language_id=sampledb.logic.languages.Language.ENGLISH,
                instrument_id=instrument.id,
                name=instrument_name,
                description=''
            )
        else:
            instrument = None
        if user_name:
            user = sampledb.logic.users.create_user(
                name=user_name,
                email="example@example.com",
                type=sampledb.models.UserType.PERSON
            )
        else:
            user = None
        if has_fed_id:
            fed_id = next(fed_id_iter)
        else:
            fed_id = None
        action = actions.create_action(
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema=SCHEMA,
            user_id=user.id if user is not None else None,
            fed_id=fed_id,
            component_id=component.id if fed_id is not None else None,
            instrument_id=instrument.id if instrument is not None else None
        )
        sampledb.logic.action_translations.set_action_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_id=action.id,
            name=action_name
        )
        if is_favorite:
            sampledb.logic.favorites.add_favorite_action(
                action_id=action.id,
                user_id=test_user.id
            )
        sampledb.logic.action_permissions.set_user_action_permissions(
            action_id=action.id,
            user_id=test_user.id,
            permissions=sampledb.models.Permissions.READ
        )
        action_list.append(sampledb.logic.actions.get_action(action.id))
    assert sampledb.logic.actions.sort_actions_for_user(action_list, test_user.id) == action_list
    assert sampledb.logic.actions.sort_actions_for_user(action_list[::-1], test_user.id) == action_list
    assert sampledb.logic.actions.sort_actions_for_user(action_list, test_user.id, sort_by_favorite=False) == list(sum(zip(action_list[:len(action_list) // 2], action_list[len(action_list) // 2:]), ()))
    assert sampledb.logic.actions.sort_actions_for_user(action_list[::-1], test_user.id, sort_by_favorite=False) == list(sum(zip(action_list[len(action_list) // 2:], action_list[:len(action_list) // 2]), ()))
