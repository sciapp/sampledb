# coding: utf-8
"""

"""

import datetime

import pytest
import sqlalchemy.dialects.postgresql as postgresql

import sampledb
import sampledb.logic
import sampledb.models
from sampledb import db
from sampledb.models import User, UserType

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture
def user():
    user = User(name="User", email="example@fz-juelich.de", type=UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def user2():
    user = User(name="User 2", email="example@fz-juelich.de", type=UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def action():
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name="",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    return action


def test_create_object(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    assert object1.version_id == 0
    assert object1.action_id == action.id
    assert object1.user_id is not None and object1.user_id == user.id
    assert object1.data == data
    assert object1.schema == action.schema
    assert object1.utc_datetime < datetime.datetime.utcnow()
    assert object1.utc_datetime > datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    assert [object1] == sampledb.logic.objects.get_objects()
    assert object1 == sampledb.logic.objects.get_object(object1.object_id)


def test_create_object_with_missing_action(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    with pytest.raises(sampledb.logic.errors.ActionDoesNotExistError):
        sampledb.logic.objects.create_object(action_id=action.id+1, data=data, user_id=user.id)


def test_create_object_with_missing_user(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id+1)


def test_update_object(user, action, user2) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    assert [object1] == sampledb.logic.objects.get_objects()
    assert object1 == sampledb.logic.objects.get_object(object1.object_id)
    data['name']['text'] = 'Modified Example'
    sampledb.logic.objects.update_object(object1.object_id, data=data, user_id=user2.id)
    object2 = sampledb.logic.objects.get_object(object1.id)
    assert object2.object_id == object1.object_id
    assert object2.version_id == 1
    assert object2.user_id is not None and object2.user_id == user2.id
    assert object2.data['name']['text'] == 'Modified Example'
    assert object2.schema == action.schema
    assert object2.utc_datetime < datetime.datetime.utcnow()
    assert object2.utc_datetime > datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    assert [object2] == sampledb.logic.objects.get_objects()
    assert object2 == sampledb.logic.objects.get_object(object2.object_id)


def test_get_objects(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    object2 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    current_objects = sampledb.logic.objects.get_objects()
    assert current_objects == [object1, object2] or current_objects == [object2, object1]


def test_get_objects_action_filter(user, action) -> None:
    action1 = action
    action2 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name="",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text',
                    'default': 'Action 2 Object ###'
                }
            },
            'required': ['name']
        }
    )
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action1.id, data=data, user_id=user.id)
    object2 = sampledb.logic.objects.create_object(action_id=action2.id, data=data, user_id=user.id)

    current_objects = sampledb.logic.objects.get_objects(action_filter=(db.cast(sampledb.models.Action.schema, postgresql.JSONB) == action1.schema))
    """{
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text',
                    'default': 'Action 2 Object ###'
                }
            },
            'required': ['name']
        }))"""
    assert current_objects == [object1]


def test_get_object(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    object2 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    assert object1 == sampledb.logic.objects.get_object(object1.object_id)
    assert object2 == sampledb.logic.objects.get_object(object2.object_id)
    with pytest.raises(sampledb.logic.errors.ObjectDoesNotExistError):
        assert object2 == sampledb.logic.objects.get_object(object2.object_id+1)


def test_get_object_versions(user, action, user2) -> None:
    user1 = user
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user1.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example 2'
        }
    }
    sampledb.logic.objects.update_object(object1.object_id, data=data, user_id=user2.id)
    object2 = sampledb.logic.objects.get_object(object_id=object1.id)
    object_versions = sampledb.logic.objects.get_object_versions(object1.object_id)
    assert object_versions == [object1, object2]


def test_get_object_versions_errors() -> None:
    with pytest.raises(sampledb.logic.errors.ObjectDoesNotExistError):
        sampledb.logic.objects.get_object_versions(0)


def test_get_object_version(user, action, user2) -> None:
    user1 = user
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user1.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example 2'
        }
    }
    sampledb.logic.objects.update_object(object1.object_id, data=data, user_id=user2.id)
    object2 = sampledb.logic.objects.get_object(object_id=object1.id)
    object_version1 = sampledb.logic.objects.get_object(object1.id, version_id=0)
    object_version2 = sampledb.logic.objects.get_object(object1.id, version_id=1)
    assert object_version1 == object1
    assert object_version2 == object2
    with pytest.raises(sampledb.logic.errors.ObjectVersionDoesNotExistError):
        sampledb.logic.objects.get_object(object1.id, version_id=2)


def test_create_object_invalid_data(user, action) -> None:
    with pytest.raises(sampledb.logic.errors.ValidationError):
        sampledb.logic.objects.create_object(action_id=action.id, data={'test': False}, user_id=user.id)


def test_update_object_invalid_data(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    assert [object1] == sampledb.logic.objects.get_objects()
    assert object1 == sampledb.logic.objects.get_object(object1.object_id)
    with pytest.raises(sampledb.logic.errors.ValidationError):
        sampledb.logic.objects.update_object(object1.object_id, data={'name': 1}, user_id=user.id)


def test_update_missing_object(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    with pytest.raises(sampledb.logic.errors.ObjectDoesNotExistError):
        sampledb.logic.objects.update_object(object1.object_id+1, data=data, user_id=user.id)


def test_restore_object_version(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'Example'
    data['name']['text'] = 'Modified Example'
    sampledb.logic.objects.update_object(object.object_id, data=data, user_id=user.id)
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'Modified Example'
    sampledb.logic.objects.restore_object_version(object_id=object.object_id, version_id=0, user_id=user.id)
    assert sampledb.logic.objects.get_object(object_id=object.object_id).data['name']['text'] == 'Example'


def test_restore_object_version_invalid_data(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    with pytest.raises(sampledb.logic.errors.ObjectVersionDoesNotExistError):
        sampledb.logic.objects.restore_object_version(object_id=object.object_id, version_id=1, user_id=user.id)
    with pytest.raises(sampledb.logic.errors.ObjectDoesNotExistError):
        sampledb.logic.objects.restore_object_version(object_id=42, version_id=0, user_id=user.id)


def test_measurement_referencing_sample(flask_server, user) -> None:
    sample_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Sample Action',
        description='',
        schema={
            'title': 'Sample',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Sample Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        })
    measurement_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.MEASUREMENT,
        name='Measurement Action',
        description='',
        schema={
            'title': 'Measurement',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Measurement Name',
                    'type': 'text'
                },
                'sample': {
                    'title': 'Sample',
                    'type': 'sample'
                }
            },
            'required': ['name']
        })
    sample = sampledb.logic.objects.create_object(
        action_id=sample_action.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Sample"
            }
        },
        user_id=user.id
    )
    sample2 = sampledb.logic.objects.create_object(
        action_id=sample_action.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Sample"
            }
        },
        user_id=user.id
    )
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=sample.id, user_id=user.id)
    assert len(object_log_entries) == 1
    measurement = sampledb.logic.objects.create_object(
        action_id=measurement_action.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Measurement"
            },
            'sample': {
                '_type': 'sample',
                'object_id': sample.id
            }
        },
        user_id=user.id
    )
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=measurement.id, user_id=user.id)
    assert len(object_log_entries) == 1
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=sample.id, user_id=user.id)
    assert len(object_log_entries) == 2
    sampledb.logic.objects.update_object(
        object_id=measurement.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Measurement"
            }
        },
        user_id=user.id
    )
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=measurement.id, user_id=user.id)
    assert len(object_log_entries) == 2
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=sample.id, user_id=user.id)
    assert len(object_log_entries) == 2
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=sample2.id, user_id=user.id)
    assert len(object_log_entries) == 1
    sampledb.logic.objects.update_object(
        object_id=measurement.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Measurement"
            },
            'sample': {
                '_type': 'sample',
                'object_id': sample2.id
            }
        },
        user_id=user.id
    )
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=measurement.id, user_id=user.id)
    assert len(object_log_entries) == 3
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=sample.id, user_id=user.id)
    assert len(object_log_entries) == 2
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=sample2.id, user_id=user.id)
    assert len(object_log_entries) == 2
    sampledb.logic.objects.update_object(
        object_id=measurement.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Measurement"
            },
            'sample': {
                '_type': 'sample',
                'object_id': sample.id
            }
        },
        user_id=user.id
    )
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=measurement.id, user_id=user.id)
    assert len(object_log_entries) == 4
    object_log_entries = sampledb.logic.object_log.get_object_log_entries(object_id=sample.id, user_id=user.id)
    assert len(object_log_entries) == 3
