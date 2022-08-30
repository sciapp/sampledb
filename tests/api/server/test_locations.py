# coding: utf-8
"""

"""

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
                }
            },
            'required': ['name']
        }
    )
    return action


def test_get_location(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/locations/1', auth=auth)
    assert r.status_code == 404

    location = sampledb.logic.locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    r = requests.get(flask_server.base_url + 'api/v1/locations/{}'.format(location.id), auth=auth)
    assert r.status_code == 403

    sampledb.logic.location_permissions.set_location_permissions_for_all_users(location.id, sampledb.logic.location_permissions.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/locations/{}'.format(location.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'location_id': location.id,
        'name': "Example Location",
        'description': "This is an example location",
        'parent_location_id': None,
        'type_id': location.type_id
    }

    parent_location = sampledb.logic.locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    sampledb.logic.locations.update_location(
        location_id=location.id,
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=parent_location.id,
        user_id=user.id,
        type_id=location.type_id
    )
    r = requests.get(flask_server.base_url + 'api/v1/locations/{}'.format(location.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'location_id': location.id,
        'name': "Example Location",
        'description': "This is an example location",
        'parent_location_id': parent_location.id,
        'type_id': location.type_id
    }


def test_get_locations(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/locations/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    location = sampledb.logic.locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    r = requests.get(flask_server.base_url + 'api/v1/locations/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    sampledb.logic.location_permissions.set_location_permissions_for_all_users(location.id, sampledb.logic.location_permissions.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/locations/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'location_id': location.id,
            'name': "Example Location",
            'description': "This is an example location",
            'parent_location_id': None,
            'type_id': location.type_id
        }
    ]


def test_get_location_assignment(flask_server, auth, user, action):
    r = requests.get(flask_server.base_url + 'api/v1/objects/1/locations/', auth=auth)
    assert r.status_code == 404
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/locations/0'.format(object.id), auth=auth)
    assert r.status_code == 404

    location = sampledb.logic.locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    sampledb.logic.locations.assign_location_to_object(object.id, location.id, user.id, user.id, {'en': "This is an example description"})

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/locations/0'.format(object.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'object_id': object.id,
        'location_id': location.id,
        'responsible_user_id': user.id,
        'user_id': user.id,
        'description': "This is an example description",
        'utc_datetime': sampledb.logic.locations.get_object_location_assignments(object.id)[0].utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
    }


def test_get_location_assignments(flask_server, auth, user, action):
    r = requests.get(flask_server.base_url + 'api/v1/objects/1/locations/', auth=auth)
    assert r.status_code == 404
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/locations/'.format(object.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    location = sampledb.logic.locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    sampledb.logic.locations.assign_location_to_object(object.id, location.id, None, user.id, {'en': "This is an example description"})

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/locations/'.format(object.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'object_id': object.id,
            'location_id': location.id,
            'responsible_user_id': None,
            'user_id': user.id,
            'description': "This is an example description",
            'utc_datetime': sampledb.logic.locations.get_object_location_assignments(object.id)[0].utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
        }
    ]
