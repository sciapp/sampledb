# coding: utf-8
"""

"""

import base64
import datetime

import requests
import pytest

import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def auth_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
        assert user.id is not None
    return ('username', 'password'), user


@pytest.fixture
def auth(auth_user):
    return auth_user[0]


@pytest.fixture
def user(auth_user):
    return auth_user[1]


def test_get_instrument_log_entries(flask_server, auth, user, app):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_entries', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "instrument 1 does not exist"
    }

    instrument = sampledb.logic.instruments.create_instrument()
    sampledb.logic.instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Instrument",
        description="This is an example instrument"
    )
    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'log_entry_id': log_entry.id,
            'author': user.id,
            'versions': [
                {
                    'version_id': 1,
                    'log_entry_id': log_entry.id,
                    'utc_datetime': log_entry.versions[0].utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
                    'content': "Example Log Entry",
                    'event_utc_datetime': None,
                    'content_is_markdown': False,
                    'categories': []
                }
            ]
        }
    ]

    category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title='Category',
        theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
    )

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry 2",
        event_utc_datetime=datetime.datetime.strptime('2023-05-03T12:11:10.12345', '%Y-%m-%dT%H:%M:%S.%f'),
        category_ids=[category.id]
    )
    log_entry = sampledb.logic.instrument_log_entries.update_instrument_log_entry(
        log_entry_id=log_entry.id,
        content="**Example Log Entry 2**",
        content_is_markdown=True,
        event_utc_datetime=None,
        category_ids = [category.id]
    )


    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries', auth=auth)
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.json()[1] == {
        'log_entry_id': log_entry.id,
        'author': user.id,
        'versions': [
            {
                'version_id': 1,
                'log_entry_id': log_entry.id,
                'utc_datetime': log_entry.versions[0].utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
                'event_utc_datetime': log_entry.versions[0].event_utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
                'content_is_markdown': False,
                'content': "Example Log Entry 2",
                'categories': [
                    {
                        'category_id': category.id,
                        'title': "Category"
                    }
                ]
            },
            {
                'version_id': 2,
                'log_entry_id': log_entry.id,
                'utc_datetime': log_entry.versions[1].utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
                'event_utc_datetime': None,
                'content_is_markdown': True,
                'content': "**Example Log Entry 2**",
                'categories': [
                    {
                        'category_id': category.id,
                        'title': "Category"
                    }
                ]
            }
        ]
    }


def test_get_instrument_log_entry(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_entries/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': 'instrument 1 does not exist'
    }

    instrument = sampledb.logic.instruments.create_instrument()
    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry 1 for instrument {instrument.id} does not exist"
    }

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'log_entry_id': log_entry.id,
        'author': user.id,
        'versions': [
            {
                'version_id': 1,
                'log_entry_id': log_entry.id,
                'utc_datetime': log_entry.versions[0].utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
                'content': "Example Log Entry",
                'event_utc_datetime': None,
                'content_is_markdown': False,
                'categories': []
            }
        ]
    }

    instrument2 = sampledb.logic.instruments.create_instrument(
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument2.id}/log_entries/{log_entry.id}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry {log_entry.id} for instrument {instrument2.id} does not exist"
    }


def test_instrument_log_file_attachments(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_entries/1/file_attachments/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': 'instrument 1 does not exist'
    }

    instrument = sampledb.logic.instruments.create_instrument()

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/file_attachments/', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/file_attachments/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry 1 for instrument {instrument.id} does not exist"
    }

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/file_attachments/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
        instrument_log_entry_id=log_entry.id,
        file_name="example.txt",
        content="Example Content".encode('utf-8')
    )

    file_attachment = sampledb.logic.instrument_log_entries.get_instrument_log_file_attachments(log_entry.id)[0]

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/file_attachments/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'file_attachment_id': file_attachment.id,
            'file_name': 'example.txt',
            'base64_content': 'RXhhbXBsZSBDb250ZW50',
            'is_hidden': False
        }
    ]

    other_instrument = sampledb.logic.instruments.create_instrument(
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{other_instrument.id}/log_entries/{log_entry.id}/file_attachments/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry {log_entry.id} for instrument {other_instrument.id} does not exist"
    }


def test_instrument_log_file_attachment(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_entries/1/file_attachments/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': 'instrument 1 does not exist'
    }

    instrument = sampledb.logic.instruments.create_instrument()

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/file_attachments/1', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/file_attachments/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry 1 for instrument {instrument.id} does not exist"
    }

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/file_attachments/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"file attachment 1 for log entry {log_entry.id} for instrument {instrument.id} does not exist"
    }

    sampledb.logic.instrument_log_entries.create_instrument_log_file_attachment(
        instrument_log_entry_id=log_entry.id,
        file_name="example.txt",
        content="Example Content".encode('utf-8')
    )

    file_attachment = sampledb.logic.instrument_log_entries.get_instrument_log_file_attachments(log_entry.id)[0]

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/file_attachments/{file_attachment.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'file_attachment_id': file_attachment.id,
        'file_name': 'example.txt',
        'base64_content': 'RXhhbXBsZSBDb250ZW50',
        'is_hidden': False
    }

    other_instrument = sampledb.logic.instruments.create_instrument(
        users_can_view_log_entries=True
    )

    other_log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=other_instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{other_log_entry.id}/file_attachments/{file_attachment.id}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry {other_log_entry.id} for instrument {instrument.id} does not exist"
    }

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{other_instrument.id}/log_entries/{other_log_entry.id}/file_attachments/{file_attachment.id}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"file attachment {file_attachment.id} for log entry {other_log_entry.id} for instrument {other_instrument.id} does not exist"
    }


def test_instrument_log_object_attachments(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_entries/1/object_attachments/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': 'instrument 1 does not exist'
    }

    instrument = sampledb.logic.instruments.create_instrument()

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/object_attachments/', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/object_attachments/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry 1 for instrument {instrument.id} does not exist"
    }

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/object_attachments/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': "Sample Information",
            'type': 'object',
            'properties': {
                'name': {
                    'title': "Name",
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )

    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Test"
            }
        },
        user_id=user.id
    )

    sampledb.logic.instrument_log_entries.create_instrument_log_object_attachment(
        instrument_log_entry_id=log_entry.id,
        object_id=object.id
    )

    object_attachment = sampledb.logic.instrument_log_entries.get_instrument_log_object_attachments(log_entry.id)[0]

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/object_attachments/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'object_attachment_id': object_attachment.id,
            'object_id': object.id,
            'is_hidden': False
        }
    ]

    other_instrument = sampledb.logic.instruments.create_instrument(
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{other_instrument.id}/log_entries/{log_entry.id}/object_attachments/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry {log_entry.id} for instrument {other_instrument.id} does not exist"
    }


def test_instrument_log_object_attachment(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_entries/1/object_attachments/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': 'instrument 1 does not exist'
    }

    instrument = sampledb.logic.instruments.create_instrument()

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/object_attachments/1', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/object_attachments/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry 1 for instrument {instrument.id} does not exist"
    }

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/object_attachments/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"object attachment 1 for log entry {log_entry.id} for instrument {instrument.id} does not exist"
    }

    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': "Sample Information",
            'type': 'object',
            'properties': {
                'name': {
                    'title': "Name",
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )

    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Test"
            }
        },
        user_id=user.id
    )

    sampledb.logic.instrument_log_entries.create_instrument_log_object_attachment(
        instrument_log_entry_id=log_entry.id,
        object_id=object.id
    )

    object_attachment = sampledb.logic.instrument_log_entries.get_instrument_log_object_attachments(log_entry.id)[0]

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/object_attachments/{object_attachment.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'object_attachment_id': object_attachment.id,
        'object_id': object.id,
        'is_hidden': False
    }

    other_instrument = sampledb.logic.instruments.create_instrument(
        users_can_view_log_entries=True
    )

    other_log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=other_instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{other_log_entry.id}/object_attachments/{object_attachment.id}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"log entry {other_log_entry.id} for instrument {instrument.id} does not exist"
    }

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{other_instrument.id}/log_entries/{other_log_entry.id}/object_attachments/{object_attachment.id}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': f"object attachment {object_attachment.id} for log entry {other_log_entry.id} for instrument {other_instrument.id} does not exist"
    }


def test_create_instrument_log_entry(flask_server, auth, user):
    data = {
        'content': "Example Log Entry Text",
        'content_is_markdown': True,
        'category_ids': [1, 7],
        'file_attachments': [
            {
                'file_name': "example.txt",
                'base64_content': base64.b64encode(b'Example Content').decode('ascii')
            }
        ],
        'object_attachments': [
            {
                'object_id': 1
            }
        ]
    }

    r = requests.post(flask_server.base_url + 'api/v1/instruments/1/log_entries/', auth=auth, json=data)
    assert r.status_code == 404
    assert r.json() == {
        'message': 'instrument 1 does not exist'
    }

    instrument = sampledb.logic.instruments.create_instrument()

    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be created by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_create_log_entries=True
    )

    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert r.json() == {
        'message': f"unknown category_ids: 1, 7"
    }

    category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title='Category',
        theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
    )
    data['category_ids'] = [category.id]

    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert r.json() == {
        'message': f"unknown object ids in object_attachments: 1"
    }

    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': "Sample Information",
            'type': 'object',
            'properties': {
                'name': {
                    'title': "Name",
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )

    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Test"
            }
        },
        user_id=user.id
    )

    data['object_attachments'][0]['object_id'] = object.id

    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 201
    log_entry_id = int(r.headers['Location'].split('/')[-1])

    log_entry = sampledb.logic.instrument_log_entries.get_instrument_log_entry(log_entry_id)
    assert log_entry.versions[0].content == 'Example Log Entry Text'
    assert log_entry.user_id == user.id
    assert log_entry.versions[0].content_is_markdown is True

    file_attachments = sampledb.logic.instrument_log_entries.get_instrument_log_file_attachments(log_entry_id)
    assert len(file_attachments) == 1
    file_attachment = file_attachments[0]
    assert file_attachment.content == b'Example Content'
    assert file_attachment.file_name == 'example.txt'

    object_attachments = sampledb.logic.instrument_log_entries.get_instrument_log_object_attachments(log_entry_id)
    assert len(object_attachments) == 1
    object_attachment = object_attachments[0]
    assert object_attachment.object_id == object.id

    data['user_id'] = user.id
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1
    del data['user_id']

    del data['content']
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['content'] = ["Example", "Log", "Entry", "Content"]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1
    data['content'] = "Example Log Entry Content"

    data['content_is_markdown'] = None
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1
    data['content_is_markdown'] = False

    data['category_ids'] = {"category_id": category.id}
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['category_ids'] = [None]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['category_ids'] = [category.id]

    data['file_attachments'] = None
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['file_attachments'] = [
        {
            'file_name': "example.txt",
            'content': "Example Content"
        }
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['file_attachments'] = [
        ("example.txt", base64.b64encode(b'Example Content').decode('ascii'))
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['file_attachments'] = [
        {
            'file_name': list('example.txt'),
            'base64_content': base64.b64encode(b'Example Content').decode('ascii')
        }
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['file_attachments'] = [
        {
            'file_name': 'example' * 100 + '.txt',
            'base64_content': base64.b64encode(b'Example Content').decode('ascii')
        }
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['file_attachments'] = [
        {
            'file_name': "  ",
            'base64_content': base64.b64encode(b'Example Content').decode('ascii')
        }
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['file_attachments'] = [
        {
            'file_name': "example.txt",
            'base64_content': list(base64.b64encode(b'Example Content').decode('ascii'))
        }
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['file_attachments'] = [
        {
            'file_name': "example.txt",
            'base64_content': base64.b64encode(b'Example Content').decode('ascii')
        }
    ]

    data['object_attachments'] = {
        'object_id': object.id
    }
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['object_attachments'] = [object.id]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['object_attachments'] = [
        {
            'object': object.id
        }
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['object_attachments'] = [
        {
            'object_id': str(object.id)
        }
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['object_attachments'] = [
        {
            'object_id': -1
        }
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['object_attachments'] = [
        {
            'object_id': object.id
        },
        {
            'object_id': object.id
        }
    ]
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 1

    data['object_attachments'] = [
        {
            'object_id': object.id
        }
    ]

    data['content'] = None
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 201
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 2

    data['content'] = 'Example Log Entry Test'
    del data['category_ids']
    del data['file_attachments']
    del data['object_attachments']
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 201
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 3

    data['content'] = ''
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 3

    data['content'] = 'Example Log Entry Test'
    data['event_utc_datetime'] = '2024-01-02T03:04:05.678910'
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 201
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 4
    assert sampledb.logic.instrument_log_entries.get_instrument_log_entry(int(r.headers['Location'].rsplit('/', maxsplit=1)[1])).versions[0].event_utc_datetime == datetime.datetime(2024, 1, 2, 3, 4, 5, 678910, datetime.timezone.utc)

    data['event_utc_datetime'] = '2024-01-02T03:04:05'
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 4

    data['event_utc_datetime'] = '0001-01-01T00:00:00.00000'
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 4

    data['event_utc_datetime'] = '9999-01-01T00:00:00.00000'
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 400
    assert len(sampledb.logic.instrument_log_entries.get_instrument_log_entries(instrument.id)) == 4


def test_instrument_log_categories(flask_server, auth, user, app):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_categories/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': 'instrument 1 does not exist'
    }

    instrument = sampledb.logic.instruments.create_instrument()
    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_categories/', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log categories for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_categories/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title="Category",
        theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_categories/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'category_id': category.id,
            'title': "Category"
        }
    ]


def test_instrument_log_category(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_categories/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': 'instrument 1 does not exist'
    }

    instrument = sampledb.logic.instruments.create_instrument()

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_categories/1', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log categories for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_categories/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": f"log category 1 for instrument {instrument.id} does not exist"
    }

    category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title="Category",
        theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_categories/{category.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'category_id': category.id,
        'title': "Category"
    }


def test_get_instrument_log_entry_versions(flask_server, auth, user, app):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_entries/1/versions/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "instrument 1 does not exist"
    }

    instrument = sampledb.logic.instruments.create_instrument()
    sampledb.logic.instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Instrument",
        description="This is an example instrument"
    )
    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/versions/', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/versions/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "log entry 1 for instrument 1 does not exist"
    }

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/versions/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'version_id': 1,
            'log_entry_id': log_entry.id,
            'utc_datetime': log_entry.versions[0].utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
            'content': "Example Log Entry",
            'event_utc_datetime': None,
            'content_is_markdown': False,
            'categories': []
        }
    ]

    category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title='Category',
        theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
    )

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry 2",
        event_utc_datetime=datetime.datetime.strptime('2023-05-03T12:11:10.12345', '%Y-%m-%dT%H:%M:%S.%f'),
        category_ids=[category.id]
    )
    log_entry = sampledb.logic.instrument_log_entries.update_instrument_log_entry(
        log_entry_id=log_entry.id,
        content="**Example Log Entry 2**",
        content_is_markdown=True,
        event_utc_datetime=None,
        category_ids = [category.id]
    )


    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/versions/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'version_id': 1,
            'log_entry_id': log_entry.id,
            'utc_datetime': log_entry.versions[0].utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
            'event_utc_datetime': log_entry.versions[0].event_utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
            'content_is_markdown': False,
            'content': "Example Log Entry 2",
            'categories': [
                {
                    'category_id': category.id,
                    'title': "Category"
                }
            ]
        },
        {
            'version_id': 2,
            'log_entry_id': log_entry.id,
            'utc_datetime': log_entry.versions[1].utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
            'event_utc_datetime': None,
            'content_is_markdown': True,
            'content': "**Example Log Entry 2**",
            'categories': [
                {
                    'category_id': category.id,
                    'title': "Category"
                }
            ]
        }
    ]


def test_get_instrument_log_entry_version(flask_server, auth, user, app):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_entries/1/versions/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "instrument 1 does not exist"
    }

    instrument = sampledb.logic.instruments.create_instrument()
    sampledb.logic.instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Instrument",
        description="This is an example instrument"
    )
    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/versions/1', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/versions/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "log entry 1 for instrument 1 does not exist"
    }

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/versions/1', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'version_id': 1,
        'log_entry_id': log_entry.id,
        'utc_datetime': log_entry.versions[0].utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f'),
        'content': "Example Log Entry",
        'event_utc_datetime': None,
        'content_is_markdown': False,
        'categories': []
    }

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/versions/2', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "version 2 for log entry 1 for instrument 1 does not exist"
    }


def test_post_instrument_log_entry_version(flask_server, auth, user, app):
    r = requests.post(flask_server.base_url + 'api/v1/instruments/1/log_entries/1/versions/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "instrument 1 does not exist"
    }

    instrument = sampledb.logic.instruments.create_instrument()
    sampledb.logic.instrument_translations.set_instrument_translation(
        language_id=sampledb.logic.languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name="Example Instrument",
        description="This is an example instrument"
    )
    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/versions/', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        users_can_view_log_entries=True
    )

    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/versions/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "log entry 1 for instrument 1 does not exist"
    }

    log_entry = sampledb.logic.instrument_log_entries.create_instrument_log_entry(
        instrument_id=instrument.id,
        user_id=user.id,
        content="Example Log Entry",
        category_ids=()
    )

    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/versions/', auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        'message': "expected json object containing version_id, log_entry_id, content, content_is_markdown, category_ids, file_attachments, object attachments and event_utc_datetime"
    }

    category = sampledb.logic.instrument_log_entries.create_instrument_log_category(
        instrument_id=instrument.id,
        title='Category',
        theme=sampledb.logic.instrument_log_entries.InstrumentLogCategoryTheme.RED
    )

    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': "Sample Information",
            'type': 'object',
            'properties': {
                'name': {
                    'title': "Name",
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )

    object = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': "Test"
            }
        },
        user_id=user.id
    )

    for data in [
        {
            'version_id': 2,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': [],
            'object_attachments': [],
            'category_ids': []
        },
        {
            'version_id': 3,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': True,
            'event_utc_datetime': None,
            'file_attachments': [],
            'object_attachments': [],
            'category_ids': []
        },
        {
            'version_id': 4,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': False,
            'event_utc_datetime': datetime.datetime.now().replace(tzinfo=None).strftime('%Y-%m-%dT%H:%M:%S.%f'),
            'file_attachments': [],
            'object_attachments': [],
            'category_ids': []
        },
        {
            'version_id': 5,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': [],
            'object_attachments': [],
            'category_ids': [category.id]
        },
        {
            'version_id': 6,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': [],
            'object_attachments': [{'object_id': object.id}],
            'category_ids': [category.id]
        },
        {
            'version_id': 7,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': [],
            'object_attachments': [],
            'category_ids': [category.id]
        },
        {
            'version_id': 8,
            'log_entry_id': log_entry.id,
            'content': '',
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': [],
            'object_attachments': [{'object_id': object.id}],
            'category_ids': [category.id]
        },
        {
            'version_id': 9,
            'log_entry_id': log_entry.id,
            'content': '',
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': [{
                'file_name': "example.txt",
                'base64_content': base64.b64encode(b'Example Content').decode('ascii')
            }],
            'object_attachments': [],
            'category_ids': [category.id]
        },
        {
            'version_id': 10,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': [{
                'file_name': "example.txt",
                'base64_content': base64.b64encode(b'Example Content').decode('ascii')
            }],
            'object_attachments': [],
            'category_ids': [category.id]
        },
        {
            'version_id': 11,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': [],
            'object_attachments': [],
            'category_ids': [category.id]
        },
        {
            'version_id': 12,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': [{
                'file_name': "example.txt",
                'base64_content': base64.b64encode(b'Example Content').decode('ascii')
            }],
            'object_attachments': [],
            'category_ids': [category.id]
        },
        {
            'version_id': 13,
            'log_entry_id': log_entry.id,
            'content': "Example Log Entry",
            'content_is_markdown': False,
            'event_utc_datetime': None,
            'file_attachments': None,
            'object_attachments': [],
            'category_ids': [category.id]
        }
    ]:
        file_attachments_before = log_entry.file_attachments
        object_attachments_before = log_entry.object_attachments
        r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/versions/', auth=auth, json=data)
        assert r.content == b''
        assert r.status_code == 201
        assert r.headers['Location'] == flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/versions/{data['version_id']}'
        log_entry = sampledb.logic.instrument_log_entries.get_instrument_log_entry(log_entry.id)
        assert log_entry.versions[-1].version_id == data['version_id']
        assert log_entry.versions[-1].content == data['content']
        assert log_entry.versions[-1].content_is_markdown == data['content_is_markdown']
        if data['event_utc_datetime'] is None:
            assert log_entry.versions[-1].event_utc_datetime is None
        else:
            assert log_entry.versions[-1].event_utc_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f') == data['event_utc_datetime']
        assert [category.id for category in log_entry.versions[-1].categories] == data['category_ids']
        assert len({object_attachment.object_id for object_attachment in log_entry.object_attachments}) == len(log_entry.object_attachments)
        if data['object_attachments'] is None:
            assert log_entry.object_attachments == object_attachments_before
        else:
            assert {object_attachment.object_id for object_attachment in log_entry.object_attachments if not object_attachment.is_hidden} == set(object_attachment['object_id'] for object_attachment in data['object_attachments'])
        if data['file_attachments'] is None:
            assert log_entry.file_attachments == file_attachments_before
        else:
            assert {(file_attachment.file_name, base64.b64encode(file_attachment.content).decode('ascii')) for file_attachment in log_entry.file_attachments if not file_attachment.is_hidden} == {(file_attachment['file_name'], file_attachment['base64_content']) for file_attachment in data['file_attachments']}

    next_version_id = len(log_entry.versions) + 1
    for data, expected_message in [
        (
            {
                'version_id': next_version_id + 1,
                'log_entry_id': log_entry.id,
                'content': "Example Log Entry",
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            f'version_id must be {next_version_id}'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id + 1,
                'content': "Example Log Entry",
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            f'log_entry_id must be {log_entry.id}'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': "Example Log Entry",
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id],
                'unexpected_key': True
            },
            'expected json object containing version_id, log_entry_id, content, content_is_markdown, category_ids, file_attachments, object attachments and event_utc_datetime'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': "Example Log Entry",
                'content_is_markdown': None,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            'expected true or false for content_is_markdown'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': 1,
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            'expected string or null for content'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            'log entry must contain content or an attachment'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': None,
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            'log entry must contain content or an attachment'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': "Example Log Entry",
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.title]
            },
            'expected list containing integer numbers for category_ids'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': "Example Log Entry",
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': category.id
            },
            'expected list containing integer numbers for category_ids'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': "Example Log Entry",
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id + 1]
            },
            'unknown category_ids: 2'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': "Example Log Entry",
                'content_is_markdown': False,
                'event_utc_datetime': datetime.datetime.now().replace(tzinfo=None).strftime('%Y-%m-%dT%H:%M:%S'),
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            'event_utc_datetime must be in ISO format including microseconds, e.g. 2024-01-02T03:04:05.678910'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': "Example Log Entry",
                'content_is_markdown': False,
                'event_utc_datetime': (datetime.datetime.now().replace(tzinfo=None) + datetime.timedelta(days=366000)).strftime('%Y-%m-%dT%H:%M:%S.%f'),
                'file_attachments': [],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            'event_utc_datetime must be not be more than 1000 years before or after the current date'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [{'object_id': object.id}, {'object_id': object.id}],
                'category_ids': [category.id]
            },
            f'duplicate object id in object_attachments: {object.id}'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [{'object_id': object.id}, {'object_id': object.id + 1}, {'object_id': object.id + 2}],
                'category_ids': [category.id]
            },
            f'unknown object ids in object_attachments: {object.id + 1}, {object.id + 2}'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': {'object_id': object.id},
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing object_id for object_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [object.id],
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing object_id for object_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [{'object_id': str(object.id)}],
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing object_id for object_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [{'object': object.id}],
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing object_id for object_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [],
                'object_attachments': [{'object_id': -1}],
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing object_id for object_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': {
                    'file_name': "example.txt",
                    'base64_content': base64.b64encode(b'Example Content').decode('ascii')
                },
                'object_attachments': [],
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing file_name and base64_content for file_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': ["example.txt", base64.b64encode(b'Example Content').decode('ascii')],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing file_name and base64_content for file_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [{
                    'file_name': "example.txt",
                    'base64_content': base64.b64encode(b'Example Content').decode('ascii'),
                    'content': 'Example Content'
                }],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing file_name and base64_content for file_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [{
                    'file_name': 1,
                    'base64_content': base64.b64encode(b'Example Content').decode('ascii')
                }],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing file_name and base64_content for file_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [{
                    'file_name': "example.txt",
                    'base64_content': 1
                }],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            f'expected list containing dicts containing file_name and base64_content for file_attachments'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [{
                    'file_name': "",
                    'base64_content': base64.b64encode(b'Example Content').decode('ascii')
                }],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            f'file attachment names must not be empty and must contain at most 256 characters'
        ),
        (
            {
                'version_id': next_version_id,
                'log_entry_id': log_entry.id,
                'content': '',
                'content_is_markdown': False,
                'event_utc_datetime': None,
                'file_attachments': [{
                    'file_name': "x" * 257,
                    'base64_content': base64.b64encode(b'Example Content').decode('ascii')
                }],
                'object_attachments': [],
                'category_ids': [category.id]
            },
            f'file attachment names must not be empty and must contain at most 256 characters'
        ),
    ]:
        r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/{log_entry.id}/versions/', auth=auth, json=data)
        assert r.status_code == 400
        assert r.json() == {
            'message': expected_message
        }
