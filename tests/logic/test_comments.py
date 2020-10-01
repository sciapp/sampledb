# coding: utf-8
"""

"""

import datetime
import pytest

import sampledb
from sampledb.models import User, UserType, Action, ActionType, Object
from sampledb.logic import comments, objects, actions


@pytest.fixture
def user():
    user = User(name='User', email="example@fz-juelich.de", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return user


@pytest.fixture
def action():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Sample Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        description='',
        instrument_id=None
    )
    return action


@pytest.fixture
def object(user: User, action: Action):
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    return objects.create_object(user_id=user.id, action_id=action.id, data=data)


def test_comments(user: User, object: Object):
    start_datetime = datetime.datetime.utcnow()
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 0
    comments.create_comment(object_id=object.object_id, user_id=user.id, content="Test 1")
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 1
    comment = comments.get_comments_for_object(object_id=object.object_id)[0]
    assert comment.user_id == user.id
    assert comment.author == user
    assert comment.object_id == object.object_id
    assert comment.content == "Test 1"
    assert comment.utc_datetime >= start_datetime
    assert comment.utc_datetime <= datetime.datetime.utcnow()
    comments.create_comment(object_id=object.object_id, user_id=user.id, content="Test 2")
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 2
    comment2, comment1 = comments.get_comments_for_object(object_id=object.object_id)
    assert comment1.content == "Test 2"
    assert comment2.content == "Test 1"
    assert comment2.utc_datetime >= start_datetime
    assert comment2.utc_datetime <= datetime.datetime.utcnow()
