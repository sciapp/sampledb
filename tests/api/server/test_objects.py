# coding: utf-8
"""

"""

import requests
import pytest
import json
import uuid
import datetime

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
def other_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        assert user.id is not None
    return  user


@pytest.fixture
def auth(auth_user):
    return auth_user[0]


@pytest.fixture
def user(auth_user):
    return auth_user[1]


@pytest.fixture
def action():
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                },
                'file': {
                    'title': 'Example File',
                    'type': 'file'
                }
            },
            'required': ['name']
        }
    )
    sampledb.logic.action_translations.set_action_translation(
        language_id=sampledb.logic.action_translations.Language.ENGLISH,
        action_id=action.id,
        name="Example Action",
        description="This is an example action"
    )
    return sampledb.logic.actions.get_action(
        action_id=action.id
    )


@pytest.fixture
def other_action():
    other_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.MEASUREMENT,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                },
                'sample': {
                    'title': 'Sample',
                    'type': 'object_reference',
                    'action_type_id': -99
                }
            },
            'required': ['name']
        }
    )
    return other_action


def test_get_object_version(flask_server, auth, user, action):
    r = requests.get(flask_server.base_url + 'api/v1/objects/1/versions/0', auth=auth)
    assert r.status_code == 404
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/{}'.format(object.object_id, object.version_id), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": object.object_id,
        "version_id": object.version_id,
        "action_id": object.action_id,
        "user_id": user.id,
        "utc_datetime": object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": object.schema,
        "data": object.data,
        "fed_object_id": object.fed_object_id,
        "fed_version_id": object.fed_version_id,
        "component_id": object.component_id
    }
    r = requests.get(flask_server.base_url + 'api/v1/objects/1/versions/1', auth=auth)
    assert r.status_code == 404

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/{}?embed_user=1'.format(object.object_id, object.version_id), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": object.object_id,
        "version_id": object.version_id,
        "action_id": object.action_id,
        "user_id": user.id,
        "user": {
            'user_id': user.id,
            'name': user.name,
            'orcid': None,
            'affiliation': None,
            'role': None
        },
        "utc_datetime": object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": object.schema,
        "data": object.data,
        "fed_object_id": object.fed_object_id,
        "fed_version_id": object.fed_version_id,
        "component_id": object.component_id
    }

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/{}?embed_action=1'.format(object.object_id, object.version_id), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": object.object_id,
        "version_id": object.version_id,
        "action_id": object.action_id,
        "action": None,
        "user_id": user.id,
        "utc_datetime": object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": object.schema,
        "data": object.data,
        "fed_object_id": object.fed_object_id,
        "fed_version_id": object.fed_version_id,
        "component_id": object.component_id
    }

    sampledb.logic.action_permissions.set_action_permissions_for_all_users(object.action_id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/{}?embed_action=1'.format(object.object_id, object.version_id), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": object.object_id,
        "version_id": object.version_id,
        "action_id": object.action_id,
        "action": {
            'action_id': action.id,
            'instrument_id': None,
            'user_id': None,
            'type': 'sample',
            'type_id': sampledb.models.ActionType.SAMPLE_CREATION,
            'name': action.name['en'],
            'description': action.description['en'],
            'is_hidden': action.is_hidden,
            'schema': action.schema
        },
        "user_id": user.id,
        "utc_datetime": object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": object.schema,
        "data": object.data,
        "fed_object_id": object.fed_object_id,
        "fed_version_id": object.fed_version_id,
        "component_id": object.component_id
    }

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/0?include_diff=1'.format(object.object_id, object.version_id), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": object.object_id,
        "version_id": 0,
        "action_id": object.action_id,
        "user_id": user.id,
        "utc_datetime": object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": object.schema,
        "fed_object_id": object.fed_object_id,
        "fed_version_id": object.fed_version_id,
        "component_id": object.component_id,
        "data": object.data
    }

    object_json = {
        "data": {
            "name": {
                '_type': 'text',
                'text': 'Example2',
            }
        }
    }

    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    new_object = sampledb.logic.objects.get_object(object_id=object.object_id, version_id=object.version_id + 1)

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/{}?include_diff=1'.format(object.object_id, new_object.version_id), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": new_object.object_id,
        "version_id": new_object.version_id,
        "action_id": new_object.action_id,
        "user_id": user.id,
        "utc_datetime": new_object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": new_object.schema,
        "fed_object_id": new_object.fed_object_id,
        "fed_version_id": new_object.fed_version_id,
        "component_id": new_object.component_id,
        "data": new_object.data,
        "data_diff": {
            "name": {
                "_before": {
                    "_type": "text",
                    "text": "Example"
                },
                "_after": {
                    "_type": "text",
                    "text": "Example2"
                }
            }
        }
    }

    component = sampledb.logic.components.add_component(str(uuid.uuid4()))
    imported_object = sampledb.logic.objects.insert_fed_object_version(
        fed_object_id=1,
        fed_version_id=1,
        component_id=component.id,
        action_id=None,
        schema=None,
        data=None,
        user_id=None,
        utc_datetime=datetime.datetime.utcnow()
    )
    sampledb.logic.object_permissions.set_user_object_permissions(imported_object.object_id, user.id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/{}?include_diff=1'.format(imported_object.object_id, 0), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": imported_object.object_id,
        "version_id": 0,
        "action_id": None,
        "user_id": None,
        "utc_datetime": imported_object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": None,
        "fed_object_id": 1,
        "fed_version_id": 1,
        "component_id": component.id,
        "data": None
    }

    imported_object = sampledb.logic.objects.insert_fed_object_version(
        fed_object_id=1,
        fed_version_id=2,
        component_id=component.id,
        action_id=None,
        schema=None,
        data=None,
        user_id=None,
        utc_datetime=datetime.datetime.utcnow()
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/{}?include_diff=1'.format(imported_object.object_id, 1), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": imported_object.object_id,
        "version_id": 1,
        "action_id": None,
        "user_id": None,
        "utc_datetime": imported_object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": None,
        "fed_object_id": 1,
        "fed_version_id": 2,
        "component_id": component.id,
        "data": None,
        "data_diff": None
    }

    imported_object = sampledb.logic.objects.insert_fed_object_version(
        fed_object_id=1,
        fed_version_id=3,
        component_id=component.id,
        action_id=None,
        schema=object.schema,
        data=object.data,
        user_id=None,
        utc_datetime=datetime.datetime.utcnow()
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/{}?include_diff=1'.format(imported_object.object_id, 2), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": imported_object.object_id,
        "version_id": 2,
        "action_id": None,
        "user_id": None,
        "utc_datetime": imported_object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": object.schema,
        "fed_object_id": 1,
        "fed_version_id": 3,
        "component_id": component.id,
        "data": object.data,
        "data_diff": {
            '_before': None,
            '_after': object.data
        }
    }

    imported_object = sampledb.logic.objects.insert_fed_object_version(
        fed_object_id=1,
        fed_version_id=4,
        component_id=component.id,
        action_id=None,
        schema=None,
        data=None,
        user_id=None,
        utc_datetime=datetime.datetime.utcnow()
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/versions/{}?include_diff=1'.format(imported_object.object_id, 3), auth=auth)
    assert r.status_code == 200
    assert json.loads(r.content.decode('utf-8')) == {
        "object_id": imported_object.object_id,
        "version_id": 3,
        "action_id": None,
        "user_id": None,
        "utc_datetime": imported_object.utc_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "schema": None,
        "fed_object_id": 1,
        "fed_version_id": 4,
        "component_id": component.id,
        "data": None,
        "data_diff": {
            '_before': object.data,
            '_after': None
        }
    }


def test_get_object(flask_server, auth, user, action):
    r = requests.get(flask_server.base_url + 'api/v1/objects/1', auth=auth)
    assert r.status_code == 404
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'] == flask_server.base_url + 'api/v1/objects/{}/versions/{}'.format(object.object_id, object.version_id)


def test_post_object_version(flask_server, auth, user, action):
    r = requests.get(flask_server.base_url + 'api/v1/objects/1', auth=auth)
    assert r.status_code == 404
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'].startswith('Failed to decode JSON object')

    object_json=[]
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'JSON object body required'

    object_json = {'unknown': 1}
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'invalid key \'unknown\''

    object_json = {
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    assert r.headers['Location'] == flask_server.base_url + 'api/v1/objects/{}/versions/{}'.format(object.object_id, object.version_id + 1)
    new_object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert new_object.version_id == object.version_id + 1
    assert new_object.data == object_json['data']
    object = new_object

    object_json = {}
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'data or data_diff must be set'

    object_json = {
        'object_id': object.object_id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    assert r.headers['Location'] == flask_server.base_url + 'api/v1/objects/{}/versions/{}'.format(object.object_id, object.version_id + 1)
    new_object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert new_object.version_id == object.version_id + 1
    assert new_object.data == object_json['data']
    object = new_object

    object_json = {
        'object_id': object.object_id,
        'data_diff': {
            'name': {
                '_before': {
                    '_type': 'text',
                    'text': 'Wrong Object Name',
                },
                '_after': {
                    '_type': 'text',
                    'text': 'Example Object (Diff)'
                }
            }
        }
    }

    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'failed to apply diff'

    object_json = {
        'object_id': object.object_id,
        'data_diff': {
            'name': {
                '_before': {
                    'text': 'Example Object',
                    '_type': 'text'
                },
                '_after': {
                    'text': 'Example Object (Diff)',
                    '_type': 'text'
                }
            }
        }
    }
    result_object_json = {
        'object_id': object.object_id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object (Diff)'
            }
        }
    }

    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    assert r.headers['Location'] == flask_server.base_url + 'api/v1/objects/{}/versions/{}'.format(object.object_id, object.version_id + 1)
    new_object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert new_object.version_id == object.version_id + 1
    assert new_object.data == result_object_json['data']
    object = new_object

    object_json = {
        'object_id': object.object_id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object (data and data_diff)'
            }
        },
        'data_diff': {
            'name': {
                '_before': {
                    'text': 'Example Object (Diff)',
                    '_type': 'text'
                },
                '_after': {
                    'text': 'Example Object (inconsistent)',
                    '_type': 'text'
                }
            }
        }
    }

    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'data and data_diff are conflicting'

    object_json = {
        'object_id': object.object_id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object (data and data_diff)'
            }
        },
        'data_diff': {
            'name': {
                '_before': {
                    'text': 'Example Object (Diff)',
                    '_type': 'text'
                },
                '_after': {
                    'text': 'Example Object (data and data_diff)',
                    '_type': 'text'
                }
            }
        }
    }

    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    assert r.headers['Location'] == flask_server.base_url + 'api/v1/objects/{}/versions/{}'.format(object.object_id, object.version_id + 1)
    new_object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert new_object.version_id == object.version_id + 1
    assert new_object.data == object_json['data']
    object = new_object

    object_json = {
        'object_id': object.object_id + 1,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'object_id must be {}'.format(object.object_id)

    object_json = {
        'version_id': object.version_id + 1,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    assert r.headers['Location'] == flask_server.base_url + 'api/v1/objects/{}/versions/{}'.format(object.object_id, object.version_id + 1)
    new_object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert new_object.version_id == object.version_id + 1
    assert new_object.data == object_json['data']
    object = new_object

    object_json = {
        'version_id': object.version_id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'version_id must be {}'.format(object.version_id+1)

    object_json = {
        'action_id': object.action_id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    assert r.headers['Location'] == flask_server.base_url + 'api/v1/objects/{}/versions/{}'.format(object.object_id, object.version_id + 1)
    new_object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert new_object.version_id == object.version_id + 1
    assert new_object.data == object_json['data']
    object = new_object

    object_json = {
        'action_id': object.action_id + 1,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'action_id must be {}'.format(object.action_id)

    new_schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Object Name',
                'type': 'text'
            },
            'info': {
                'title': 'Object Info',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    object_json = {
        'schema': new_schema,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            },
            'info': {
                '_type': 'text',
                'text': 'Example Info'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'].startswith('schema must be either')

    sampledb.logic.actions.update_action(
        action_id=action.id,
        schema=new_schema
    )
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    new_object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert new_object.version_id == object.version_id + 1
    assert new_object.schema == object_json['schema']
    assert new_object.data == object_json['data']
    object = new_object

    object_json = {
        'schema': new_schema,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example Object'
            },
            'info': {
                '_type': 'text',
                'text': 'Example Info 2'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 201
    new_object = sampledb.logic.objects.get_object(object_id=object.object_id)
    assert new_object.version_id == object.version_id + 1
    assert new_object.schema == object_json['schema']
    assert new_object.data == object_json['data']
    object = new_object

    object_json = {
        'data': {
            'name': {
                '_type': 'boolean',
                'value': True
            },
            'info': {
                '_type': 'text',
                'text': 'Example Info 2'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == """validation failed:
 - unexpected keys in schema: {'value'} (at name)"""

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}'.format(object.object_id), auth=auth)
    assert r.status_code == 200
    object_json = r.json()
    # remove keys that must not be copied
    del object_json['user_id']
    del object_json['utc_datetime']
    # update version_id
    object_json['version_id'] += 1
    r = requests.post(flask_server.base_url + 'api/v1/objects/{}/versions/'.format(object.object_id), json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 201


def test_get_objects(flask_server, auth, user, other_user, action):
    r = requests.get(flask_server.base_url + 'api/v1/objects/1', auth=auth)
    assert r.status_code == 404
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=other_user.id)
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == []
    sampledb.logic.object_permissions.set_user_object_permissions(
        object_id=object.object_id,
        user_id=user.id,
        permissions=sampledb.logic.object_permissions.Permissions.READ
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == [
        {
            "object_id": object.object_id,
            "version_id": object.version_id,
            "action_id": object.action_id,
            "schema": object.schema,
            "data": object.data,
            "fed_object_id": object.fed_object_id,
            "fed_version_id": object.fed_version_id,
            "component_id": object.component_id
        }
    ]


def test_get_objects_with_limit_and_offset(flask_server, auth, user, action):
    for i in range(10):
        data = {
            'name': {
                '_type': 'text',
                'text': str(i)
            }
        }
        sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert [
        object["data"]["name"]["text"]
        for object in r.json()
    ] == [
        str(i)
        for i in reversed(range(10))
    ]

    r = requests.get(flask_server.base_url + 'api/v1/objects/', params={"offset": 3}, auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert [
        object["data"]["name"]["text"]
        for object in r.json()
    ] == [
        str(i)
        for i in reversed(range(7))
    ]

    r = requests.get(flask_server.base_url + 'api/v1/objects/', params={"limit": 5}, auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert [
        object["data"]["name"]["text"]
        for object in r.json()
    ] == [
        str(i)
        for i in reversed(range(5,10))
    ]

    r = requests.get(flask_server.base_url + 'api/v1/objects/', params={"limit": 5, "offset": 3}, auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert [
        object["data"]["name"]["text"]
        for object in r.json()
    ] == [
        str(i)
        for i in reversed(range(2,7))
    ]

    r = requests.get(flask_server.base_url + 'api/v1/objects/', params={"offset": -3}, auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert [
        object["data"]["name"]["text"]
        for object in r.json()
    ] == [
        str(i)
        for i in reversed(range(10))
    ]

    r = requests.get(flask_server.base_url + 'api/v1/objects/', params={"limit": -5}, auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert [
        object["data"]["name"]["text"]
        for object in r.json()
    ] == [
        str(i)
        for i in reversed(range(10))
    ]

    r = requests.get(flask_server.base_url + 'api/v1/objects/', params={"limit": 1e20, "offset": 1e20}, auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert [
        object["data"]["name"]["text"]
        for object in r.json()
    ] == [
        str(i)
        for i in reversed(range(10))
    ]


def test_get_objects_with_name_only(flask_server, auth, user):
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Object Name',
                    'type': 'text'
                },
                'other_property': {
                    'title': 'Other Property',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        },
        'other_property': {
            '_type': 'text',
            'text': 'Value'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    r = requests.get(flask_server.base_url + 'api/v1/objects/', params={"name_only": "yes"}, auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == [
        {
            "object_id": object.object_id,
            "version_id": object.version_id,
            "action_id": action.id,
            "schema": {
                'title': 'Object',
                'type': 'object',
                'properties': {
                    'name': {
                        'title': 'Name',
                        'type': 'text'
                    }
                }
            },
            "data": {
                'name': {
                    '_type': 'text',
                    'text': 'Example'
                }
            },
            "fed_object_id": object.fed_object_id,
            "fed_version_id": object.fed_version_id,
            "component_id": object.component_id
        }
    ]


def test_create_object(flask_server, auth, user, action):
    object_json = {
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 201
    objects = sampledb.logic.objects.get_objects()
    assert len(objects) == 1
    object = objects[0]
    assert r.headers['Location'] == flask_server.base_url + 'api/v1/objects/{}/versions/{}'.format(object.object_id, object.version_id)
    assert object.version_id == 0
    assert object.action_id == action.id
    assert object.schema == action.schema
    assert object.data == object_json['data']

    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'].startswith('Failed to decode JSON object')

    r = requests.post(flask_server.base_url + 'api/v1/objects/', json=[], auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'JSON object body required'

    object_json = {
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        },
        'user_id': user.id
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'invalid key \'user_id\''

    object_json = {
        'object_id': 1,
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', json=object_json, auth=auth, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'object_id cannot be set'

    object_json = {
        'version_id': 0,
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 201

    object_json = {
        'version_id': 1,
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'version_id must be 0'

    object_json = {
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'action_id must be set'

    object_json = {
        'action_id': "Create other Sample",
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'action_id must be an integer'

    object_json = {
        'action_id': action.id + 1,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'action {} does not exist'.format(action.id + 1)

    object_json = {
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        },
        'schema': action.schema
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 201

    object_json = {
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        },
        'schema': {
            'name': {
                'type': 'text',
                'default': 'Sample'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'schema must be:\n{}'.format(json.dumps(action.schema, indent=4))

    object_json = {
        'action_id': action.id
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == 'data must be set'

    object_json = {
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'boolean',
                'value': True
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == """validation failed:
 - unexpected keys in schema: {'value'} (at name)"""
    object_json = {
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'boolean',
                'value': True
            },
            'test': {
                '_type': 'text',
                'value': 'Test'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    assert r.json()['message'] == """validation failed:
 - unexpected keys in schema: {'value'} (at name)
 - unknown property "test" (at test)"""


def test_search_objects(flask_server, auth, user, other_user, action):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=other_user.id)
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'q': 'name=="Example"'
    })
    assert r.status_code == 200
    assert r.json() == []
    sampledb.logic.object_permissions.set_user_object_permissions(
        object_id=object.object_id,
        user_id=user.id,
        permissions=sampledb.logic.object_permissions.Permissions.READ
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'q': 'name=="Example"'
    })
    assert r.status_code == 200
    assert r.json() == [
        {
            "object_id": object.object_id,
            "version_id": object.version_id,
            "action_id": object.action_id,
            "schema": object.schema,
            "data": object.data,
            "fed_object_id": object.fed_object_id,
            "fed_version_id": object.fed_version_id,
            "component_id": object.component_id
        }
    ]
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'q': 'name=="Example2"'
    })
    assert r.status_code == 200
    assert r.json() == []
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'q': 'name=="Example'
    })
    assert r.status_code == 400
    assert r.json() == {
        'message': 'Error: Unfinished text'
    }


def test_get_objects_by_action_id(flask_server, auth, user, other_user, action, other_action):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=other_user.id)
    sampledb.logic.object_permissions.set_user_object_permissions(
        object_id=object.object_id,
        user_id=user.id,
        permissions=sampledb.logic.object_permissions.Permissions.READ
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'action_id': str(action.id)
    })
    assert r.status_code == 200
    assert r.json() == [
        {
            "object_id": object.object_id,
            "version_id": object.version_id,
            "action_id": object.action_id,
            "schema": object.schema,
            "data": object.data,
            "fed_object_id": object.fed_object_id,
            "fed_version_id": object.fed_version_id,
            "component_id": object.component_id
        }
    ]
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'action_id': str(other_action.id)
    })
    assert r.status_code == 200
    assert r.json() == []
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'action_id': '-1'
    })
    assert r.status_code == 400


def test_get_objects_by_action_type(flask_server, auth, user, other_user, action, other_action):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=other_user.id)
    sampledb.logic.object_permissions.set_user_object_permissions(
        object_id=object.object_id,
        user_id=user.id,
        permissions=sampledb.logic.object_permissions.Permissions.READ
    )
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'action_type': 'sample'
    })
    assert r.status_code == 200
    assert r.json() == [
        {
            "object_id": object.object_id,
            "version_id": object.version_id,
            "action_id": object.action_id,
            "schema": object.schema,
            "data": object.data,
            "fed_object_id": object.fed_object_id,
            "fed_version_id": object.fed_version_id,
            "component_id": object.component_id
        }
    ]
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'action_type_id': sampledb.models.ActionType.SAMPLE_CREATION
    })
    assert r.status_code == 200
    assert r.json() == [
        {
            "object_id": object.object_id,
            "version_id": object.version_id,
            "action_id": object.action_id,
            "schema": object.schema,
            "data": object.data,
            "fed_object_id": object.fed_object_id,
            "fed_version_id": object.fed_version_id,
            "component_id": object.component_id
        }
    ]
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'action_type': 'measurement'
    })
    assert r.status_code == 200
    assert r.json() == []
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, allow_redirects=False, params={
        'action_type': 'other'
    })
    assert r.status_code == 400


def test_get_related_object_ids(flask_server, auth, user, action, other_action):
    r = requests.get(flask_server.base_url + 'api/v1/objects/0/related_objects', auth=auth, allow_redirects=False)
    assert r.status_code == 404
    sample_data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    sample = sampledb.logic.objects.create_object(action_id=action.id, data=sample_data, user_id=user.id)
    r = requests.get(flask_server.base_url + f'api/v1/objects/{sample.object_id}/related_objects', auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {
        'referenced_objects': [],
        'referencing_objects': []
    }
    measurement_data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        },
        'sample': {
            '_type': 'object_reference',
            'object_id': sample.object_id
        }
    }
    measurement = sampledb.logic.objects.create_object(action_id=other_action.id, data=measurement_data, user_id=user.id)
    r = requests.get(flask_server.base_url + f'api/v1/objects/{sample.object_id}/related_objects', auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {
        'referenced_objects': [],
        'referencing_objects': [
            {
                'object_id': measurement.object_id,
                'component_uuid': None
            }
        ]
    }
    r = requests.get(flask_server.base_url + f'api/v1/objects/{measurement.object_id}/related_objects', auth=auth, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == {
        'referenced_objects': [
            {
                'object_id': sample.object_id,
                'component_uuid': None
            }
        ],
        'referencing_objects': []
    }


def test_get_referencing_objects(flask_server, auth, user, action, other_action):
    sample_data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        },
    }
    sample = sampledb.logic.objects.create_object(action_id=action.id, data=sample_data, user_id=user.id)
    measurement_data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    measurment1 = sampledb.logic.objects.create_object(action_id=other_action.id, data=measurement_data, user_id=user.id)
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, params={'get_referencing_objects': 'True'}, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == [
        {
            "object_id": measurment1.object_id,
            "version_id": measurment1.version_id,
            "action_id": measurment1.action_id,
            "schema": measurment1.schema,
            "data": measurment1.data,
            "fed_object_id": measurment1.fed_object_id,
            "fed_version_id": measurment1.fed_version_id,
            "component_id": measurment1.component_id,
            "referencing_objects": []
        },
        {
            'action_id': sample.action_id,
            'component_id': None,
            'data': sample.data,
            'fed_object_id': sample.fed_object_id,
            'fed_version_id': sample.fed_version_id,
            'object_id': sample.object_id,
            'referencing_objects': [],
            'schema': sample.schema,
            'version_id': sample.version_id
         }
    ]
    measurement_data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        },
        'sample': {
            '_type': 'object_reference',
            'object_id': sample.object_id
        }
    }
    measurment2 = sampledb.logic.objects.create_object(action_id=other_action.id, data=measurement_data, user_id=user.id)
    r = requests.get(flask_server.base_url + 'api/v1/objects/', auth=auth, params={'get_referencing_objects': 'True'}, allow_redirects=False)
    assert r.status_code == 200
    assert r.json() == [
        {
            "object_id": measurment2.object_id,
            "version_id": measurment2.version_id,
            "action_id": measurment2.action_id,
            "schema": measurment2.schema,
            "data": measurment2.data,
            "fed_object_id": measurment2.fed_object_id,
            "fed_version_id": measurment2.fed_version_id,
            "component_id": measurment2.component_id,
            "referencing_objects": []
        },
        {
            "object_id": measurment1.object_id,
            "version_id": measurment1.version_id,
            "action_id": measurment1.action_id,
            "schema": measurment1.schema,
            "data": measurment1.data,
            "fed_object_id": measurment1.fed_object_id,
            "fed_version_id": measurment1.fed_version_id,
            "component_id": measurment1.component_id,
            "referencing_objects": []
        },
        {
            'action_id': sample.action_id,
            'component_id': None,
            'data': sample.data,
            'fed_object_id': sample.fed_object_id,
            'fed_version_id': sample.fed_version_id,
            'object_id': sample.object_id,
            'referencing_objects': [{'object_id': measurment2.object_id}],
            'schema': sample.schema,
            'version_id': sample.version_id
         }

    ]

def test_create_object_with_file_invalid_reference(flask_server, auth, user, action):
    object_json = {
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            },
            'file': {
                '_type': 'file',
                'file_id': 1
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    assert not sampledb.logic.objects.get_objects()


def test_update_object_with_file_reference(flask_server, auth, user, action):
    object_json = {
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            }
        }
    }
    r = requests.post(flask_server.base_url + 'api/v1/objects/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 201
    objects = sampledb.logic.objects.get_objects()
    assert len(objects) == 1
    object = objects[0]
    object_json = {
        'action_id': action.id,
        'data': {
            'name': {
                '_type': 'text',
                'text': 'Example'
            },
            'file': {
                '_type': 'file',
                'file_id': 0
            }
        }
    }
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/versions/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 400
    file = sampledb.logic.files.create_database_file(
        object_id=object.object_id,
        user_id=object.user_id,
        file_name='test.txt',
        save_content=lambda stream: stream.write(b"Test")
    )
    assert file.id == 0
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/versions/', auth=auth, json=object_json, allow_redirects=False)
    assert r.status_code == 201
