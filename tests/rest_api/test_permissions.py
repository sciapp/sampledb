# coding: utf-8
"""

"""

import flask
import pytest
import requests

import sampledb
from sampledb import logic
from sampledb.models import User, UserType, Action, Instrument, Permissions, Objects, ActionType
from sampledb.logic.permissions import get_object_permissions, set_user_object_permissions, object_is_public, set_object_public, get_user_object_permissions

from tests.test_utils import flask_server, app

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture
def users(flask_server):
    names = ['User 1', 'User 2']
    users = []
    for name in names:
        with flask_server.app.app_context():
            user = User(name=name, email="example@fz-juelich.de", type=UserType.PERSON)
            sampledb.db.session.add(user)
            sampledb.db.session.commit()
            # force attribute refresh
            assert user.id is not None
            users.append(user)
    return users


@pytest.fixture
def independent_action(app):
    action = Action(
        action_type=ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {}
        },
        description='',
        instrument_id=None
    )
    with app.app_context():
        sampledb.db.session.add(action)
        sampledb.db.session.commit()
        # force attribute refresh
        assert action.id is not None
    return action


@pytest.fixture
def instrument(app):
    instrument = Instrument(
        name='Example Instrument',
        description=''
    )
    with app.app_context():
        sampledb.db.session.add(instrument)
        sampledb.db.session.commit()
        # force attribute refresh
        assert instrument.id is not None
        assert instrument.responsible_users == []
    return instrument


@pytest.fixture
def instrument_action(app, instrument):
    action = Action(
        action_type=ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {}
        },
        description='',
        instrument_id=instrument.id
    )
    with app.app_context():
        sampledb.db.session.add(action)
        sampledb.db.session.commit()
        # force attribute refresh
        assert action.id is not None
    return action


@pytest.fixture
def objects(users, instrument_action, independent_action):
    actions = [instrument_action, independent_action]
    objects = [Objects.create_object(user_id=users[1].id, action_id=action.id, data={}, schema=action.schema) for action in actions]
    return objects


@pytest.fixture
def instrument_action_object(objects):
    return objects[0]


@pytest.fixture
def independent_action_object(objects):
    return objects[1]


@pytest.fixture
def username():
    return flask.current_app.config['TESTING_LDAP_LOGIN']


@pytest.fixture
def password():
    return flask.current_app.config['TESTING_LDAP_PW']


@pytest.fixture
def user(flask_server, username, password):
    with flask_server.app.app_context():
        user = logic.authentication.login(username, password)
        assert user.id is not None
    return user


@pytest.fixture(autouse=True)
def app_context(flask_server):
    with flask_server.app.app_context():
        yield None


def test_require_login(flask_server, user, username, password, independent_action_object):
    object_id = independent_action_object.object_id
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/all'.format(object_id), allow_redirects=False)
    assert r.status_code == 401
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/all'.format(object_id), auth=(username, password))
    assert r.status_code == 403


def test_public_objects(flask_server, user, username, password, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.GRANT)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/all'.format(object_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'none'
    set_object_public(object_id)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/all'.format(object_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'read'
    set_object_public(object_id, False)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/all'.format(object_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'none'
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/all'.format(object_id), json='read', auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'read'
    assert object_is_public(object_id)


def test_default_user_object_permissions(flask_server, user, username, password, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, user_id), auth=(username, password))
    assert r.status_code == 403
    set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.READ)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, user_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'read'


def test_get_user_object_permissions(flask_server, user, username, password, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, user_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'write'


def test_get_instrument_responsible_user_object_permissions(flask_server, user, username, password, instrument, instrument_action_object):
    user_id = user.id
    object_id = instrument_action_object.object_id
    instrument.responsible_users.append(user)
    sampledb.db.session.add(instrument)
    set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, user_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'grant'


def test_get_user_public_object_permissions(flask_server, user, username, password, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    set_object_public(object_id)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, user_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'read'


def test_get_object_permissions(flask_server, users, user, username, password, instrument, instrument_action_object):
    user_id = user.id
    object_id = instrument_action_object.object_id
    set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.READ)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/'.format(object_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == {
        'all': 'none',
        str(user_id): 'read',
        str(users[1].id): 'grant'
    }
    set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.NONE)
    set_object_public(object_id)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/'.format(object_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == {
        'all': 'read',
        str(users[1].id): 'grant'
    }
    set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE)
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/'.format(object_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == {
        'all': 'read',
        str(user_id): 'write',
        str(users[1].id): 'grant'
    }
    instrument.responsible_users.append(user)
    sampledb.db.session.add(instrument)
    sampledb.db.session.commit()
    r = requests.get(flask_server.api_url + 'objects/{}/permissions/'.format(object_id), auth=(username, password))
    assert r.status_code == 200
    assert r.json() == {
        'all': 'read',
        str(user_id): 'grant',
        str(users[1].id): 'grant'
    }


def test_get_missing_object_permissions(flask_server, username, password):
    r = requests.get(flask_server.api_url + 'objects/42/permissions/', auth=(username, password))
    assert r.status_code == 404


def test_get_missing_object_public_permissions(flask_server, username, password):
    r = requests.get(flask_server.api_url + 'objects/42/permissions/all', auth=(username, password))
    assert r.status_code == 404


def test_update_object_permissions(flask_server, users, user, username, password, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    set_user_object_permissions(user_id=user.id, object_id=object_id, permissions=Permissions.GRANT)
    assert get_user_object_permissions(user_id=users[0].id, object_id=object_id) == Permissions.NONE
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, users[0].id), json='write', auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'write'
    assert get_user_object_permissions(user_id=users[0].id, object_id=object_id) == Permissions.WRITE
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, users[0].id), json='read', auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'read'
    assert get_user_object_permissions(user_id=users[0].id, object_id=object_id) == Permissions.READ
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, users[0].id), json='none', auth=(username, password))
    assert r.status_code == 200
    assert r.json() == 'none'
    assert get_user_object_permissions(user_id=users[0].id, object_id=object_id) == Permissions.NONE
    assert get_object_permissions(object_id=object_id) == {
        None: Permissions.NONE,
        user.id: Permissions.GRANT,
        users[1].id: Permissions.GRANT
    }


def test_update_object_permissions_errors(flask_server, users, user, username, password, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id
    set_user_object_permissions(user_id=user.id, object_id=object_id, permissions=Permissions.GRANT)
    assert get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    # invalid permission name
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, user_id), json='execute', auth=(username, password))
    assert r.status_code == 400
    assert get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    # invalid object id
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/{}'.format(42, user_id), json='read', auth=(username, password))
    assert r.status_code == 404
    # invalid data
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/{}'.format(object_id, user_id), data='invalid', auth=(username, password))
    assert r.status_code == 400


def test_update_object_public_permissions_errors(flask_server, user, username, password, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    set_object_public(object_id)
    assert get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    # permissions higher than read
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/all'.format(object_id, user_id), json='write', auth=(username, password))
    assert r.status_code == 400
    assert get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    # invalid permission name
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/all'.format(object_id, user_id), json='execute', auth=(username, password))
    assert r.status_code == 400
    assert get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    # invalid object id
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/all'.format(42, user_id), json='read', auth=(username, password))
    assert r.status_code == 404
    # invalid data
    r = requests.put(flask_server.api_url + 'objects/{}/permissions/all'.format(object_id, user_id), data='invalid', auth=(username, password))
    assert r.status_code == 400
