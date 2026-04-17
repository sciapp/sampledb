# coding: utf-8
"""

"""

import requests
import pytest
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

import sampledb
import sampledb.models
import sampledb.logic


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return user


@pytest.fixture
def instrument():
    instrument = sampledb.logic.instruments.create_instrument(
        users_can_create_log_entries=True
    )
    sampledb.logic.instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Instrument",
        description="This is an example instrument"
    )
    # force attribute refresh
    assert instrument.id is not None
    return instrument


@pytest.fixture
def action(instrument):
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
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
        instrument_id=instrument.id
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        action_id=action.id,
        name='Example Action',
        description=''
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


def test_external_links(flask_server, app, driver, user):
    instrument1 = sampledb.logic.instruments.create_instrument(
        users_can_create_log_entries=True
    )
    sampledb.logic.instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument1.id,
        name="Example Instrument 1",
        description=""
    )
    instrument2 = sampledb.logic.instruments.create_instrument(
        users_can_create_log_entries=True
    )
    sampledb.logic.instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument1.id,
        name="Example Instrument 1",
        description=""
    )

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')

    sampledb.frontend.utils.merge_external_links.cache_clear()
    flask_server.app.config['INSTRUMENT_LINKS_BY_INSTRUMENT_ID'] = {
        '*': [
            {
                'links': [
                    {
                        'name': {'en': 'Example Link 1'},
                        'url': 'http://example.org/link1'
                    },
                    {
                        'name': {'en': 'Example Link 2'},
                        'url': 'http://example.org/link2'
                    }
                ],
                'label': {'en': 'Links'},
                'icon': 'fa-external-link',
                'id_placeholder': '<ID>'
            }
        ],
        instrument1.id: [
            {
                'links': [
                    {
                        'name': {'en': 'Example Link 3'},
                        'url': 'http://example.org/link3'
                    }
                ],
                'label': {'en': 'Links'},
                'icon': 'fa-external-link',
                'id_placeholder': '<ID>'
            }
        ]
    }

    driver.get(flask_server.base_url + f'instruments/{instrument1.id}')
    external_links = driver.find_elements(By.CSS_SELECTOR, 'ul[aria-labelledby="linksDropdownMenuButton"] li a')
    assert {(external_link.get_attribute("textContent"), external_link.get_attribute('href')) for external_link in external_links} == {
        (
            'Example Link 1',
            'http://example.org/link1'
        ),
        (
            'Example Link 2',
            'http://example.org/link2'
        ),
        (
            'Example Link 3',
            'http://example.org/link3'
        ),
    }

    driver.get(flask_server.base_url + f'instruments/{instrument2.id}')
    external_links = driver.find_elements(By.CSS_SELECTOR, 'ul[aria-labelledby="linksDropdownMenuButton"] li a')
    assert {(external_link.get_attribute("textContent"), external_link.get_attribute('href')) for external_link in external_links} == {
        (
            'Example Link 1',
            'http://example.org/link1'
        ),
        (
            'Example Link 2',
            'http://example.org/link2'
        ),
    }
    sampledb.frontend.utils.merge_external_links.cache_clear()


def test_instrument_log_file_attachment_must_match_log_entry(flask_server, user):
    accessible_instrument = sampledb.logic.instruments.create_instrument()
    sampledb.logic.instruments.set_instrument_responsible_users(
        instrument_id=accessible_instrument.id,
        user_ids=[user.id]
    )
    accessible_log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=accessible_instrument.id,
        user_id=user.id,
        content='Accessible log entry'
    )
    sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
        instrument_log_entry_id=accessible_log_entry.id,
        file_name='accessible.txt',
        content=b'accessible'
    )

    inaccessible_instrument = sampledb.logic.instruments.create_instrument(
        users_can_create_log_entries=True
    )
    inaccessible_log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=inaccessible_instrument.id,
        user_id=user.id,
        content='Inaccessible log entry'
    )
    sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
        instrument_log_entry_id=inaccessible_log_entry.id,
        file_name='inaccessible.txt',
        content=b'inaccessible'
    )
    inaccessible_attachment = sampledb.logic.instrument_log_entries.get_instrument_log_file_attachments(
        inaccessible_log_entry.id
    )[0]

    session = requests.session()
    assert session.get(flask_server.base_url + f'users/{user.id}/autologin').status_code == 200

    response = session.get(
        flask_server.base_url
        + f'instruments/{accessible_instrument.id}/log/{accessible_log_entry.id}/file_attachments/{inaccessible_attachment.id}'
    )
    assert response.status_code == 404
