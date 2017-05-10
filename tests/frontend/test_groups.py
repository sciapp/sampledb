# coding: utf-8
"""

"""

import flask
import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
import sampledb.logic

from tests.test_utils import flask_server, app, app_context


@pytest.fixture
def user_session(flask_server):
    user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    session.user_id = user.id
    return session


def test_list_groups(flask_server, user_session):
    other_user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()

    r = user_session.get(flask_server.base_url + 'groups/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    group_anchors = document.find('ul', id='groups_list').find_all('a')
    assert len(group_anchors) == 0

    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id)

    r = user_session.get(flask_server.base_url + 'groups/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    group_anchors = document.find('ul', id='groups_list').find_all('a')
    assert len(group_anchors) == 1
    group_url = group_anchors[0]['href']
    assert group_url.endswith('/groups/{}'.format(group_id))


def test_list_user_groups(flask_server, user_session):
    other_user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()

    r = user_session.get(flask_server.base_url + 'groups?user_id={}'.format(user_session.user_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    group_anchors = document.find('ul', id='groups_list').find_all('a')
    assert len(group_anchors) == 0

    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id)

    r = user_session.get(flask_server.base_url + 'groups?user_id={}'.format(user_session.user_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    group_anchors = document.find('ul', id='groups_list').find_all('a')
    assert len(group_anchors) == 0

    group_id = sampledb.logic.groups.create_group("Example Group 2", "", user_session.user_id)

    r = user_session.get(flask_server.base_url + 'groups?user_id={}'.format(user_session.user_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    group_anchors = document.find('ul', id='groups_list').find_all('a')
    assert len(group_anchors) == 1
    group_url = group_anchors[0]['href']
    assert group_url.endswith('/groups/{}'.format(group_id))


def test_view_group(flask_server, user_session):
    group_id = sampledb.logic.groups.create_group("Example Group", "", user_session.user_id)

    r = user_session.get(flask_server.base_url + 'groups/{}'.format(group_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('h3').text == 'Group #{}: Example Group'.format(group_id)


def test_create_group(flask_server, user_session):
    r = user_session.get(flask_server.base_url + 'groups/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    create_group_form = document.find(id='createGroupModal').find('form')
    assert create_group_form is not None

    csrf_token = create_group_form.find('input', {'name': 'csrf_token'})['value']

    r = user_session.post(flask_server.base_url + 'groups/', data={
        'create': 'create',
        'csrf_token': csrf_token,
        'name': 'Example Group',
        'description': 'Example Description'
    }, allow_redirects=False)
    assert r.status_code == 302
    # Force reloading of objects
    sampledb.db.session.rollback()

    groups = sampledb.logic.groups.get_user_groups(user_session.user_id)
    assert len(groups) == 1
    group = groups[0]
    assert group.name == 'Example Group'
    assert group.description == 'Example Description'

    assert r.headers['Location'] == flask_server.base_url + 'groups/{}'.format(group.id)


def test_leave_group(flask_server, user_session):
    group_id = sampledb.logic.groups.create_group("Example Group", "", user_session.user_id)

    r = user_session.get(flask_server.base_url + 'groups/{}'.format(group_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    leave_group_form = document.find('form', id='leaveGroupForm')
    csrf_token = leave_group_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'groups/{}'.format(group_id), data={
        'leave': 'leave',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    assert len(sampledb.logic.groups.get_user_groups(user_session.user_id)) == 0


def test_edit_group(flask_server, user_session):
    group_id = sampledb.logic.groups.create_group("Example Group", "", user_session.user_id)

    r = user_session.get(flask_server.base_url + 'groups/{}'.format(group_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    edit_group_form = document.find(id='editGroupModal').find('form')
    csrf_token = edit_group_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'groups/{}'.format(group_id), data={
        'edit': 'edit',
        'csrf_token': csrf_token,
        'name': 'Test Group',
        'description': 'Test Description'
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    group = sampledb.logic.groups.get_group(group_id)
    assert group.name == 'Test Group'
    assert group.description == 'Test Description'


def test_add_user(flask_server, user_session):
    group_id = sampledb.logic.groups.create_group("Example Group", "", user_session.user_id)

    new_user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(new_user)
    sampledb.db.session.commit()

    assert len(sampledb.logic.groups.get_user_groups(new_user.id)) == 0

    r = user_session.get(flask_server.base_url + 'groups/{}'.format(group_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    invite_user_form = document.find(id='inviteUserModal').find('form')
    csrf_token = invite_user_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'groups/{}'.format(group_id), data={
        'add_user': 'add_user',
        'csrf_token': csrf_token,
        'user_id': str(new_user.id)
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    assert len(sampledb.logic.groups.get_user_groups(new_user.id)) == 1
    assert sampledb.logic.groups.get_user_groups(new_user.id)[0].id == group_id
