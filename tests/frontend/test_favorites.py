# coding: utf-8
"""

"""


import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
import sampledb.logic


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
def actions(flask_server):
    actions = [sampledb.models.Action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Action {}'.format(i + 1),
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            }, 'required': ['name']
        },
        description='',
        instrument_id=None
    ) for i in range(2)]
    for action in actions:
        sampledb.db.session.add(action)
        sampledb.db.session.commit()
        # force attribute refresh
        assert action.id is not None
    return actions


@pytest.fixture
def instruments(flask_server):
    instruments = [sampledb.models.Instrument(
        'Instrument {}'.format(i + 1)
    ) for i in range(2)]
    for instrument in instruments:
        sampledb.db.session.add(instrument)
        sampledb.db.session.commit()
        # force attribute refresh
        assert instrument.id is not None
    return instruments


def test_favorite_actions(actions, flask_server, user_session):
    r = user_session.get(flask_server.base_url + 'actions/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    action_headings = [heading for heading in document.find_all('h2') if heading.find('button')]
    favorite_action_headings = []
    other_action_headings = []
    for heading in action_headings:
        if 'fav-star-on' in heading.find('button')['class']:
            favorite_action_headings.append(heading.find('a').text)
        else:
            other_action_headings.append(heading.find('a').text)
    assert favorite_action_headings == []
    assert other_action_headings == ['Action 1', 'Action 2']

    # Add favorite action
    csrf_token = document.find(attrs={'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'users/me/favorite_actions/', data={
        'csrf_token': csrf_token,
        'action_id': actions[1].id
    })
    assert r.status_code == 200
    assert sampledb.logic.favorites.get_user_favorite_action_ids(user_session.user_id) == [actions[1].id]
    document = BeautifulSoup(r.content, 'html.parser')
    action_headings = [heading for heading in document.find_all('h2') if heading.find('button')]
    favorite_action_headings = []
    other_action_headings = []
    for heading in action_headings:
        if 'fav-star-on' in heading.find('button')['class']:
            favorite_action_headings.append(heading.find('a').text)
        else:
            other_action_headings.append(heading.find('a').text)
    assert favorite_action_headings == ['Action 2']
    assert other_action_headings == ['Action 1']

    # Remove favorite action
    csrf_token = document.find(attrs={'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'users/me/favorite_actions/', data={
        'csrf_token': csrf_token,
        'action_id': actions[1].id
    })
    assert r.status_code == 200
    assert sampledb.logic.favorites.get_user_favorite_action_ids(user_session.user_id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    action_headings = [heading for heading in document.find_all('h2') if heading.find('button')]
    favorite_action_headings = []
    other_action_headings = []
    for heading in action_headings:
        if 'fav-star-on' in heading.find('button')['class']:
            favorite_action_headings.append(heading.find('a').text)
        else:
            other_action_headings.append(heading.find('a').text)
    assert favorite_action_headings == []
    assert other_action_headings == ['Action 1', 'Action 2']


def test_favorite_instruments(instruments, flask_server, user_session):
    r = user_session.get(flask_server.base_url + 'instruments/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    instrument_headings = [heading for heading in document.find_all('h2') if heading.find('button')]
    favorite_instrument_headings = []
    other_instrument_headings = []
    for heading in instrument_headings:
        if 'fav-star-on' in heading.find('button')['class']:
            favorite_instrument_headings.append(heading.find('a').text)
        else:
            other_instrument_headings.append(heading.find('a').text)
    assert favorite_instrument_headings == []
    assert other_instrument_headings == ['Instrument 1', 'Instrument 2']

    # Add favorite instrument
    csrf_token = document.find(attrs={'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'users/me/favorite_instruments/', data={
        'csrf_token': csrf_token,
        'instrument_id': instruments[1].id
    })
    assert r.status_code == 200
    assert sampledb.logic.favorites.get_user_favorite_instrument_ids(user_session.user_id) == [instruments[1].id]
    document = BeautifulSoup(r.content, 'html.parser')
    instrument_headings = [heading for heading in document.find_all('h2') if heading.find('button')]
    favorite_instrument_headings = []
    other_instrument_headings = []
    for heading in instrument_headings:
        if 'fav-star-on' in heading.find('button')['class']:
            favorite_instrument_headings.append(heading.find('a').text)
        else:
            other_instrument_headings.append(heading.find('a').text)
    assert favorite_instrument_headings == ['Instrument 2']
    assert other_instrument_headings == ['Instrument 1']

    # Remove favorite instrument
    csrf_token = document.find(attrs={'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'users/me/favorite_instruments/', data={
        'csrf_token': csrf_token,
        'instrument_id': instruments[1].id
    })
    assert r.status_code == 200
    assert sampledb.logic.favorites.get_user_favorite_instrument_ids(user_session.user_id) == []
    document = BeautifulSoup(r.content, 'html.parser')
    instrument_headings = [heading for heading in document.find_all('h2') if heading.find('button')]
    favorite_instrument_headings = []
    other_instrument_headings = []
    for heading in instrument_headings:
        if 'fav-star-on' in heading.find('button')['class']:
            favorite_instrument_headings.append(heading.find('a').text)
        else:
            other_instrument_headings.append(heading.find('a').text)
    assert favorite_instrument_headings == []
    assert other_instrument_headings == ['Instrument 1', 'Instrument 2']
