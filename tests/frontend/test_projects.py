# coding: utf-8
"""

"""

import flask
import requests
import pytest
import bcrypt
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
import sampledb.logic
from sampledb.logic.authentication import add_authentication_to_db

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


@pytest.fixture
def user(flask_server):
    user = sampledb.models.User(name="Basic User2", email="example2@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    # force attribute refresh
    password = 'abc.123'
    confirmed = True
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    log = {
        'login': 'example@fz-juelich.de',
        'bcrypt_hash': pw_hash
    }
    add_authentication_to_db(log, sampledb.models.AuthenticationType.EMAIL, confirmed, user.id)
    # force attribute refresh
    assert user.id is not None
    # Check if authentication-method add to db
    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 1
    return user


def test_list_projects(flask_server, user_session):
    other_user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()

    r = user_session.get(flask_server.base_url + 'projects/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 0

    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id

    r = user_session.get(flask_server.base_url + 'projects/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 1
    project_url = project_anchors[0]['href']
    assert project_url.endswith('/projects/{}'.format(project_id))


def test_list_user_projects(flask_server, user_session):
    other_user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format(user_session.user_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 0

    other_project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format(user_session.user_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 0

    project_id = sampledb.logic.projects.create_project("Example Project 2", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format(user_session.user_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 1
    project_url = project_anchors[0]['href']
    assert project_url.endswith('/projects/{}'.format(project_id))

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format('unknown'))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 2
    assert any(project_anchor['href'].endswith('/projects/{}'.format(project_id)) for project_anchor in project_anchors)
    assert any(project_anchor['href'].endswith('/projects/{}'.format(other_project_id)) for project_anchor in project_anchors)

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format(user_session.user_id+1))
    assert r.status_code == 403


def test_create_project(flask_server, user_session):
    r = user_session.get(flask_server.base_url + 'projects/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    create_project_form = document.find(id='createProjectModal').find('form')
    assert create_project_form is not None

    csrf_token = create_project_form.find('input', {'name': 'csrf_token'})['value']

    r = user_session.post(flask_server.base_url + 'projects/', data={
        'create': 'create',
        'csrf_token': csrf_token,
        'name': 'Example Project',
        'description': 'Example Description'
    }, allow_redirects=False)
    assert r.status_code == 302
    # Force reloading of objects
    sampledb.db.session.rollback()

    projects = sampledb.logic.projects.get_user_projects(user_session.user_id)
    assert len(projects) == 1
    project = projects[0]
    assert project.name == 'Example Project'
    assert project.description == 'Example Description'

    assert r.headers['Location'] == flask_server.base_url + 'projects/{}'.format(project.id)


def test_leave_project(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    leave_project_form = document.find('form', id='leaveProjectForm')
    csrf_token = leave_project_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(project_id), data={
        'leave': 'leave',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    assert len(sampledb.logic.projects.get_user_projects(user_session.user_id)) == 0


def test_edit_project(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    edit_project_form = document.find(id='editProjectModal').find('form')
    csrf_token = edit_project_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(project_id), data={
        'edit': 'edit',
        'csrf_token': csrf_token,
        'name': 'Test Project',
        'description': 'Test Description'
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    project = sampledb.logic.projects.get_project(project_id)
    assert project.name == 'Test Project'
    assert project.description == 'Test Description'


def test_add_user(flask_server, user_session, user):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    new_user = user

    assert len(sampledb.logic.projects.get_user_projects(new_user.id)) == 0

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    url = flask_server.base_url + 'projects/{}'.format(project_id)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    invite_user_form = document.find(id='inviteUserModal').find('form')
    csrf_token = invite_user_form.find('input', {'name': 'csrf_token'})['value']

    #  send invitation
    with sampledb.mail.record_messages() as outbox:
        r = user_session.post(url, {
            'add_user': 'add_user',
            'csrf_token': csrf_token,
            'user_id': str(new_user.id)
        })
    assert r.status_code == 200

    # Check if an invitation mail was sent
    assert len(outbox) == 1
    assert 'example2@fz-juelich.de' in outbox[0].recipients
    message = outbox[0].html
    assert 'Join project Example Project' in message
    assert 'You have been invited to be a member of the project Example Project.' in message

    assert len(sampledb.logic.projects.get_user_projects(new_user.id)) == 0

    # Get the confirmation url from the mail and open it without logged in
    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[1].split('"')[0]
    assert confirmation_url.startswith(flask_server.base_url + 'projects/1')
    r = user_session.get(confirmation_url)
    assert r.status_code == 403
    assert 'Please sign in as user &#34;{}&#34; to accept this invitation'.format(user.name) in r.content.decode('utf-8')

    assert len(sampledb.logic.projects.get_user_projects(new_user.id)) == 0

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    # Get the confirmation url from the mail and open it without logged in
    confirmation_url = flask_server.base_url + message.split(flask_server.base_url)[1].split('"')[0]
    assert confirmation_url.startswith(flask_server.base_url + 'projects/1')

    r = session.get(confirmation_url)
    assert r.status_code == 200

    assert len(sampledb.logic.projects.get_user_projects(new_user.id)) == 1
    assert sampledb.logic.projects.get_user_projects(new_user.id)[0].id == project_id


def test_add_group(flask_server, user_session):
    group_id = sampledb.logic.groups.create_group("Example Group", "", user_session.user_id).id

    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    assert len(sampledb.logic.projects.get_group_projects(group_id)) == 0

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    url = flask_server.base_url + 'projects/{}'.format(project_id)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    invite_user_form = document.find(id='inviteGroupModal').find('form')
    csrf_token = invite_user_form.find('input', {'name': 'csrf_token'})['value']

    r = user_session.post(url, {
        'add_group': 'add_group',
        'csrf_token': csrf_token,
        'group_id': str(group_id)
    })
    assert r.status_code == 200

    assert len(sampledb.logic.projects.get_group_projects(group_id)) == 1
    assert sampledb.logic.projects.get_group_projects(group_id)[0].id == project_id


def test_view_project(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('h3').text == 'Project #{}: Example Project'.format(project_id)
