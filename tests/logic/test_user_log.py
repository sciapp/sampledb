# coding: utf-8
"""

"""

import pytest
import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def user1():
    user = sampledb.models.User(
        name="User",
        email="example1@example.com",
        type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user


@pytest.fixture
def user2():
    user = sampledb.models.User(
        name="User",
        email="example2@example.com",
        type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user


@pytest.fixture
def action():
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {

                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    return action


def test_get_user_log_entries(user1, user2, action):
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id)) == 0
    sampledb.logic.user_log.invite_user(user1.id, "example@example.com")
    sampledb.logic.user_log.create_object(user1.id, 42)
    sampledb.logic.user_log.create_batch(user1.id, [42, 21])
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id)) == 3
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user1.id)) == 3
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user2.id)) == 0
    object = sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user1.id)
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user1.id)) == 4
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user2.id)) == 0
    sampledb.logic.object_permissions.set_object_permissions_for_all_users(object.id, sampledb.models.Permissions.READ)
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user1.id)) == 4
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user2.id)) == 1
    sampledb.logic.user_log.create_batch(user1.id, [object.id, 21])
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user1.id)) == 5
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user2.id)) == 2


def test_get_user_related_object_ids(user1, user2, action):
    assert not sampledb.logic.user_log.get_user_related_object_ids(user1.id)
    assert not sampledb.logic.user_log.get_user_related_object_ids(user2.id)
    sampledb.logic.user_log.create_object(user1.id, 1)
    sampledb.logic.user_log.create_object(user1.id, 2)
    assert sampledb.logic.user_log.get_user_related_object_ids(user1.id) == {1, 2}
    assert not sampledb.logic.user_log.get_user_related_object_ids(user2.id)
    sampledb.logic.user_log.edit_object(user1.id, 2, 1)
    assert sampledb.logic.user_log.get_user_related_object_ids(user1.id) == {1, 2}
    assert not sampledb.logic.user_log.get_user_related_object_ids(user2.id)
    sampledb.logic.user_log.create_batch(user2.id, [3, 4])
    assert sampledb.logic.user_log.get_user_related_object_ids(user1.id) == {1, 2}
    assert sampledb.logic.user_log.get_user_related_object_ids(user2.id) == {3, 4}


def test_get_user_related_object_ids_with_location_assignments(user1, user2, action):
    assert sampledb.logic.user_log.get_user_related_object_ids(user1.id) == set()
    assert sampledb.logic.user_log.get_user_related_object_ids(user2.id) == set()
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user1.id)
    location = sampledb.logic.locations.create_location('test', '', None, user1.id, type_id=sampledb.logic.locations.LocationType.LOCATION)
    assert sampledb.logic.user_log.get_user_related_object_ids(user1.id) == {object1.id}
    assert sampledb.logic.user_log.get_user_related_object_ids(user2.id) == set()
    sampledb.logic.locations.create_notification_for_being_assigned_as_responsible_user = lambda *args, **kwargs: None
    sampledb.logic.locations.assign_location_to_object(object1.id, location.id, user2.id, user1.id, '')
    assert sampledb.logic.user_log.get_user_related_object_ids(user1.id) == {object1.id}
    # being assigned as responsible can mean that the object is related to the
    # user, but it is not part of the user's log and does not fit the way that
    # this function is used so far, as in 'objects with activity by user X'
    assert sampledb.logic.user_log.get_user_related_object_ids(user2.id) == set()
    sampledb.logic.locations.assign_location_to_object(object1.id, location.id, None, user2.id, '')
    assert sampledb.logic.user_log.get_user_related_object_ids(user1.id) == {object1.id}
    assert sampledb.logic.user_log.get_user_related_object_ids(user2.id) == {object1.id}

