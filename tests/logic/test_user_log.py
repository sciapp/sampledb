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
        email="example1@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user


@pytest.fixture
def user2():
    user = sampledb.models.User(
        name="User",
        email="example2@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
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
    sampledb.logic.user_log.invite_user(user1.id, "example@fz-juelich.de")
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
    sampledb.logic.object_permissions.set_object_public(object_id=object.id, is_public=True)
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user1.id)) == 4
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user2.id)) == 1
    sampledb.logic.user_log.create_batch(user1.id, [object.id, 21])
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user1.id)) == 5
    assert len(sampledb.logic.user_log.get_user_log_entries(user1.id, as_user_id=user2.id)) == 2


def test_get_user_related_object_ids(user1, user2):
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
