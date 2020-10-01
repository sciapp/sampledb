# coding: utf-8
"""

"""

import datetime
import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
import sampledb.logic

from sampledb.models import User, Action


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture
def action():
    action = sampledb.logic.actions.create_action(
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
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def object_id(user: User, action: Action) -> int:
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    return sampledb.logic.objects.create_object(user_id=user.id, action_id=action.id, data=data).id


def test_view_comments(flask_server, user: User, object_id: int):
    assert len(sampledb.logic.comments.get_comments_for_object(object_id=object_id)) == 0
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}'.format(object_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    comment_divs = [div for div in document.find_all('div') if div.has_attr('id') in div and div['id'].startswith('comment-')]
    assert len(comment_divs) == 0
    sampledb.logic.comments.create_comment(object_id=object_id, user_id=user.id, content="Test")
    r = session.get(flask_server.base_url + 'objects/{}'.format(object_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    comment_divs = [div for div in document.find_all('div') if div.has_attr('id') and div['id'].startswith('comment-')]
    assert len(comment_divs) == 1
    comment = sampledb.logic.comments.get_comments_for_object(object_id=object_id)[0]
    assert comment_divs[0]['id'] == 'comment-{}'.format(comment.id)


def test_post_comments(flask_server, user: User, object_id: int):
    assert len(sampledb.logic.comments.get_comments_for_object(object_id=object_id)) == 0
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'objects/{}'.format(object_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    comment_form = document.find('form', {'action': '/objects/{}/comments/'.format(object_id), 'method': 'post'})
    csrf_token = comment_form.find('input', {'name': 'csrf_token'})['value']
    content_name = comment_form.find('textarea')['name']
    data = {
        'csrf_token': csrf_token,
        content_name: 'Test Comment'
    }
    start_datetime = datetime.datetime.utcnow()
    r = session.post(flask_server.base_url + 'objects/{}/comments/'.format(object_id), data=data)
    assert r.status_code == 200
    assert len(sampledb.logic.comments.get_comments_for_object(object_id=object_id)) == 1
    comment = sampledb.logic.comments.get_comments_for_object(object_id=object_id)[0]
    assert comment.user_id == user.id
    assert comment.author == user
    assert comment.object_id == object_id
    assert comment.content == "Test Comment"
    assert comment.utc_datetime >= start_datetime
    assert comment.utc_datetime <= datetime.datetime.utcnow()

