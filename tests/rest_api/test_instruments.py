# coding: utf-8
"""

"""

import json
import requests
import pytest
import sampledb
from sampledb.models import User, UserType
from sampledb.logic import instruments

from tests.test_utils import flask_server, app

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture
def user(flask_server):
    user = User(name="Testuser", email="example@fz-juelich.de", type=UserType.PERSON)
    with flask_server.app.app_context():
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture(autouse=True)
def app_context(flask_server):
    with flask_server.app.app_context():
        yield None


def test_create_instrument(flask_server, user):
    with flask_server.app.app_context():
        assert len(instruments.get_instruments()) == 0
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.post(flask_server.api_url + 'instruments/', json.dumps({
        'name': 'Example Instrument',
        'description': ''
    }))
    assert r.status_code == 201
    instrument = r.json()
    with flask_server.app.app_context():
        assert len(instruments.get_instruments()) == 1
        assert instruments.get_instrument(instrument_id=instrument['id']).id == instrument['id']
        assert instrument['name'] == 'Example Instrument'
        assert instruments.get_instrument(instrument_id=instrument['id']).name == instrument['name']
        assert instrument['description'] == ''
        assert instruments.get_instrument(instrument_id=instrument['id']).description == instrument['description']
        assert len(instrument['responsible_users']) == 0


def test_create_instrument_invalid_data(flask_server, user):
    assert len(instruments.get_instruments()) == 0
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.post(flask_server.api_url + 'instruments/', json.dumps([]))
    assert r.status_code == 400
    assert len(instruments.get_instruments()) == 0
    # invalid JSON
    r = session.post(flask_server.api_url + 'instruments/', 'invalid')
    assert r.status_code == 400
    assert len(instruments.get_instruments()) == 0
    # invalid attributes
    r = session.post(flask_server.api_url + 'instruments/', json.dumps({
        'invalid': 'name'
    }))
    assert r.status_code == 400
    assert len(instruments.get_instruments()) == 0
    # try setting id
    r = session.post(flask_server.api_url + 'instruments/', json.dumps({
        'id': '0',
        'name': 'Test',
        'description': ''
    }))
    assert r.status_code == 400
    assert len(instruments.get_instruments()) == 0
    # try setting responsible users
    r = session.post(flask_server.api_url + 'instruments/', json.dumps({
        'name': 'Test',
        'description': '',
        'responsible_users': []
    }))
    assert r.status_code == 400
    assert len(instruments.get_instruments()) == 0


def test_update_instrument(flask_server, user):
    user2 = User(name="Testuser", email="example@fz-juelich.de", type=UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()
    instrument = instruments.create_instrument(name="Example Instrument", description="")
    assert instrument.id is not None
    instruments.add_instrument_responsible_user(instrument.id, user2.id)
    instrument_id = instrument.id
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.put(flask_server.api_url + 'instruments/{}'.format(instrument_id), json.dumps({
        'id': instrument_id,
        'name': 'Test',
        'description': 'desc',
        'responsible_users': [user.id]
    }))
    assert r.status_code == 200
    instrument = r.json()
    assert len(instruments.get_instruments()) == 1
    assert instruments.get_instrument(instrument_id=instrument['id']).id == instrument['id']
    assert instrument['name'] == 'Test'
    assert instruments.get_instrument(instrument_id=instrument['id']).name == instrument['name']
    assert instrument['description'] == 'desc'
    assert instruments.get_instrument(instrument_id=instrument['id']).description == instrument['description']
    assert instrument['responsible_users'] == [user.id]
    assert [user.id for user in instruments.get_instrument(instrument_id=instrument['id']).responsible_users] == instrument['responsible_users']


def test_update_instrument_invalid_data(flask_server, user):
    instrument = instruments.create_instrument(name="Example Instrument", description="")
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    original_instrument = instrument
    # invalid json data
    r = session.put(flask_server.api_url + 'instruments/{}'.format(instrument.id), json.dumps([]))
    assert r.status_code == 400
    assert instruments.get_instrument(instrument_id=instrument.id) == original_instrument
    # invalid attributes
    r = session.put(flask_server.api_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'invalid': 'name'
    }))
    assert r.status_code == 400
    assert instruments.get_instrument(instrument_id=instrument.id) == original_instrument
    # missing attributes
    r = session.put(flask_server.api_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'name': 'Test',
        'description': 'desc'
    }))
    assert r.status_code == 400
    assert instruments.get_instrument(instrument_id=instrument.id) == original_instrument
    # modified id
    r = session.put(flask_server.api_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'id': instrument.id+1,
        'name': 'Test',
        'description': 'desc',
        'responsible_users': [user.id]
    }))
    assert r.status_code == 400
    assert instruments.get_instrument(instrument_id=instrument.id) == original_instrument
    # invalid json data
    r = session.put(flask_server.api_url + 'instruments/{}'.format(instrument.id), 'invalid')
    assert r.status_code == 400
    assert instruments.get_instrument(instrument_id=instrument.id) == original_instrument
    # invalid responsible users
    r = session.put(flask_server.api_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'id': instrument.id,
        'name': 'Example Instrument',
        'description': '',
        'responsible_users': {}
    }))
    assert r.status_code == 400
    assert instruments.get_instrument(instrument_id=instrument.id) == original_instrument
    # invalid id
    r = session.put(flask_server.api_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'id': instrument.id+1,
        'name': 'Example Instrument',
        'description': '',
        'responsible_users': {}
    }))
    assert r.status_code == 400
    assert instruments.get_instrument(instrument_id=instrument.id) == original_instrument


def test_update_instrument_missing(flask_server, user):
    instrument = instruments.create_instrument(name="Example Instrument", description="")
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.put(flask_server.api_url + 'instruments/{}'.format(instrument.id+1))
    assert r.status_code == 404


def test_get_instrument(flask_server, user):
    instrument = instruments.create_instrument(name="Example Instrument", description="")
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.api_url + 'instruments/{}'.format(instrument.id))
    assert r.status_code == 200
    instrument = r.json()
    assert len(instruments.get_instruments()) == 1
    assert instruments.get_instrument(instrument_id=instrument['id']).id == instrument['id']
    assert instrument['name'] == 'Example Instrument'
    assert instruments.get_instrument(instrument_id=instrument['id']).name == instrument['name']
    assert instrument['description'] == ''
    assert instruments.get_instrument(instrument_id=instrument['id']).description == instrument['description']
    assert [user.id for user in instruments.get_instrument(instrument_id=instrument['id']).responsible_users] == instrument['responsible_users']


def test_get_instrument_missing(flask_server, user):
    instrument = instruments.create_instrument(name="Example Instrument", description="")
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.api_url + 'instruments/{}'.format(instrument.id+1))
    assert r.status_code == 404


def test_get_instruments(flask_server, user):
    instrument = instruments.create_instrument(name="Example Instrument", description="")
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.api_url + 'instruments/')
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert len(instruments.get_instruments()) == 1
    instrument = r.json()[0]
    assert instruments.get_instrument(instrument_id=instrument['id']).id == instrument['id']
    assert instrument['name'] == 'Example Instrument'
    assert instruments.get_instrument(instrument_id=instrument['id']).name == instrument['name']
    assert instrument['description'] == ''
    assert instruments.get_instrument(instrument_id=instrument['id']).description == instrument['description']
    assert [user.id for user in instruments.get_instrument(instrument_id=instrument['id']).responsible_users] == instrument['responsible_users']


def test_get_actions(flask_server, user):
    action = instruments.create_action(name="Example Action", description="", schema={})
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.api_url + 'actions/')
    assert r.status_code == 200
    actions = r.json()
    assert len(actions) == 1
    assert len(instruments.get_actions()) == 1
    action = actions[0]
    assert instruments.get_action(action_id=action['id']).id == action['id']
    assert action['name'] == 'Example Action'
    assert instruments.get_action(action_id=action['id']).name == action['name']
    assert action['description'] == ''
    assert instruments.get_action(action_id=action['id']).description == action['description']
    assert action['instrument_id'] is None
    assert instruments.get_action(action_id=action['id']).instrument_id is None
    assert action['schema'] == {}
    assert instruments.get_action(action_id=action['id']).schema == action['schema']


def test_get_action(flask_server, user):
    action = instruments.create_action(name="Example Action", description="", schema={})
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.api_url + 'actions/{}'.format(action.id))
    assert r.status_code == 200
    action = r.json()
    assert len(instruments.get_actions()) == 1
    assert instruments.get_action(action_id=action['id']).id == action['id']
    assert action['name'] == 'Example Action'
    assert instruments.get_action(action_id=action['id']).name == action['name']
    assert action['description'] == ''
    assert instruments.get_action(action_id=action['id']).description == action['description']
    assert action['instrument_id'] is None
    assert instruments.get_action(action_id=action['id']).instrument_id is None
    assert action['schema'] == {}
    assert instruments.get_action(action_id=action['id']).schema == action['schema']


def test_get_action_missing(flask_server, user):
    action = instruments.create_action(name="Example Action", description="", schema={})
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.api_url + 'actions/{}'.format(action.id+1))
    assert r.status_code == 404


def test_update_action(flask_server, user):
    action = instruments.create_action(name="Example Action", description="", schema={})
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.put(flask_server.api_url + 'actions/{}'.format(action.id), json.dumps({
        'id': action.id,
        'instrument_id': None,
        'name': 'Test',
        'description': 'desc',
        'schema': {}
    }))
    assert r.status_code == 200
    action = r.json()
    assert len(instruments.get_actions()) == 1
    assert instruments.get_action(action_id=action['id']).id == action['id']
    assert action['name'] == 'Test'
    assert instruments.get_action(action_id=action['id']).name == action['name']
    assert action['description'] == 'desc'
    assert instruments.get_action(action_id=action['id']).description == action['description']
    assert action['instrument_id'] is None
    assert instruments.get_action(action_id=action['id']).instrument_id is None
    assert action['schema'] == {}
    assert instruments.get_action(action_id=action['id']).schema == action['schema']


def test_update_action_missing(flask_server, user):
    action = instruments.create_action(name="Example Action", description="", schema={})
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.put(flask_server.api_url + 'actions/{}'.format(action.id+1))
    assert r.status_code == 404


def test_update_action_invalid_data(flask_server, user):
    action = instruments.create_action(name="Example Action", description="", schema={})
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    original_action = action
    # invalid json data
    r = session.put(flask_server.api_url + 'actions/{}'.format(action.id), json.dumps([]))
    assert r.status_code == 400
    assert instruments.get_action(action_id=action.id) == original_action
    # invalid attributes
    r = session.put(flask_server.api_url + 'actions/{}'.format(action.id), json.dumps({
        'invalid': 'name'
    }))
    assert r.status_code == 400
    assert instruments.get_action(action_id=action.id) == original_action
    # invalid json data
    r = session.put(flask_server.api_url + 'actions/{}'.format(action.id), 'invalid')
    assert r.status_code == 400
    assert instruments.get_action(action_id=action.id) == original_action
    # modified instrument id
    r = session.put(flask_server.api_url + 'actions/{}'.format(action.id), json.dumps({
        'id': action.id,
        'name': 'Example Action',
        'description': '',
        'instrument_id': 0,
        'schema': {}
    }))
    assert r.status_code == 400
    assert instruments.get_action(action_id=action.id) == original_action
    # modified id
    r = session.put(flask_server.api_url + 'actions/{}'.format(action.id), json.dumps({
        'id': action.id+1,
        'name': 'Example Action',
        'description': '',
        'instrument_id': None,
        'schema': {}
    }))
    assert r.status_code == 400
    assert instruments.get_action(action_id=action.id) == original_action
    # invalid schema
    r = session.put(flask_server.api_url + 'actions/{}'.format(action.id), json.dumps({
        'id': action.id,
        'name': 'Example Action',
        'description': '',
        'instrument_id': None,
        'schema': {'type': 'invalid'}
    }))
    assert r.status_code == 400
    assert instruments.get_action(action_id=action.id) == original_action
    # missing id
    r = session.put(flask_server.api_url + 'actions/{}'.format(action.id), json.dumps({
        'name': 'Example Action',
        'description': '',
        'instrument_id': None,
        'schema': {}
    }))
    assert r.status_code == 400
    assert instruments.get_action(action_id=action.id) == original_action


def test_create_action(flask_server, user):
    assert len(instruments.get_actions()) == 0
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.post(flask_server.api_url + 'actions/', json.dumps({
        'name': 'Example Action',
        'description': '',
        'schema': {},
        'instrument_id': None
    }))
    assert r.status_code == 201
    action = r.json()
    assert len(instruments.get_actions()) == 1
    assert instruments.get_action(action_id=action['id']).id == action['id']
    assert action['name'] == 'Example Action'
    assert instruments.get_action(action_id=action['id']).name == action['name']
    assert action['description'] == ''
    assert action['instrument_id'] is None
    assert instruments.get_action(action_id=action['id']).instrument_id is None
    assert action['schema'] == {}
    assert instruments.get_action(action_id=action['id']).schema == action['schema']


def test_create_action_invalid_data(flask_server, user):
    assert len(instruments.get_actions()) == 0
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    # invalid json data
    r = session.post(flask_server.api_url + 'actions/', json.dumps([]))
    assert r.status_code == 400
    assert len(instruments.get_actions()) == 0
    # invalid json data
    r = session.post(flask_server.api_url + 'actions/', 'invalid')
    assert r.status_code == 400
    assert len(instruments.get_actions()) == 0
    # invalid attributes
    r = session.post(flask_server.api_url + 'actions/', json.dumps({
        'invalid': 'name'
    }))
    # missing attributes
    r = session.post(flask_server.api_url + 'actions/', json.dumps({
        'name': 'Example Action',
        'description': '',
        'schema': {}
    }))
    assert r.status_code == 400
    assert len(instruments.get_actions()) == 0
    # invalid schema
    r = session.post(flask_server.api_url + 'actions/', json.dumps({
        'name': 'Example Action',
        'description': '',
        'schema': {'type': 'invalid'},
        'instrument_id': None
    }))
    assert r.status_code == 400
    assert len(instruments.get_actions()) == 0
