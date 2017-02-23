# coding: utf-8
"""

"""


import datetime
import json
import jsonschema
import logging
import pytest
import requests
import sampledb
from sampledb.object_database import datatypes
from sampledb.object_database import object_api

from .utils import flask_server

logging.getLogger('werkzeug').setLevel(logging.WARNING)


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture
def app():
    db_url = sampledb.app.config['SQLALCHEMY_DATABASE_URI']
    engine = sampledb.db.create_engine(
        db_url,
        json_serializer=lambda obj: json.dumps(obj, cls=datatypes.JSONEncoder),
        json_deserializer=lambda obj: json.loads(obj, object_hook=datatypes.JSONEncoder.object_hook)
    )

    # fully empty the database first
    sampledb.db.MetaData(reflect=True, bind=engine).drop_all()
    # recreate the tables used by this application
    with sampledb.app.app_context():
        sampledb.db.metadata.create_all(bind=engine)
        object_api.Objects.bind = sampledb.db.engine
        # create the object tables
        object_api.Objects.metadata.create_all(sampledb.db.engine)
    return sampledb.app


def test_get_object(flask_server):
    r = requests.get(flask_server.base_url + 'objects/0')
    assert r.status_code == 404
    obj = object_api.Objects.create_object({}, user_id=0)
    r = requests.get(flask_server.base_url + 'objects/{}'.format(obj.object_id))
    assert r.status_code == 200
    data = r.json()
    jsonschema.validate(data, object_api.OBJECT_SCHEMA)
    # Make sure we know about all keys in data
    assert set(data.keys()) == {'object_id', 'version_id', 'user_id', 'data', 'last_modified'}
    # Verify their values one by one
    assert data['object_id'] == obj.object_id
    assert data['version_id'] == obj.version_id
    assert data['user_id'] == obj.user_id
    assert data['data'] == obj.data
    assert datetime.datetime.strptime(data['last_modified'], '%Y-%m-%d %H:%M:%S') == obj.utc_datetime.replace(microsecond=0)


def test_get_object_version_initial(flask_server):
    obj = object_api.Objects.create_object({}, user_id=0)
    r = requests.get(flask_server.base_url + 'objects/{}/versions/0'.format(obj.object_id))
    assert r.status_code == 200
    data = r.json()
    jsonschema.validate(data, object_api.OBJECT_SCHEMA)
    # Make sure we know about all keys in data
    assert set(data.keys()) == {'object_id', 'version_id', 'user_id', 'data', 'last_modified'}
    # Verify their values one by one
    assert data['object_id'] == obj.object_id
    assert data['version_id'] == obj.version_id
    assert data['user_id'] == obj.user_id
    assert data['data'] == obj.data
    assert datetime.datetime.strptime(data['last_modified'], '%Y-%m-%d %H:%M:%S') == obj.utc_datetime.replace(microsecond=0)


def test_get_object_version_updated(flask_server):
    obj = object_api.Objects.create_object({}, user_id=0)
    obj = object_api.Objects.update_object(obj.object_id, {}, user_id=0)
    r = requests.get(flask_server.base_url + 'objects/{}/versions/{}'.format(obj.object_id, obj.version_id))
    assert r.status_code == 200
    data = r.json()
    jsonschema.validate(data, object_api.OBJECT_SCHEMA)
    # Make sure we know about all keys in data
    assert set(data.keys()) == {'object_id', 'version_id', 'user_id', 'data', 'last_modified'}
    # Verify their values one by one
    assert data['object_id'] == obj.object_id
    assert data['version_id'] == obj.version_id
    assert data['user_id'] == obj.user_id
    assert data['data'] == obj.data
    assert datetime.datetime.strptime(data['last_modified'], '%Y-%m-%d %H:%M:%S') == obj.utc_datetime.replace(microsecond=0)


def test_get_object_version_old(flask_server):
    obj = object_api.Objects.create_object({}, user_id=0)
    object_api.Objects.update_object(obj.object_id, {}, user_id=0)
    r = requests.get(flask_server.base_url + 'objects/{}/versions/0'.format(obj.object_id, obj.version_id))
    assert r.status_code == 200
    data = r.json()
    jsonschema.validate(data, object_api.OBJECT_SCHEMA)
    # Make sure we know about all keys in data
    assert set(data.keys()) == {'object_id', 'version_id', 'user_id', 'data', 'last_modified'}
    # Verify their values one by one
    assert data['object_id'] == obj.object_id
    assert data['version_id'] == obj.version_id
    assert data['user_id'] == obj.user_id
    assert data['data'] == obj.data
    assert datetime.datetime.strptime(data['last_modified'], '%Y-%m-%d %H:%M:%S') == obj.utc_datetime.replace(microsecond=0)


def test_get_object_version_missing(flask_server):
    obj = object_api.Objects.create_object({}, user_id=0)
    obj = object_api.Objects.update_object(obj.object_id, {}, user_id=0)
    r = requests.get(flask_server.base_url + 'objects/{}/versions/2'.format(obj.object_id, obj.version_id))
    assert r.status_code == 404


def test_create_object(flask_server):
    assert len(object_api.Objects.get_current_objects()) == 0
    data = {
        'data': {}
    }
    r = requests.post(flask_server.base_url + 'objects/', json=data)
    assert r.status_code == 201
    assert len(object_api.Objects.get_current_objects()) == 1
    obj = object_api.Objects.get_current_objects()[0]
    assert r.headers['Location'] == flask_server.base_url + 'objects/{}'.format(obj.object_id)
    assert obj.version_id == 0
    assert obj.data == {}
    assert obj.utc_datetime <= datetime.datetime.utcnow()
    assert obj.utc_datetime >= datetime.datetime.utcnow()-datetime.timedelta(seconds=5)


def test_update_object(flask_server):
    obj = object_api.Objects.create_object({}, user_id=0)
    data = {
        'data': {'x' : 1}
    }
    r = requests.put(flask_server.base_url + 'objects/{}'.format(obj.object_id), json=data)
    assert r.status_code == 200
    obj = object_api.Objects.get_current_objects()[0]
    assert r.headers['Location'] == flask_server.base_url + 'objects/{}'.format(obj.object_id)
    assert obj.data == {'x': 1}
    assert obj.version_id == 1
    assert obj.utc_datetime <= datetime.datetime.utcnow()
    assert obj.utc_datetime >= datetime.datetime.utcnow()-datetime.timedelta(seconds=5)
