# coding: utf-8
"""

"""

import datetime
import flask
import logging

import flask_login
import jsonschema
import pytest
import requests

import sampledb
from sampledb import logic
from sampledb.logic.permissions import set_user_object_permissions, Permissions
from sampledb.models import User, UserType, Action, Objects
from sampledb.rest_api import objects
from tests.test_utils import flask_server, app

logging.getLogger('werkzeug').setLevel(logging.WARNING)


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture(autouse=True)
def app_context(flask_server):
    with flask_server.app.app_context():
        yield None


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


@pytest.fixture
def action(flask_server):
    action = Action(
        name='Example Action',
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'example': {
                    'title': 'Example Attribute',
                    'type': 'text'
                }
            }
        },
        description='',
        instrument_id=None
    )
    with flask_server.app.app_context():
        sampledb.db.session.add(action)
        sampledb.db.session.commit()
        # force attribute refresh
        assert action.id is not None
    return action


def test_get_objects(flask_server, user, username, password, action):
    Objects.create_object(action_id=action.id, data={}, schema=action.schema, user_id=user.id)
    obj = Objects.create_object(action_id=action.id, data={}, schema=action.schema, user_id=user.id)
    r = requests.get(flask_server.api_url + 'objects/', auth=(username, password))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    for obj in data:
        jsonschema.validate(obj, objects.OBJECT_SCHEMA)
    set_user_object_permissions(user_id=user.id, object_id=obj['object_id'], permissions=Permissions.NONE)
    r = requests.get(flask_server.api_url + 'objects/', auth=(username, password))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1


def test_get_object(flask_server, user, username, password, action):
    r = requests.get(flask_server.api_url + 'objects/0', auth=(username, password))
    assert r.status_code == 404
    obj = Objects.create_object(action_id=action.id, data={}, schema=action.schema, user_id=user.id)
    r = requests.get(flask_server.api_url + 'objects/{}'.format(obj.object_id), auth=(username, password))
    assert r.status_code == 200
    data = r.json()
    jsonschema.validate(data, objects.OBJECT_SCHEMA)
    # Make sure we know about all keys in data
    assert set(data.keys()) == {'object_id', 'version_id', 'user_id', 'data', 'schema', 'last_modified'}
    # Verify their values one by one
    assert data['object_id'] == obj.object_id
    assert data['version_id'] == obj.version_id
    assert data['user_id'] == obj.user_id
    assert data['data'] == obj.data
    assert datetime.datetime.strptime(data['last_modified'], '%Y-%m-%d %H:%M:%S') == obj.utc_datetime.replace(microsecond=0)


def test_get_object_version_initial(flask_server, user, username, password, action):
    obj = Objects.create_object(action_id=action.id, data={}, schema=action.schema, user_id=user.id)
    r = requests.get(flask_server.api_url + 'objects/{}/versions/0'.format(obj.object_id), auth=(username, password))
    assert r.status_code == 200
    data = r.json()
    jsonschema.validate(data, objects.OBJECT_SCHEMA)
    # Make sure we know about all keys in data
    assert set(data.keys()) == {'object_id', 'version_id', 'user_id', 'data', 'schema', 'last_modified'}
    # Verify their values one by one
    assert data['object_id'] == obj.object_id
    assert data['version_id'] == obj.version_id
    assert data['user_id'] == obj.user_id
    assert data['data'] == obj.data
    assert datetime.datetime.strptime(data['last_modified'], '%Y-%m-%d %H:%M:%S') == obj.utc_datetime.replace(microsecond=0)


def test_get_object_version_updated(flask_server, user, username, password, action):
    obj = Objects.create_object(action_id=action.id, data={}, schema=action.schema, user_id=user.id)
    obj = Objects.update_object(obj.object_id, data={}, schema=action.schema, user_id=user.id)
    r = requests.get(flask_server.api_url + 'objects/{}/versions/{}'.format(obj.object_id, obj.version_id), auth=(username, password))
    assert r.status_code == 200
    data = r.json()
    jsonschema.validate(data, objects.OBJECT_SCHEMA)
    # Make sure we know about all keys in data
    assert set(data.keys()) == {'object_id', 'version_id', 'user_id', 'data', 'schema', 'last_modified'}
    # Verify their values one by one
    assert data['object_id'] == obj.object_id
    assert data['version_id'] == obj.version_id
    assert data['user_id'] == obj.user_id
    assert data['data'] == obj.data
    assert datetime.datetime.strptime(data['last_modified'], '%Y-%m-%d %H:%M:%S') == obj.utc_datetime.replace(microsecond=0)


def test_get_object_version_old(flask_server, user, username, password, action):
    obj = Objects.create_object(action_id=action.id, data={}, schema=action.schema, user_id=user.id)
    Objects.update_object(obj.object_id, data={}, schema=action.schema, user_id=user.id)
    r = requests.get(flask_server.api_url + 'objects/{}/versions/0'.format(obj.object_id, obj.version_id), auth=(username, password))
    assert r.status_code == 200
    data = r.json()
    jsonschema.validate(data, objects.OBJECT_SCHEMA)
    # Make sure we know about all keys in data
    assert set(data.keys()) == {'object_id', 'version_id', 'user_id', 'data', 'schema', 'last_modified'}
    # Verify their values one by one
    assert data['object_id'] == obj.object_id
    assert data['version_id'] == obj.version_id
    assert data['user_id'] == obj.user_id
    assert data['data'] == obj.data
    assert datetime.datetime.strptime(data['last_modified'], '%Y-%m-%d %H:%M:%S') == obj.utc_datetime.replace(microsecond=0)


def test_get_object_version_missing(flask_server, user, username, password, action):
    obj = Objects.create_object(action_id=action.id, data={}, schema=action.schema, user_id=user.id)
    obj = Objects.update_object(obj.object_id, data={}, schema=action.schema, user_id=user.id)
    r = requests.get(flask_server.api_url + 'objects/{}/versions/2'.format(obj.object_id, obj.version_id), auth=(username, password))
    assert r.status_code == 404


def test_create_object(flask_server, user, username, password, action):
    assert len(Objects.get_current_objects()) == 0
    data = {
        'action_id': action.id,
        'data': {},
        'schema': action.schema
    }
    r = requests.post(flask_server.api_url + 'objects/', json=data, auth=(username, password))
    assert r.status_code == 201
    assert len(Objects.get_current_objects()) == 1
    obj = Objects.get_current_objects()[0]
    assert r.headers['Location'] == flask_server.api_url + 'objects/{}'.format(obj.object_id)
    assert obj.version_id == 0
    assert obj.data == {}
    assert obj.utc_datetime <= datetime.datetime.utcnow()
    assert obj.utc_datetime >= datetime.datetime.utcnow()-datetime.timedelta(seconds=5)


def test_create_object_errors(flask_server, user, username, password, action):
    assert len(Objects.get_current_objects()) == 0
    invalid_data = [
        {
            # object ID is determined by the database
            'object_id': 1,
            'action_id': action.id,
            'data': {},
            'schema': action.schema
        }, {
            # version ID has to be 0 for any new objects
            'version_id': 1,
            'action_id': action.id,
            'data': {},
            'schema': action.schema
        }, {
            # user ID is always the ID of the currently logged in user
            'user_id': user.id+1,
            'action_id': action.id,
            'data': {},
            'schema': action.schema
        }, {
            'action_id': action.id,
            # TODO: should it be allowed to set last_modified time? Probably not.
            'last_modified': '2017-01-01 00:00:00',
            'data': {},
            'schema': action.schema
        }, {
            # attributes / keys which aren't part of the object schema are not allowed
            'action_id': action.id,
            'invalid': '',
            'data': {},
            'schema': action.schema
        }, {
            # schema is required
            'action_id': action.id,
            'data': {}
        }, {
            # action_id is required
            'data': {},
            'schema': action.schema
        }, {
            # action_id must be valid foreign key
            'action_id': action.id+1,
            'data': {},
            'schema': action.schema
        }, {
            # schema must be equal to action schema
            'action_id': action.id,
            'data': {},
            'schema': {'type': 'object', 'properties': {'test': {'type': 'string'}}}
        }, {}
    ]
    for data in invalid_data:
        r = requests.post(flask_server.api_url + 'objects/', json=data, auth=(username, password))
        assert r.status_code == 400
        assert len(Objects.get_current_objects()) == 0
    r = requests.post(flask_server.api_url + 'objects/', json=None, auth=(username, password))
    assert r.status_code == 400
    assert len(Objects.get_current_objects()) == 0


def test_update_object(flask_server, user, username, password, action):
    obj = Objects.create_object(action_id=action.id, data={}, schema=action.schema, user_id=user.id)
    data = {
        'data': {'example': {'_type': 'text', 'text': 'Example'}},
        'schema': action.schema
    }
    r = requests.put(flask_server.api_url + 'objects/{}'.format(obj.object_id), json=data, auth=(username, password))
    assert r.status_code == 200
    obj = Objects.get_current_objects()[0]
    assert r.headers['Location'] == flask_server.api_url + 'objects/{}'.format(obj.object_id)
    assert obj.data == {'example': {'_type': 'text', 'text': 'Example'}}
    assert obj.schema == action.schema
    assert obj.version_id == 1
    assert obj.utc_datetime <= datetime.datetime.utcnow()
    assert obj.utc_datetime >= datetime.datetime.utcnow()-datetime.timedelta(seconds=5)


def test_update_object_errors(flask_server, user, username, password, action):
    assert len(Objects.get_current_objects()) == 0
    r = requests.put(flask_server.api_url + 'objects/0', json={'data': {}}, auth=(username, password))
    assert r.status_code == 404
    assert len(Objects.get_current_objects()) == 0
    obj = Objects.create_object(action_id=action.id, data={}, schema=action.schema, user_id=user.id)
    assert len(Objects.get_current_objects()) == 1
    invalid_data = [
        {
            # modifying the object ID is not allowed
            'object_id': 2,
            'data': {},
            'schema': action.schema
        }, {
            # version ID must always me incremented by one
            'version_id': 0,
            'data': {},
            'schema': action.schema
        }, {
            # user ID is always the ID of the currently logged in user
            'user_id': user.id+1,
            'data': {},
            'schema': action.schema
        }, {
            # TODO: should it be allowed to vary last_modified time? Probably not.
            'last_modified': '2017-01-01 00:00:00',
            'data': {},
            'schema': action.schema
        }, {
            # attributes / keys which aren't part of the object schema are not allowed
            'invalid': '',
            'data': {},
            'schema': action.schema
        }, {
            # schema is required
            'data': {}
        }, {
            # action_id cannot be changed
            'action_id': action.id+1,
            'data': {},
            'schema': action.schema
        }, {
            # schema must be valid
            'data': {},
            'schema': {}
        }, {
            # object must be valid for the schema
            'data': {'example2': {'_type': 'text', 'text': 'Example'}},
            'schema': action.schema
        }, {}
    ]
    for data in invalid_data:
        r = requests.put(flask_server.api_url + 'objects/{}'.format(obj.object_id), json=data, auth=(username, password))
        assert r.status_code == 400
        assert len(Objects.get_current_objects()) == 1
    r = requests.put(flask_server.api_url + 'objects/{}'.format(obj.object_id), json=None, auth=(username, password))
    assert r.status_code == 400
    assert len(Objects.get_current_objects()) == 1
