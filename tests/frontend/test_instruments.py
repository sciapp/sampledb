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
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture
def instrument():
    instrument = sampledb.logic.instruments.create_instrument(
        name='Example Instrument',
        description='This is an example instrument',
        users_can_create_log_entries=True
    )
    # force attribute refresh
    assert instrument.id is not None
    return instrument


@pytest.fixture
def action(instrument):
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Sample Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        },
        description='',
        instrument_id=instrument.id
    )
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def object_id(user, action):
    data = {'name': {'_type': 'text', 'text': 'Object'}}
    return sampledb.logic.objects.create_object(user_id=user.id, action_id=action.id, data=data).id


def test_create_instrument_log_entry(flask_server, user, instrument, object_id):
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 0
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    r = session.get(flask_server.base_url + 'instruments/{}'.format(instrument.id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    log_entry_content_element = document.find('textarea', {'name': 'content'})
    for parent_element in log_entry_content_element.parents:
        if parent_element is not None and parent_element.name == 'form':
            log_entry_form = parent_element
            break
    else:
        assert False
    csrf_token = log_entry_form.find('input', {'name': 'csrf_token'})['value']

    data = {
        'csrf_token': csrf_token,
        'content': 'Test Log Entry'
    }
    r = session.post(flask_server.base_url + 'instruments/{}'.format(instrument.id), data=data)
    assert r.status_code == 200
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1
    log_entry = sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)[0]
    assert log_entry.user_id == user.id
    assert log_entry.instrument_id == instrument.id
    assert log_entry.versions[0].content == 'Test Log Entry'
    assert log_entry.versions[0].categories == []

    category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title="Error",
        theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
    )

    data = {
        'csrf_token': csrf_token,
        'content': 'Test Log Entry 2',
        'categories': [str(category.id)]
    }
    r = session.post(flask_server.base_url + 'instruments/{}'.format(instrument.id), data=data)
    assert r.status_code == 200
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 2
    for log_entry in sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id):
        if log_entry.versions[0].content == 'Test Log Entry 2':
            assert log_entry.versions[0].categories == [category]
            break
    else:
        assert False

