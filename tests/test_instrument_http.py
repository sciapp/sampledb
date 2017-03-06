# coding: utf-8
"""

"""

import flask_login
import json
import requests
import pytest
import sampledb
from sampledb.authentication.models import User, UserType
from sampledb.instruments import logic, models

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
def user(flask_server):
    user = User(name="Testuser", email="example@fz-juelich.de", type=UserType.PERSON)
    with flask_server.app.app_context():
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


def test_create_instrument(flask_server, user):
    assert len(logic.get_instruments()) == 0
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.post(flask_server.base_url + 'instruments/', json.dumps({
        'name': 'Example Instrument',
        'description': ''
    }))
    assert r.status_code == 201
    instrument = r.json()
    assert len(logic.get_instruments()) == 1
    assert logic.get_instrument(instrument_id=instrument['id']).id == instrument['id']
    assert instrument['name'] == 'Example Instrument'
    assert logic.get_instrument(instrument_id=instrument['id']).name == instrument['name']
    assert instrument['description'] == ''
    assert logic.get_instrument(instrument_id=instrument['id']).description == instrument['description']
    assert len(instrument['responsible_users']) == 0


def test_create_instrument_invalid_data(flask_server, user):
    assert len(logic.get_instruments()) == 0
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.post(flask_server.base_url + 'instruments/', json.dumps([]))
    assert r.status_code == 400
    assert len(logic.get_instruments()) == 0
    # invalid JSON
    r = session.post(flask_server.base_url + 'instruments/', 'invalid')
    assert r.status_code == 400
    assert len(logic.get_instruments()) == 0
    # invalid attributes
    r = session.post(flask_server.base_url + 'instruments/', json.dumps({
        'invalid': 'name'
    }))
    assert r.status_code == 400
    assert len(logic.get_instruments()) == 0
    # try setting id
    r = session.post(flask_server.base_url + 'instruments/', json.dumps({
        'id': '0',
        'name': 'Test',
        'description': ''
    }))
    assert r.status_code == 400
    assert len(logic.get_instruments()) == 0
    # try setting responsible users
    r = session.post(flask_server.base_url + 'instruments/', json.dumps({
        'name': 'Test',
        'description': '',
        'responsible_users': []
    }))
    assert r.status_code == 400
    assert len(logic.get_instruments()) == 0


def test_update_instrument(flask_server, user):
    with flask_server.app.app_context():
        user2 = User(name="Testuser", email="example@fz-juelich.de", type=UserType.PERSON)
        sampledb.db.session.add(user2)
        sampledb.db.session.commit()
        # force loading of id
        assert user2.id is not None
        instrument = logic.create_instrument(name="Example Instrument", description="")
        assert instrument.id is not None
        logic.add_instrument_responsible_user(instrument.id, user2.id)
        instrument_id = instrument.id
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.put(flask_server.base_url + 'instruments/{}'.format(instrument_id), json.dumps({
        'id': instrument_id,
        'name': 'Test',
        'description': 'desc',
        'responsible_users': [user.id]
    }))
    assert r.status_code == 200
    instrument = r.json()
    assert len(logic.get_instruments()) == 1
    assert logic.get_instrument(instrument_id=instrument['id']).id == instrument['id']
    assert instrument['name'] == 'Test'
    assert logic.get_instrument(instrument_id=instrument['id']).name == instrument['name']
    assert instrument['description'] == 'desc'
    assert logic.get_instrument(instrument_id=instrument['id']).description == instrument['description']
    assert instrument['responsible_users'] == [user.id]
    assert [user.id for user in logic.get_instrument(instrument_id=instrument['id']).responsible_users] == instrument['responsible_users']


def test_update_instrument_invalid_data(flask_server, user):
    with flask_server.app.app_context():
        instrument = logic.create_instrument(name="Example Instrument", description="")
        # force loading of id and responsible users
        assert instrument.id is not None
        assert instrument.responsible_users is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    original_instrument = instrument
    # invalid json data
    r = session.put(flask_server.base_url + 'instruments/{}'.format(instrument.id), json.dumps([]))
    assert r.status_code == 400
    assert logic.get_instrument(instrument_id=instrument.id) == original_instrument
    # invalid attributes
    r = session.put(flask_server.base_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'invalid': 'name'
    }))
    assert r.status_code == 400
    assert logic.get_instrument(instrument_id=instrument.id) == original_instrument
    # missing attributes
    r = session.put(flask_server.base_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'name': 'Test',
        'description': 'desc'
    }))
    assert r.status_code == 400
    assert logic.get_instrument(instrument_id=instrument.id) == original_instrument
    # modified id
    r = session.put(flask_server.base_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'id': instrument.id+1,
        'name': 'Test',
        'description': 'desc',
        'responsible_users': [user.id]
    }))
    assert r.status_code == 400
    assert logic.get_instrument(instrument_id=instrument.id) == original_instrument
    # invalid json data
    r = session.put(flask_server.base_url + 'instruments/{}'.format(instrument.id), 'invalid')
    assert r.status_code == 400
    assert logic.get_instrument(instrument_id=instrument.id) == original_instrument
    # invalid responsible users
    r = session.put(flask_server.base_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'id': instrument.id,
        'name': 'Example Instrument',
        'description': '',
        'responsible_users': {}
    }))
    assert r.status_code == 400
    assert logic.get_instrument(instrument_id=instrument.id) == original_instrument
    # invalid id
    r = session.put(flask_server.base_url + 'instruments/{}'.format(instrument.id), json.dumps({
        'id': instrument.id+1,
        'name': 'Example Instrument',
        'description': '',
        'responsible_users': {}
    }))
    assert r.status_code == 400
    assert logic.get_instrument(instrument_id=instrument.id) == original_instrument


def test_update_instrument_missing(flask_server, user):
    with flask_server.app.app_context():
        instrument = logic.create_instrument(name="Example Instrument", description="")
        # force loading of id
        assert instrument.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.put(flask_server.base_url + 'instruments/{}'.format(instrument.id+1))
    assert r.status_code == 404


def test_get_instrument(flask_server, user):
    with flask_server.app.app_context():
        instrument = logic.create_instrument(name="Example Instrument", description="")
        # force loading of id
        assert instrument.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.base_url + 'instruments/{}'.format(instrument.id))
    assert r.status_code == 200
    instrument = r.json()
    assert len(logic.get_instruments()) == 1
    assert logic.get_instrument(instrument_id=instrument['id']).id == instrument['id']
    assert instrument['name'] == 'Example Instrument'
    assert logic.get_instrument(instrument_id=instrument['id']).name == instrument['name']
    assert instrument['description'] == ''
    assert logic.get_instrument(instrument_id=instrument['id']).description == instrument['description']
    assert [user.id for user in logic.get_instrument(instrument_id=instrument['id']).responsible_users] == instrument['responsible_users']


def test_get_instrument_missing(flask_server, user):
    with flask_server.app.app_context():
        instrument = logic.create_instrument(name="Example Instrument", description="")
        # force loading of id
        assert instrument.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.base_url + 'instruments/{}'.format(instrument.id+1))
    assert r.status_code == 404


def test_get_instruments(flask_server, user):
    with flask_server.app.app_context():
        instrument = logic.create_instrument(name="Example Instrument", description="")
        # force loading of id
        assert instrument.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.base_url + 'instruments/')
    assert r.status_code == 200
    instruments = r.json()
    assert len(instruments) == 1
    assert len(logic.get_instruments()) == 1
    instrument = instruments[0]
    assert logic.get_instrument(instrument_id=instrument['id']).id == instrument['id']
    assert instrument['name'] == 'Example Instrument'
    assert logic.get_instrument(instrument_id=instrument['id']).name == instrument['name']
    assert instrument['description'] == ''
    assert logic.get_instrument(instrument_id=instrument['id']).description == instrument['description']
    assert [user.id for user in logic.get_instrument(instrument_id=instrument['id']).responsible_users] == instrument['responsible_users']


def test_get_actions(flask_server, user):
    with flask_server.app.app_context():
        action = logic.create_action(name="Example Action", description="", schema={})
        # force loading of id
        assert action.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.base_url + 'actions/')
    assert r.status_code == 200
    actions = r.json()
    assert len(actions) == 1
    assert len(logic.get_actions()) == 1
    action = actions[0]
    assert logic.get_action(action_id=action['id']).id == action['id']
    assert action['name'] == 'Example Action'
    assert logic.get_action(action_id=action['id']).name == action['name']
    assert action['description'] == ''
    assert logic.get_action(action_id=action['id']).description == action['description']
    assert action['instrument_id'] is None
    assert logic.get_action(action_id=action['id']).instrument_id is None
    assert action['schema'] == {}
    assert logic.get_action(action_id=action['id']).schema == action['schema']


def test_get_action(flask_server, user):
    with flask_server.app.app_context():
        action = logic.create_action(name="Example Action", description="", schema={})
        # force loading of id
        assert action.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.base_url + 'actions/{}'.format(action.id))
    assert r.status_code == 200
    action = r.json()
    assert len(logic.get_actions()) == 1
    assert logic.get_action(action_id=action['id']).id == action['id']
    assert action['name'] == 'Example Action'
    assert logic.get_action(action_id=action['id']).name == action['name']
    assert action['description'] == ''
    assert logic.get_action(action_id=action['id']).description == action['description']
    assert action['instrument_id'] is None
    assert logic.get_action(action_id=action['id']).instrument_id is None
    assert action['schema'] == {}
    assert logic.get_action(action_id=action['id']).schema == action['schema']


def test_get_action_missing(flask_server, user):
    with flask_server.app.app_context():
        action = logic.create_action(name="Example Action", description="", schema={})
        # force loading of id
        assert action.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.get(flask_server.base_url + 'actions/{}'.format(action.id+1))
    assert r.status_code == 404


def test_update_action(flask_server, user):
    with flask_server.app.app_context():
        action = logic.create_action(name="Example Action", description="", schema={})
        assert action.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.put(flask_server.base_url + 'actions/{}'.format(action.id), json.dumps({
        'id': action.id,
        'instrument_id': None,
        'name': 'Test',
        'description': 'desc',
        'schema': {}
    }))
    assert r.status_code == 200
    action = r.json()
    assert len(logic.get_actions()) == 1
    assert logic.get_action(action_id=action['id']).id == action['id']
    assert action['name'] == 'Test'
    assert logic.get_action(action_id=action['id']).name == action['name']
    assert action['description'] == 'desc'
    assert logic.get_action(action_id=action['id']).description == action['description']
    assert action['instrument_id'] is None
    assert logic.get_action(action_id=action['id']).instrument_id is None
    assert action['schema'] == {}
    assert logic.get_action(action_id=action['id']).schema == action['schema']


def test_update_action_missing(flask_server, user):
    with flask_server.app.app_context():
        action = logic.create_action(name="Example Action", description="", schema={})
        # force loading of id
        assert action.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.put(flask_server.base_url + 'actions/{}'.format(action.id+1))
    assert r.status_code == 404


def test_update_action_invalid_data(flask_server, user):
    with flask_server.app.app_context():
        action = logic.create_action(name="Example Action", description="", schema={})
        # force loading of id
        assert action.id is not None
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    original_action = action
    # invalid json data
    r = session.put(flask_server.base_url + 'actions/{}'.format(action.id), json.dumps([]))
    assert r.status_code == 400
    assert logic.get_action(action_id=action.id) == original_action
    # invalid attributes
    r = session.put(flask_server.base_url + 'actions/{}'.format(action.id), json.dumps({
        'invalid': 'name'
    }))
    assert r.status_code == 400
    assert logic.get_action(action_id=action.id) == original_action
    # invalid json data
    r = session.put(flask_server.base_url + 'actions/{}'.format(action.id), 'invalid')
    assert r.status_code == 400
    assert logic.get_action(action_id=action.id) == original_action
    # modified instrument id
    r = session.put(flask_server.base_url + 'actions/{}'.format(action.id), json.dumps({
        'id': action.id,
        'name': 'Example Action',
        'description': '',
        'instrument_id': 0,
        'schema': {}
    }))
    assert r.status_code == 400
    assert logic.get_action(action_id=action.id) == original_action
    # modified id
    r = session.put(flask_server.base_url + 'actions/{}'.format(action.id), json.dumps({
        'id': action.id+1,
        'name': 'Example Action',
        'description': '',
        'instrument_id': None,
        'schema': {}
    }))
    assert r.status_code == 400
    assert logic.get_action(action_id=action.id) == original_action
    # invalid schema
    r = session.put(flask_server.base_url + 'actions/{}'.format(action.id), json.dumps({
        'id': action.id,
        'name': 'Example Action',
        'description': '',
        'instrument_id': None,
        'schema': {'type': 'invalid'}
    }))
    assert r.status_code == 400
    assert logic.get_action(action_id=action.id) == original_action
    # missing id
    r = session.put(flask_server.base_url + 'actions/{}'.format(action.id), json.dumps({
        'name': 'Example Action',
        'description': '',
        'instrument_id': None,
        'schema': {}
    }))
    assert r.status_code == 400
    assert logic.get_action(action_id=action.id) == original_action


def test_create_action(flask_server, user):
    assert len(logic.get_actions()) == 0
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    r = session.post(flask_server.base_url + 'actions/', json.dumps({
        'name': 'Example Action',
        'description': '',
        'schema': {},
        'instrument_id': None
    }))
    assert r.status_code == 201
    action = r.json()
    assert len(logic.get_actions()) == 1
    assert logic.get_action(action_id=action['id']).id == action['id']
    assert action['name'] == 'Example Action'
    assert logic.get_action(action_id=action['id']).name == action['name']
    assert action['description'] == ''
    assert action['instrument_id'] is None
    assert logic.get_action(action_id=action['id']).instrument_id is None
    assert action['schema'] == {}
    assert logic.get_action(action_id=action['id']).schema == action['schema']


def test_create_action_invalid_data(flask_server, user):
    assert len(logic.get_actions()) == 0
    # this operation requires a logged in user
    session = requests.session()
    session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id))
    # invalid json data
    r = session.post(flask_server.base_url + 'actions/', json.dumps([]))
    assert r.status_code == 400
    assert len(logic.get_actions()) == 0
    # invalid json data
    r = session.post(flask_server.base_url + 'actions/', 'invalid')
    assert r.status_code == 400
    assert len(logic.get_actions()) == 0
    # invalid attributes
    r = session.post(flask_server.base_url + 'actions/', json.dumps({
        'invalid': 'name'
    }))
    # missing attributes
    r = session.post(flask_server.base_url + 'actions/', json.dumps({
        'name': 'Example Action',
        'description': '',
        'schema': {}
    }))
    assert r.status_code == 400
    assert len(logic.get_actions()) == 0
    # invalid schema
    r = session.post(flask_server.base_url + 'actions/', json.dumps({
        'name': 'Example Action',
        'description': '',
        'schema': {'type': 'invalid'},
        'instrument_id': None
    }))
    assert r.status_code == 400
    assert len(logic.get_actions()) == 0
