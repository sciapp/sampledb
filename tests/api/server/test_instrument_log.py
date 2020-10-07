# coding: utf-8
"""

"""

import base64
import requests
import pytest

import sampledb
import sampledb.logic
import sampledb.models


@pytest.fixture
def auth_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.logic.users.create_user(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
        sampledb.logic.authentication.add_other_authentication(user.id, 'username', 'password')
        assert user.id is not None
    return ('username', 'password'), user


@pytest.fixture
def auth(auth_user):
    return auth_user[0]


@pytest.fixture
def user(auth_user):
    return auth_user[1]


def test_get_instrument_log_entries(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_entries', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': "instrument 1 does not exist"
    }

    instrument = sampledb.logic.instruments.create_instrument(
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
        name=instrument.name,
        description=instrument.description,
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
                    'utc_datetime': log_entry.versions[0].utc_datetime.isoformat(),
                    'content': "Example Log Entry",
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
        category_ids=[category.id]
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
                'utc_datetime': log_entry.versions[0].utc_datetime.isoformat(),
                'content': "Example Log Entry 2",
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

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="This is an example instrument"
    )
    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        name=instrument.name,
        description=instrument.description,
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
                'utc_datetime': log_entry.versions[0].utc_datetime.isoformat(),
                'content': "Example Log Entry",
                'categories': []
            }
        ]
    }

    instrument2 = sampledb.logic.instruments.create_instrument(
        name="Example Instrument 2",
        description="This is an example instrument",
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

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="This is an example instrument"
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/file_attachments/', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        name=instrument.name,
        description=instrument.description,
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
        name="Example Instrument 2",
        description="This is an example instrument",
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

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="This is an example instrument"
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/file_attachments/1', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        name=instrument.name,
        description=instrument.description,
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
        name="Example Instrument 2",
        description="This is an example instrument",
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

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="This is an example instrument"
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/object_attachments/', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        name=instrument.name,
        description=instrument.description,
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
        name="Example Action",
        description="",
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
        name="Example Instrument 2",
        description="This is an example instrument",
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

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="This is an example instrument"
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/1/object_attachments/1', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        name=instrument.name,
        description=instrument.description,
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
        name="Example Action",
        description="",
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
        name="Example Instrument 2",
        description="This is an example instrument",
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

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="This is an example instrument"
    )

    r = requests.post(flask_server.base_url + f'api/v1/instruments/{instrument.id}/log_entries/', auth=auth, json=data)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log entries for instrument {instrument.id} can only be created by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        name=instrument.name,
        description=instrument.description,
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
        name="Example Action",
        description="",
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


def test_instrument_log_categories(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/instruments/1/log_categories/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        'message': 'instrument 1 does not exist'
    }

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="This is an example instrument"
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/1/log_categories/', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log categories for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        name=instrument.name,
        description=instrument.description,
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

    instrument = sampledb.logic.instruments.create_instrument(
        name="Example Instrument",
        description="This is an example instrument"
    )

    r = requests.get(flask_server.base_url + f'api/v1/instruments/1/log_categories/1', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        'message': f"log categories for instrument {instrument.id} can only be accessed by instrument scientists"
    }

    sampledb.logic.instruments.update_instrument(
        instrument_id=instrument.id,
        name=instrument.name,
        description=instrument.description,
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