# coding: utf-8
"""

"""

import flask_login
import json
import requests
import pytest
import sampledb
from sampledb.authentication.models import User, UserType
from sampledb.instruments.models import Action, Instrument
from sampledb.object_database.models import Objects
from sampledb.permissions import logic
from sampledb.permissions.models import Permissions, UserObjectPermissions

from .utils import flask_server

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture
def app():
    sampledb_app = sampledb.create_app()

    @sampledb_app.route('/users/<int:user_id>/autologin')
    def autologin(user_id):
        user = User.query.get(user_id)
        assert user is not None
        flask_login.login_user(user)
        return ''

    with sampledb_app.app_context():
        # fully empty the database first
        sampledb.db.MetaData(reflect=True, bind=sampledb.db.engine).drop_all()
        # recreate the tables used by this application
        sampledb.db.metadata.create_all(bind=sampledb.db.engine)
    return sampledb_app


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
        name='Example Action',
        schema={},
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
        name='Example Action',
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
        name='Example Action',
        schema={},
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
    objects = [Objects.create_object(user_id=users[1].id, action_id=action.id, data={}, schema={}) for action in actions]
    return objects


@pytest.fixture
def instrument_action_object(objects):
    return objects[0]


@pytest.fixture
def independent_action_object(objects):
    return objects[1]


@pytest.fixture
def user(users):
    return users[0]


@pytest.fixture(autouse=True)
def app_context(flask_server):
    with flask_server.app.app_context():
        yield None


def test_require_login(flask_server, user, independent_action_object):
    object_id = independent_action_object.object_id
    r = requests.get(flask_server.base_url + 'objects/{}/permissions/all'.format(object_id), allow_redirects=False)
    # Either get 401 Unauthorized or 302 Found
    assert r.status_code == 401 or r.status_code == 302
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.base_url + 'objects/{}/permissions/all'.format(object_id))
    assert r.status_code == 403


def test_public_objects(flask_server, user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    logic.set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.GRANT)
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user_id))
    r = session.get(flask_server.base_url + 'objects/{}/permissions/all'.format(object_id))
    assert r.status_code == 200
    assert r.json() == 'none'
    logic.set_object_public(object_id)
    r = session.get(flask_server.base_url + 'objects/{}/permissions/all'.format(object_id))
    assert r.status_code == 200
    assert r.json() == 'read'
    logic.set_object_public(object_id, False)
    r = session.get(flask_server.base_url + 'objects/{}/permissions/all'.format(object_id))
    assert r.status_code == 200
    assert r.json() == 'none'
    r = session.put(flask_server.base_url + 'objects/{}/permissions/all'.format(object_id), json='read')
    assert r.status_code == 200
    assert r.json() == 'read'
    assert logic.object_is_public(object_id)


def test_default_user_object_permissions(flask_server, users, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(users[1].id))
    r = session.get(flask_server.base_url + 'objects/{}/permissions/{}'.format(object_id, user_id))
    assert r.status_code == 200
    assert r.json() == 'none'


def test_get_user_object_permissions(flask_server, user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    logic.set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE)
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user_id))
    r = session.get(flask_server.base_url + 'objects/{}/permissions/{}'.format(object_id, user_id))
    assert r.status_code == 200
    assert r.json() == 'write'


def test_get_instrument_responsible_user_object_permissions(flask_server, user, instrument, instrument_action_object):
    user_id = user.id
    object_id = instrument_action_object.object_id
    instrument.responsible_users.append(user)
    sampledb.db.session.add(instrument)
    logic.set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE)
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user_id))
    r = session.get(flask_server.base_url + 'objects/{}/permissions/{}'.format(object_id, user_id))
    assert r.status_code == 200
    assert r.json() == 'grant'


def test_get_user_public_object_permissions(flask_server, users, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id
    logic.set_object_public(object_id)
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(users[1].id))
    r = session.get(flask_server.base_url + 'objects/{}/permissions/{}'.format(object_id, user_id))
    assert r.status_code == 200
    assert r.json() == 'read'


def test_get_object_permissions(flask_server, users, instrument, instrument_action_object):
    user_id = users[0].id
    object_id = instrument_action_object.object_id
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(users[1].id))
    r = session.get(flask_server.base_url + 'objects/{}/permissions/'.format(object_id))
    assert r.status_code == 200
    assert r.json() == {
        'all': 'none',
        str(users[1].id): 'grant'
    }
    logic.set_object_public(object_id)
    r = session.get(flask_server.base_url + 'objects/{}/permissions/'.format(object_id))
    assert r.status_code == 200
    assert r.json() == {
        'all': 'read',
        str(users[1].id): 'grant'
    }
    logic.set_user_object_permissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE)
    r = session.get(flask_server.base_url + 'objects/{}/permissions/'.format(object_id))
    assert r.status_code == 200
    assert r.json() == {
        'all': 'read',
        str(user_id): 'write',
        str(users[1].id): 'grant'
    }
    instrument.responsible_users.append(users[0])
    sampledb.db.session.add(instrument)
    sampledb.db.session.commit()
    r = session.get(flask_server.base_url + 'objects/{}/permissions/'.format(object_id))
    assert r.status_code == 200
    assert r.json() == {
        'all': 'read',
        str(user_id): 'grant',
        str(users[1].id): 'grant'
    }


def test_get_missing_object_permissions(flask_server, users):
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(users[1].id))
    r = session.get(flask_server.base_url + 'objects/42/permissions/')
    assert r.status_code == 404


def test_get_missing_object_public_permissions(flask_server, users):
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(users[1].id))
    r = session.get(flask_server.base_url + 'objects/42/permissions/all')
    assert r.status_code == 404


def test_update_object_permissions(flask_server, users, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(users[1].id))
    logic.set_user_object_permissions(user_id=users[1].id, object_id=object_id, permissions=Permissions.GRANT)
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    r = session.put(flask_server.base_url + 'objects/{}/permissions/{}'.format(object_id, user_id), json='write')
    assert r.status_code == 200
    assert r.json() == 'write'
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.WRITE
    r = session.put(flask_server.base_url + 'objects/{}/permissions/{}'.format(object_id, user_id), json='read')
    assert r.status_code == 200
    assert r.json() == 'read'
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    r = session.put(flask_server.base_url + 'objects/{}/permissions/{}'.format(object_id, user_id), json='none')
    assert r.status_code == 200
    assert r.json() == 'none'
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    assert logic.get_object_permissions(object_id=object_id) == {
        None: Permissions.NONE,
        users[1].id: Permissions.GRANT
    }


def test_update_object_permissions_errors(flask_server, users, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(users[1].id))
    logic.set_user_object_permissions(user_id=users[1].id, object_id=object_id, permissions=Permissions.GRANT)
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    # invalid permission name
    r = session.put(flask_server.base_url + 'objects/{}/permissions/{}'.format(object_id, user_id), json='execute')
    assert r.status_code == 400
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    # invalid object id
    r = session.put(flask_server.base_url + 'objects/{}/permissions/{}'.format(42, user_id), json='read')
    assert r.status_code == 404
    # invalid data
    r = session.put(flask_server.base_url + 'objects/{}/permissions/{}'.format(object_id, user_id), data='invalid')
    assert r.status_code == 400


def test_update_object_public_permissions_errors(flask_server, users, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(users[1].id))
    logic.set_object_public(object_id)
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    # permissions higher than read
    r = session.put(flask_server.base_url + 'objects/{}/permissions/all'.format(object_id, user_id), json='write')
    assert r.status_code == 400
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    # invalid permission name
    r = session.put(flask_server.base_url + 'objects/{}/permissions/all'.format(object_id, user_id), json='execute')
    assert r.status_code == 400
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    # invalid object id
    r = session.put(flask_server.base_url + 'objects/{}/permissions/all'.format(42, user_id), json='read')
    assert r.status_code == 404
    # invalid data
    r = session.put(flask_server.base_url + 'objects/{}/permissions/all'.format(object_id, user_id), data='invalid')
    assert r.status_code == 400
