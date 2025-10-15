import copy
import pytest

import sampledb.logic
import sampledb.models
from sampledb.models import AutomaticSchemaUpdateStatus


@pytest.fixture
def admin():
    user = sampledb.logic.users.create_user(
        name='Administrator',
        email='administrator@example.com',
        type=sampledb.models.UserType.PERSON
    )
    sampledb.logic.users.set_user_administrator(user_id=user.id, is_admin=True)
    return sampledb.logic.users.get_user(user_id=user.id)

@pytest.fixture
def action():
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            "title": "Object Information",
            "type": "object",
            "properties": {
                "name": {
                    "type": "text",
                    "title": "Name"
                }
            },
            "required": ["name"]
        }
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(
        action_id=action.id,
        permissions=sampledb.models.Permissions.READ
    )
    return action

@pytest.fixture
def object(admin, action):
    return sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            "name": {
                "_type": "text",
                "text": "Example"
            }
        },
        user_id=admin.id
    )

def test_updatable_objects_checks(admin, action, object):
    assert sampledb.logic.automatic_schema_updates.get_updatable_objects_checks() == []
    updatable_objects_check = sampledb.logic.automatic_schema_updates.start_updatable_objects_checks(
        user_id=admin.id,
        action_ids=None,
    )
    assert sampledb.logic.automatic_schema_updates.get_updatable_objects_check(updatable_objects_check.id) == updatable_objects_check
    with pytest.raises(sampledb.logic.errors.UpdatableObjectsCheckDoesNotExistError):
        assert sampledb.logic.automatic_schema_updates.get_updatable_objects_check(updatable_objects_check.id + 1)
    updatable_objects_checks = sampledb.logic.automatic_schema_updates.get_updatable_objects_checks()
    assert len(updatable_objects_checks) == 1
    assert updatable_objects_checks[0].id == updatable_objects_check.id
    assert updatable_objects_check.status == sampledb.models.UpdatableObjectsCheckStatus.DONE
    assert updatable_objects_check.result == {
        'automatically_updatable_objects': [],
        'manually_updatable_objects': [],
        'previous_object_id': object.id
    }
    sampledb.logic.automatic_schema_updates.set_updatable_objects_check_status(
        updatable_objects_check_id=updatable_objects_check.id,
        status=sampledb.models.UpdatableObjectsCheckStatus.IN_PROGRESS,
        result={
            'automatically_updatable_objects': [],
            'manually_updatable_objects': [],
            'previous_object_id': -1
        }
    )
    with pytest.raises(sampledb.logic.errors.UpdatableObjectsCheckDoesNotExistError):
        sampledb.logic.automatic_schema_updates.set_updatable_objects_check_status(
            updatable_objects_check_id=updatable_objects_check.id + 1,
            status=sampledb.models.UpdatableObjectsCheckStatus.IN_PROGRESS,
            result={
                'automatically_updatable_objects': [],
                'manually_updatable_objects': [],
                'previous_object_id': -1
            }
        )
    with pytest.raises(sampledb.logic.errors.UpdatableObjectsCheckAlreadyInProgressError):
        updatable_objects_check = sampledb.logic.automatic_schema_updates.start_updatable_objects_checks(
            user_id=admin.id,
            action_ids=None,
        )
    updatable_objects_checks = sampledb.logic.automatic_schema_updates.get_updatable_objects_checks()
    assert len(updatable_objects_checks) == 1
    assert updatable_objects_checks[0].id == updatable_objects_check.id

    schema = copy.deepcopy(action.schema)
    schema['style'] = 'test'
    sampledb.logic.actions.update_action(
        action_id=action.id,
        schema=schema
    )
    sampledb.logic.background_tasks.post_check_for_automatic_schema_updates_task(updatable_objects_check_id=updatable_objects_check.id)
    updatable_objects_check = sampledb.logic.automatic_schema_updates.get_updatable_objects_check(updatable_objects_check.id)
    assert updatable_objects_check.status == sampledb.models.UpdatableObjectsCheckStatus.DONE
    assert updatable_objects_check.result == {
        'automatically_updatable_objects': [[object.id, 0, []]],
        'manually_updatable_objects': [],
        'previous_object_id': object.id
    }

    schema = copy.deepcopy(action.schema)
    schema['properties']['other'] = schema['properties']['name']
    schema['required'] = ['name', 'other']
    sampledb.logic.actions.update_action(
        action_id=action.id,
        schema=schema
    )
    updatable_objects_check = sampledb.logic.automatic_schema_updates.start_updatable_objects_checks(
        user_id=admin.id,
        action_ids=None,
    )
    assert updatable_objects_check.status == sampledb.models.UpdatableObjectsCheckStatus.DONE
    assert updatable_objects_check.result == {
        'automatically_updatable_objects': [],
        'manually_updatable_objects': [[object.id, 0, ["Added properties: 'other'."]]],
        'previous_object_id': object.id
    }


def test_automatic_schema_updates(admin, action, object):
    assert sampledb.logic.automatic_schema_updates.get_automatic_schema_updates() == []
    updatable_objects_check = sampledb.logic.automatic_schema_updates.start_updatable_objects_checks(
        user_id=admin.id,
        action_ids=None,
    )
    automatic_schema_update = sampledb.logic.automatic_schema_updates.start_automatic_schema_updates(
        user_id=admin.id,
        updatable_objects_check_id=updatable_objects_check.id,
        object_ids=[]
    )
    assert automatic_schema_update.status == AutomaticSchemaUpdateStatus.DONE
    assert automatic_schema_update.result == {
        'object_ids_failure': [],
        'object_ids_success': [],
    }
    automatic_schema_updates = sampledb.logic.automatic_schema_updates.get_automatic_schema_updates()
    assert len(automatic_schema_updates) == 1
    assert automatic_schema_updates[0].id == automatic_schema_update.id
    assert sampledb.logic.automatic_schema_updates.get_automatic_schema_update(automatic_schema_update.id) == automatic_schema_update
    with pytest.raises(sampledb.logic.errors.AutomaticSchemaUpdateDoesNotExistError):
        sampledb.logic.automatic_schema_updates.get_automatic_schema_update(automatic_schema_update.id + 1)

    sampledb.logic.automatic_schema_updates.set_automatic_schema_update_status(
        automatic_schema_update_id=automatic_schema_update.id,
        status=AutomaticSchemaUpdateStatus.IN_PROGRESS,
        result={
            'object_ids_failure': [object.id],
            'object_ids_success': [],
        }
    )
    automatic_schema_update = sampledb.logic.automatic_schema_updates.get_automatic_schema_update(automatic_schema_update.id)
    assert automatic_schema_update.status == AutomaticSchemaUpdateStatus.IN_PROGRESS
    assert automatic_schema_update.result == {
        'object_ids_failure': [object.id],
        'object_ids_success': [],
    }
    with pytest.raises(sampledb.logic.errors.AutomaticSchemaUpdateDoesNotExistError):
        sampledb.logic.automatic_schema_updates.set_automatic_schema_update_status(
            automatic_schema_update_id=automatic_schema_update.id + 1,
            status=AutomaticSchemaUpdateStatus.IN_PROGRESS,
            result={
                'object_ids_failure': [object.id],
                'object_ids_success': [],
            }
        )

    schema = copy.deepcopy(action.schema)
    schema['style'] = 'test'
    sampledb.logic.actions.update_action(
        action_id=action.id,
        schema=schema
    )
    updatable_objects_check = sampledb.logic.automatic_schema_updates.start_updatable_objects_checks(
        user_id=admin.id,
        action_ids=None,
    )
    assert updatable_objects_check.result == {
        'automatically_updatable_objects': [[object.id, 0, []]],
        'manually_updatable_objects': [],
        'previous_object_id': object.id,
    }
    with pytest.raises(sampledb.logic.errors.AutomaticSchemaUpdateAlreadyInProgressError):
        sampledb.logic.automatic_schema_updates.start_automatic_schema_updates(
            user_id=admin.id,
            updatable_objects_check_id=updatable_objects_check.id,
            object_ids=[object.id]
        )
    sampledb.logic.automatic_schema_updates.set_automatic_schema_update_status(
        automatic_schema_update_id=automatic_schema_update.id,
        status=AutomaticSchemaUpdateStatus.DONE,
        result={
            'object_ids_failure': [],
            'object_ids_success': [],
        }
    )
    automatic_schema_update = sampledb.logic.automatic_schema_updates.start_automatic_schema_updates(
        user_id=admin.id,
        updatable_objects_check_id=updatable_objects_check.id,
        object_ids=[object.id]
    )
    assert automatic_schema_update.status == AutomaticSchemaUpdateStatus.DONE
    assert automatic_schema_update.result == {
        'object_ids_failure': [],
        'object_ids_success': [object.id],
    }
    object = sampledb.logic.objects.get_object(object.id)
    assert object.version_id == 1
    assert object.user_id == admin.id

    schema = copy.deepcopy(action.schema)
    schema['style'] = 'other'
    sampledb.logic.actions.update_action(
        action_id=action.id,
        schema=schema
    )
    updatable_objects_check = sampledb.logic.automatic_schema_updates.start_updatable_objects_checks(
        user_id=admin.id,
        action_ids=None,
    )
    assert updatable_objects_check.result == {
        'automatically_updatable_objects': [[object.id, 1, []]],
        'manually_updatable_objects': [],
        'previous_object_id': object.id,
    }
    schema['properties']['other'] = schema['properties']['name']
    schema['required'].append('other')
    sampledb.logic.actions.update_action(
        action_id=action.id,
        schema=schema
    )
    automatic_schema_update = sampledb.logic.automatic_schema_updates.start_automatic_schema_updates(
        user_id=admin.id,
        updatable_objects_check_id=updatable_objects_check.id,
        object_ids=[object.id]
    )
    assert automatic_schema_update.status == AutomaticSchemaUpdateStatus.DONE
    assert automatic_schema_update.result == {
        'object_ids_failure': [object.id],
        'object_ids_success': [],
    }
    object = sampledb.logic.objects.get_object(object.id)
    assert object.version_id == 1
