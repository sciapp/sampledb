# coding: utf-8
"""

"""

import datetime
import pytest

import sampledb
from sampledb.models import User, UserType, Action, Object
from sampledb.logic import comments, objects, actions, components, errors

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'


@pytest.fixture
def component():
    component = components.add_component(address=None, uuid=UUID_1, name='Example component', description='')
    return component


@pytest.fixture
def user():
    user = User(name='User', email="example@example.com", type=UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    return sampledb.logic.users.User.from_database(user)


@pytest.fixture
def action():
    action = actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
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
        instrument_id=None
    )
    return action


@pytest.fixture
def object(user: User, action: Action):
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    return objects.create_object(user_id=user.id, action_id=action.id, data=data)


def test_comments(user: User, object: Object):
    start_datetime = datetime.datetime.now(datetime.timezone.utc)
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 0
    comment_id = comments.create_comment(object_id=object.object_id, user_id=user.id, content="Test 1")
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 1
    comment = comments.get_comments_for_object(object_id=object.object_id)[0]
    assert comment.id == comment_id
    assert comment.user_id == user.id
    assert comment.author == user
    assert comment.object_id == object.object_id
    assert comment.content == "Test 1"
    assert comment.utc_datetime >= start_datetime
    assert comment.utc_datetime <= datetime.datetime.now(datetime.timezone.utc)
    comments.create_comment(object_id=object.object_id, user_id=user.id, content="Test 2")
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 2
    comment2, comment1 = comments.get_comments_for_object(object_id=object.object_id)
    assert comment1.content == "Test 2"
    assert comment2.content == "Test 1"
    assert comment2.utc_datetime >= start_datetime
    assert comment2.utc_datetime <= datetime.datetime.now(datetime.timezone.utc)


def test_create_comment_invalid_object(user, object):
    with pytest.raises(errors.ObjectDoesNotExistError):
        comments.create_comment(object.id + 1, user.id, 'Comment text')


def test_create_comment_invalid_user(user, object):
    with pytest.raises(errors.UserDoesNotExistError):
        comments.create_comment(object.id, user.id + 1, 'Comment text')


def test_create_fed_comment(user, object, component):
    dt = datetime.datetime.now(datetime.timezone.utc)
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 0
    comment = comments.get_comment(comments.create_comment(object.object_id, user.id, 'Comment text', dt, fed_id=1, component_id=component.id, imported_from_component_id=component.id))
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 1
    assert comment.user_id == user.id
    assert comment.author == user
    assert comment.object_id == object.object_id
    assert comment.content == "Comment text"
    assert comment.fed_id == 1
    assert comment.component_id == component.id
    assert comment.imported_from_component_id == component.id
    assert comment.utc_datetime == dt


def test_create_fed_comment_missing_user_id(object, component):
    dt = datetime.datetime.now(datetime.timezone.utc)
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 0
    comment = comments.get_comment(comments.create_comment(object.object_id, None, 'Comment text', dt, fed_id=1, component_id=component.id, imported_from_component_id=component.id))
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 1
    assert comment.user_id is None
    assert comment.author is None
    assert comment.object_id == object.object_id
    assert comment.content == "Comment text"
    assert comment.fed_id == 1
    assert comment.component_id == component.id
    assert comment.imported_from_component_id == component.id
    assert comment.utc_datetime == dt


def test_get_fed_comment(object, user, component):
    dt = datetime.datetime.now(datetime.timezone.utc)
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 0
    comment = comments.get_comment(comments.create_comment(object.object_id, user.id, 'Comment text', dt, fed_id=1, component_id=component.id, imported_from_component_id=component.id))
    assert len(comments.get_comments_for_object(object_id=object.object_id)) == 1
    assert comment == comments.get_comment(1, component.id)


def test_get_fed_comment_missing_component(object, user, component):
    dt = datetime.datetime.now(datetime.timezone.utc)
    comments.create_comment(object.object_id, user.id, 'Comment text', dt, fed_id=1, component_id=component.id, imported_from_component_id=component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        comments.get_comment(1, component.id + 1)


def test_get_fed_comment_missing_comment(object, user, component):
    dt = datetime.datetime.now(datetime.timezone.utc)
    comments.create_comment(object.object_id, user.id, 'Comment text', dt, fed_id=1, component_id=component.id, imported_from_component_id=component.id)
    with pytest.raises(errors.CommentDoesNotExistError):
        comments.get_comment(2, component.id)
