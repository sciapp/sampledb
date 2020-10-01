# coding: utf-8
"""

"""

import requests
import pytest
import typing
from bs4 import BeautifulSoup

import sampledb
from sampledb import db
import sampledb.logic
import sampledb.models
from sampledb.models import User, Action


@pytest.fixture
def user() -> User:
    user = sampledb.models.User(
        name="User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def action() -> Action:
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


def test_get_objects_sort_by_object_id(flask_server: typing.Any, user: User, action: Action):
    for i in range(10):
        sampledb.logic.objects.create_object(action_id=action.id, data={
            'name': {
                '_type': 'text',
                'text': str(i)
            }
        }, user_id=user.id)
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200

    r = session.get(flask_server.base_url + 'objects')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    rows = document.find(id='table-objects').find('tbody').find_all('tr')
    assert len(rows) == 10
    for i, row in enumerate(rows):
        assert row.find('th').text == str(10-i)

    r = session.get(flask_server.base_url + 'objects?sortby=_object_id&order=desc')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    rows = document.find(id='table-objects').find('tbody').find_all('tr')
    assert len(rows) == 10
    for i, row in enumerate(rows):
        assert row.find('th').text == str(10-i)

    r = session.get(flask_server.base_url + 'objects?sortby=_object_id&order=asc')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    rows = document.find(id='table-objects').find('tbody').find_all('tr')
    assert len(rows) == 10
    for i, row in enumerate(rows):
        assert row.find('th').text == str(1+i)
