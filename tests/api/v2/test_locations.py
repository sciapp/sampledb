# coding: utf-8
"""

"""
import base64
from urllib.parse import urlencode

import flask
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
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.get(flask_server.base_url + 'api/v2/locations/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Location #1 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested location does not exist.",
        "type": "http://localhost/api/v2/errors/LocationNotFound"
    }

    location = sampledb.logic.locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    r = requests.get(flask_server.base_url + 'api/v2/locations/{}'.format(location.id), auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} does not have sufficient permissions for location #{location.id}.",
        "errors": [],
        "status": 403,
        "title": "The user does not have sufficient permissions for the location.",
        "type": "http://localhost/api/v2/errors/InsufficientLocationPermissions"
    }

    sampledb.logic.location_permissions.set_location_permissions_for_all_users(location.id, sampledb.logic.location_permissions.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v2/locations/{}'.format(location.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'location_id': location.id,
        'name': location.name,
        'description': location.description,
        'parent_location_id': None,
        'type_id': location.type_id,
        'is_hidden': False,
        'enable_object_assignments': True,
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
        type_id=location.type_id,
        is_hidden=True,
        enable_object_assignments=True,
    )
    location = sampledb.logic.locations.get_location(location.id)
    r = requests.get(flask_server.base_url + 'api/v2/locations/{}'.format(location.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'location_id': location.id,
        'name': location.name,
        'description': location.description,
        'parent_location_id': parent_location.id,
        'type_id': location.type_id,
        'is_hidden': True,
        'enable_object_assignments': True,
    }


def test_get_locations(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v2/locations/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    location = sampledb.logic.locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    r = requests.get(flask_server.base_url + 'api/v2/locations/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    sampledb.logic.location_permissions.set_location_permissions_for_all_users(location.id, sampledb.logic.location_permissions.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v2/locations/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'location_id': location.id,
            'name': location.name,
            'description': location.description,
            'parent_location_id': None,
            'type_id': location.type_id,
            'is_hidden': False,
            'enable_object_assignments': True,
        }
    ]


def test_get_locations_pagination(flask_server, auth, user):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.get(flask_server.base_url + 'api/v2/locations/?&limit=10', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    locations = [
        sampledb.logic.locations.create_location(
            name={'en': f"Example Location {i}"},
            description={'en': "This is an example location"},
            parent_location_id=None,
            user_id=user.id,
            type_id=sampledb.logic.locations.LocationType.LOCATION
        )
        for i in range(30)
    ]
    for location in locations:
        sampledb.logic.location_permissions.set_location_permissions_for_all_users(location.id, sampledb.logic.location_permissions.Permissions.READ)

    r = requests.get(flask_server.base_url + 'api/v2/locations/?limit=10', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'location_id': location.id,
            'name': location.name,
            'description': location.description,
            'parent_location_id': None,
            'type_id': location.type_id,
            'is_hidden': False,
            'enable_object_assignments': True,
        }
        for location in locations[:10]
    ]
    assert r.headers['Link'] == ', '.join(
        [
            '<http://localhost/api/v2/locations/?limit=10>; rel="start"',
            '<http://localhost/api/v2/locations/?limit=10>; rel="self"',
            f'<http://localhost/api/v2/locations/?' + urlencode({"limit": 10, "cursor": base64.urlsafe_b64encode(str(locations[9].id).encode('utf8')).decode('utf8')}) + '>; rel="next"',
        ]
    )
    r = requests.get(flask_server.base_url + 'api/v2/locations/?' + urlencode({"limit": 5, "cursor": base64.urlsafe_b64encode(str(locations[9].id).encode('utf8')).decode('utf8')}), auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'location_id': location.id,
            'name': location.name,
            'description': location.description,
            'parent_location_id': None,
            'type_id': location.type_id,
            'is_hidden': False,
            'enable_object_assignments': True,
        }
        for location in locations[10:15]
    ]
    assert r.headers['Link'] == ', '.join(
        [
            '<http://localhost/api/v2/locations/?limit=5>; rel="start"',
            f'<http://localhost/api/v2/locations/?' + urlencode({"limit": 5, "cursor": base64.urlsafe_b64encode(str(locations[9].id).encode('utf8')).decode('utf8')}) + '>; rel="self"',
            f'<http://localhost/api/v2/locations/?' + urlencode({"limit": 5, "cursor": base64.urlsafe_b64encode(str(locations[14].id).encode('utf8')).decode('utf8')}) + '>; rel="next"',
        ]
    )
    r = requests.get(flask_server.base_url + 'api/v2/locations/?' + urlencode({"limit": 5, "cursor": base64.urlsafe_b64encode(str(locations[-4].id).encode('utf8')).decode('utf8')}), auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'location_id': location.id,
            'name': location.name,
            'description': location.description,
            'parent_location_id': None,
            'type_id': location.type_id,
            'is_hidden': False,
            'enable_object_assignments': True,
        }
        for location in locations[-3:]
    ]
    assert r.headers['Link'] == ', '.join(
        [
            '<http://localhost/api/v2/locations/?limit=5>; rel="start"',
            f'<http://localhost/api/v2/locations/?' + urlencode({"limit": 5, "cursor": base64.urlsafe_b64encode(str(locations[-4].id).encode('utf8')).decode('utf8')}) + '>; rel="self"',
        ]
    )
    for location in locations[::2]:
        sampledb.logic.location_permissions.set_location_permissions_for_all_users(location.id, sampledb.logic.location_permissions.Permissions.NONE)
    r = requests.get(flask_server.base_url + 'api/v2/locations/?limit=10', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'location_id': location.id,
            'name': location.name,
            'description': location.description,
            'parent_location_id': None,
            'type_id': location.type_id,
            'is_hidden': False,
            'enable_object_assignments': True,
        }
        for location in locations[1::2][:10]
    ]


def test_get_location_assignment(flask_server, auth, user, action):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.get(flask_server.base_url + 'api/v2/objects/1/locations/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Object #1 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested object does not exist.",
        "type": "http://localhost/api/v2/errors/ObjectNotFound"
    }

    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    r = requests.get(flask_server.base_url + 'api/v2/objects/{}/locations/0'.format(object.id), auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": f"Location assignment #0 for object #{object.id} does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested object location assignment does not exist.",
        "type": "http://localhost/api/v2/errors/ObjectLocationAssignmentNotFound"
    }

    location = sampledb.logic.locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    sampledb.logic.locations.assign_location_to_object(object.id, location.id, user.id, user.id, {'en': "This is an example description"})

    r = requests.get(flask_server.base_url + 'api/v2/objects/{}/locations/0'.format(object.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'object_location_assignment_id': sampledb.logic.locations.get_object_location_assignments(object.id)[0].id,
        'object_id': object.id,
        'location_id': location.id,
        'responsible_user_id': user.id,
        'user_id': user.id,
        'description': {"en": "This is an example description"},
        'utc_datetime': sampledb.logic.locations.get_object_location_assignments(object.id)[0].utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
    }


def test_get_location_assignments(flask_server, auth, user, action):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.get(flask_server.base_url + 'api/v2/objects/1/locations/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Object #1 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested object does not exist.",
        "type": "http://localhost/api/v2/errors/ObjectNotFound"
    }

    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    r = requests.get(flask_server.base_url + 'api/v2/objects/{}/locations/'.format(object.id), auth=auth)
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

    r = requests.get(flask_server.base_url + 'api/v2/objects/{}/locations/'.format(object.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'object_location_assignment_id': sampledb.logic.locations.get_object_location_assignments(object.id)[0].id,
            'object_id': object.id,
            'location_id': location.id,
            'responsible_user_id': None,
            'user_id': user.id,
            'description': {"en": "This is an example description"},
            'utc_datetime': sampledb.logic.locations.get_object_location_assignments(object.id)[0].utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
        }
    ]


def test_create_location_assignment(flask_server, auth, user, action):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.post(flask_server.base_url + 'api/v2/objects/1/locations/', auth=auth, json={
        'location_id': 2,
        'responsible_user_id': user.id,
        'description': {'en': 'This is an example description'},
    })
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Object #1 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested object does not exist.",
        "type": "http://localhost/api/v2/errors/ObjectNotFound",
    }

    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 0

    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'description': {'en': 'This is an example description'},
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Object assignment should include a location or a responsible user",
        "errors": [
            {
                "detail": "Object assignment should include a location or a responsible user",
                "input": {
                    "description": {"en": "This is an example description"},
                },
                "json_pointer": "/",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 0

    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'description': {'en': 'This is an example description'},
        'location_id': 1
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Location should exist (location_id)",
        "errors": [
            {
                "detail": "Location should exist (location_id)",
                "input": {
                    "description": {"en": "This is an example description"},
                    "location_id": 1,
                },
                "json_pointer": "/",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 0

    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'description': {'en': 'This is an example description'},
        'responsible_user_id': user.id + 1
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": "User should exist (responsible_user_id)",
        "errors": [
            {
                "detail": "User should exist",
                "input":  user.id + 1,
                "json_pointer": "/responsible_user_id",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 0

    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'description': {'en': 'This is an example description'},
        'responsible_user_id': user.id,
    })
    assert r.status_code == 201
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 1
    object_location_assignment = sampledb.logic.locations.get_object_location_assignments(object.id)[-1]
    assert object_location_assignment.object_id == object.id
    assert object_location_assignment.description == {'en': 'This is an example description'}
    assert object_location_assignment.location_id is None
    assert object_location_assignment.responsible_user_id == user.id
    assert object_location_assignment.user_id == user.id

    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'responsible_user_id': user.id,
    })
    assert r.status_code == 201
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 2
    object_location_assignment = sampledb.logic.locations.get_object_location_assignments(object.id)[-1]
    assert object_location_assignment.object_id == object.id
    assert object_location_assignment.description == {}
    assert object_location_assignment.location_id is None
    assert object_location_assignment.responsible_user_id == user.id
    assert object_location_assignment.user_id == user.id

    location = sampledb.logic.locations.create_location(
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    sampledb.logic.location_permissions.set_user_location_permissions(location.id, user.id, sampledb.models.Permissions.READ)

    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id
    })
    assert r.status_code == 201
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 3
    object_location_assignment = sampledb.logic.locations.get_object_location_assignments(object.id)[-1]
    assert object_location_assignment.object_id == object.id
    assert object_location_assignment.description == {}
    assert object_location_assignment.location_id == location.id
    assert object_location_assignment.responsible_user_id is None
    assert object_location_assignment.user_id == user.id

    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 201
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 4
    object_location_assignment = sampledb.logic.locations.get_object_location_assignments(object.id)[-1]
    assert object_location_assignment.object_id == object.id
    assert object_location_assignment.description == {}
    assert object_location_assignment.location_id == location.id
    assert object_location_assignment.responsible_user_id == user.id
    assert object_location_assignment.user_id == user.id

    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'object_id': object.id + 1,
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"Input should be {object.id} (object_id)",
        "errors": [
            {
                "detail": f"Input should be {object.id}",
                "input": object.id + 1,
                "json_pointer": "/object_id",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 4

    sampledb.logic.object_permissions.set_user_object_permissions(object.id, user.id, sampledb.models.Permissions.READ)
    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} does not have sufficient permissions for object #{object.id}.",
        "errors": [],
        "status": 403,
        "title": "The user does not have sufficient permissions for the object.",
        "type": "http://localhost/api/v2/errors/InsufficientObjectPermissions",}
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 4
    sampledb.logic.object_permissions.set_user_object_permissions(object.id, user.id, sampledb.models.Permissions.GRANT)

    sampledb.logic.locations.update_location(
        location.id,
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION,
        is_hidden=False,
        enable_object_assignments=False
    )
    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"Location #{location.id} does not allow object assignments.",
        "errors": [],
        "status": 400,
        "title": "The location does not allow object assignments.",
        "type": "http://localhost/api/v2/errors/LocationDoesNotAllowObjectAssignments",
    }
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 4
    sampledb.logic.locations.update_location(
        location.id,
        name={'en': "Example Location"},
        description={'en': "This is an example location"},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION,
        is_hidden=False,
        enable_object_assignments=True
    )

    sampledb.logic.location_permissions.set_user_location_permissions(location.id, user.id, sampledb.models.Permissions.NONE)
    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} does not have sufficient permissions for location #{location.id}.",
        "errors": [],
        "status": 403,
        "title": "The user does not have sufficient permissions for the location.",
        "type": "http://localhost/api/v2/errors/InsufficientLocationPermissions",
    }
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 4
    sampledb.logic.location_permissions.set_user_location_permissions(location.id, user.id, sampledb.models.Permissions.READ)

    sampledb.logic.locations.update_location_type(
        location_type_id=location.type.id,
        name=location.type.name,
        location_name_singular=location.type.location_name_singular,
        location_name_plural=location.type.location_name_plural,
        admin_only=location.type.admin_only,
        enable_parent_location=location.type.enable_parent_location,
        enable_sub_locations=location.type.enable_sub_locations,
        enable_object_assignments=location.type.enable_object_assignments,
        enable_responsible_users=location.type.enable_responsible_users,
        enable_instruments=location.type.enable_instruments,
        enable_capacities=True,
        show_location_log=location.type.show_location_log,
    )
    r = requests.post(flask_server.base_url + f'api/v2/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 400
    assert r.json() == { 
        "detail": f"Location #{location.id} has reached its maximum capacity for objects of this type. Object #{object.id} could not be assigned to it as that would exceed the maximum capacity.",
        "errors": [],
        "status": 400,
        "title": "The location has reached its maximum capacity for object assignments and the assigning an additional object would exceed that capacity.",
        "type": "http://localhost/api/v2/errors/LocationCapacityReached",
    }
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 4


def test_create_location(flask_server, auth, user):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Input should be an object",
        "errors": [
            {
                "detail": "Input should be an object",
                "input": None,
                "json_pointer": "/",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
    assert len(sampledb.logic.locations.get_locations()) == 0

    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json={
        "name": {"en": "Example Location"},
    })
    assert r.status_code == 201
    assert len(sampledb.logic.locations.get_locations()) == 1
    location = sampledb.logic.locations.get_locations()[-1]
    assert location.name == {'en': 'Example Location'}
    assert location.description == {}
    assert location.parent_location_id is None
    assert location.type_id == sampledb.logic.locations.LocationType.LOCATION

    parent_location_id = location.id
    sampledb.logic.location_permissions.set_user_location_permissions(parent_location_id, user.id, sampledb.models.Permissions.GRANT)

    location_type = sampledb.logic.locations.create_location_type(
        name={'en': 'Container'},
        location_name_singular={'en': 'Container'},
        location_name_plural={'en': 'Containers'},
        admin_only=False,
        enable_parent_location=True,
        enable_sub_locations=False,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=True,
        show_location_log=False,
    )

    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json={
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example action."},
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 201
    assert len(sampledb.logic.locations.get_locations()) == 2
    location = sampledb.logic.locations.get_locations()[-1]
    assert location.name == {'en': 'Example Location'}
    assert location.description == {'en': 'This is an example action.'}
    assert location.parent_location_id == parent_location_id
    assert location.type_id == location_type.id

    data = {
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example action."},
        'type_id': location_type.id + 1,
        'parent_location_id': parent_location_id
    }
    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json=data)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Location type should exist (type_id)",
        "errors": [
            {
                "detail": "Location type should exist (type_id)",
                "input": data,
                "json_pointer": "/",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
    assert len(sampledb.logic.locations.get_locations()) == 2

    sampledb.logic.locations.update_location_type(
        location_type_id=location_type.id,
        name={'en': 'Container'},
        location_name_singular={'en': 'Container'},
        location_name_plural={'en': 'Containers'},
        admin_only=True,
        enable_parent_location=True,
        enable_sub_locations=False,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=True,
        show_location_log=False,
    )
    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json={
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example action."},
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} is no administrator, but only administrators may use location type #{location_type.id}.",
        "errors": [],
        "status": 403,
        "title": "Only administrators may use the location type.",
        "type": "http://localhost/api/v2/errors/OnlyAdminsMayUseLocationType",
    }
    assert len(sampledb.logic.locations.get_locations()) == 2

    sampledb.logic.locations.update_location_type(
        location_type_id=location_type.id,
        name={'en': 'Container'},
        location_name_singular={'en': 'Container'},
        location_name_plural={'en': 'Containers'},
        admin_only=False,
        enable_parent_location=False,
        enable_sub_locations=False,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=True,
        show_location_log=False,
    )
    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json={
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example action."},
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"Location type #{location_type.id} does not allow having a parent location.",
        "errors": [],
        "status": 400,
        "title": "The location type does not allow parent locations.",
        "type": "http://localhost/api/v2/errors/LocationTypeDoesNotAllowParentLocations",
    }
    assert len(sampledb.logic.locations.get_locations()) == 2

    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json={
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example action."},
        'type_id': location_type.id,
        'parent_location_id': None
    })
    assert r.status_code == 201
    assert len(sampledb.logic.locations.get_locations()) == 3
    location = sampledb.logic.locations.get_locations()[-1]
    assert location.name == {'en': 'Example Location'}
    assert location.description == {'en': 'This is an example action.'}
    assert location.parent_location_id is None
    assert location.type_id == location_type.id
    sampledb.logic.locations.update_location_type(
        location_type_id=location_type.id,
        name={'en': 'Container'},
        location_name_singular={'en': 'Container'},
        location_name_plural={'en': 'Containers'},
        admin_only=False,
        enable_parent_location=True,
        enable_sub_locations=False,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=True,
        show_location_log=False,
    )

    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json={
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example action."},
        'type_id': location_type.id,
        'parent_location_id': location.id
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"Parent location type #{location_type.id} does not allow having sub locations.",
        "errors": [],
        "status": 400,
        "title": "The location type does not allow sub locations.",
        "type": "http://localhost/api/v2/errors/LocationTypeDoesNotAllowSubLocations",
    }
    assert len(sampledb.logic.locations.get_locations()) == 3

    sampledb.logic.locations.update_location_type(
        location_type_id=location_type.id,
        name={'en': 'Container'},
        location_name_singular={'en': 'Container'},
        location_name_plural={'en': 'Containers'},
        admin_only=False,
        enable_parent_location=True,
        enable_sub_locations=False,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=True,
        show_location_log=False,
    )

    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json={
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example action."},
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 201
    assert len(sampledb.logic.locations.get_locations()) == 4

    data = {
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example action."},
        'type_id': location_type.id,
        'parent_location_id': parent_location_id + 100
    }
    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json=data)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Location should exist (parent_location_id)",
        "errors": [
            {
                "detail": "Location should exist (parent_location_id)",
                "input": data,
                "json_pointer": "/",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
    assert len(sampledb.logic.locations.get_locations()) == 4

    sampledb.logic.location_permissions.set_user_location_permissions(parent_location_id, user.id, sampledb.models.Permissions.READ)
    r = requests.post(flask_server.base_url + 'api/v2/locations/', auth=auth, json={
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example action."},
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} does not have sufficient permissions for parent location #{parent_location_id}.",
        "errors": [],
        "status": 403,
        "title": "The user does not have sufficient permissions for the location.",
        "type": "http://localhost/api/v2/errors/InsufficientLocationPermissions",
    }
    assert len(sampledb.logic.locations.get_locations()) == 4


def test_update_location(flask_server, auth, user):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.put(flask_server.base_url + 'api/v2/locations/1', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Location #1 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested location does not exist.",
        "type": "http://localhost/api/v2/errors/LocationNotFound",
    }

    location = sampledb.logic.locations.create_location(
        name={'en': 'Example Location'},
        description={'en': 'This is an example location'},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )
    sampledb.logic.location_permissions.set_user_location_permissions(location.id, user.id, sampledb.models.Permissions.READ)

    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth)
    assert r.status_code == 400
    assert r.json() == { 
        "detail": "Input should be an object",
        "errors": [
            {
                "detail": "Input should be an object",
                "input": None,
                "json_pointer": "/",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    location_json = requests.get(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth).json()
    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json=location_json)
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} does not have sufficient permissions for location #{location.id}.",
        "errors": [],
        "status": 403,
        "title": "The user does not have sufficient permissions for the location.",
        "type": "http://localhost/api/v2/errors/InsufficientLocationPermissions"
    }

    sampledb.logic.location_permissions.set_user_location_permissions(location.id, user.id, sampledb.models.Permissions.WRITE)
    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json=location_json)
    assert r.status_code == 200
    assert r.json() == requests.get(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth).json()
    location = sampledb.logic.locations.get_location(location.id)
    assert location.name == {'en': 'Example Location'}
    assert location.description == {'en': 'This is an example location'}
    assert location.parent_location_id is None
    assert location.type_id == sampledb.logic.locations.LocationType.LOCATION
    assert location.is_hidden == False
    assert location.enable_object_assignments == True

    for key in location_json:
        r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json={
            k: v
            for k, v in location_json.items()
            if key != k
        })
        if key == 'location_id':
            assert r.status_code == 200
        else:
            assert r.status_code == 400
            assert r.json() == { 
                "detail": f"Field required ({key})",
                "errors": [
                    {
                        "detail": "Field required",
                        "input": None,
                        "json_pointer": f"/{key}",
                    },
                ],
                "status": 400,
                "title": "Failed to validate request body data.",
                "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed"
            }

    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': {"en": "Example Location"},
        'description': {"en": "This is an example location"},
        'parent_location_id': None,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 200
    assert r.json() == requests.get(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth).json()
    location = sampledb.logic.locations.get_location(location.id)
    assert location.name == {'en': 'Example Location'}
    assert location.description == {'en': 'This is an example location'}
    assert location.parent_location_id is None
    assert location.type_id == sampledb.logic.locations.LocationType.LOCATION
    assert location.is_hidden == False
    assert location.enable_object_assignments == True

    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': {"en": "Example Location 2"},
        'description': {"en": "This is an example location 2"},
        'parent_location_id': None,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 200
    assert r.json() == requests.get(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth).json()
    location = sampledb.logic.locations.get_location(location.id)
    assert location.name == {'en': 'Example Location 2'}
    assert location.description == {'en': 'This is an example location 2'}

    parent_location = sampledb.logic.locations.create_location(
        name={'en': 'Example Location'},
        description={'en': 'This is an example location'},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )

    data = {
        'location_id': location.id,
        'name': {"en": "Example Location 2"},
        'description': {"en": "This is an example location 2"},
        'parent_location_id': parent_location.id + 1,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    }
    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json=data)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Location should exist (parent_location_id)",
        "errors": [
            {
                "detail": "Location should exist (parent_location_id)",
                "input": data,
                "json_pointer": "/",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': {"en": "Example Location 2"},
        'description': {"en": "This is an example location 2"},
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 403
    assert r.json() == {  
        "detail": f"User #{user.id} does not have sufficient permissions for parent location #{parent_location.id}.",
        "errors": [],
        "status": 403,
        "title": "The user does not have sufficient permissions for the location.",
        "type": "http://localhost/api/v2/errors/InsufficientLocationPermissions",
    }

    sampledb.logic.location_permissions.set_user_location_permissions(parent_location.id, user.id, sampledb.models.Permissions.WRITE)
    sampledb.logic.locations.update_location_type(
        location_type_id=sampledb.logic.locations.LocationType.LOCATION,
        name={'en': 'Location'},
        location_name_singular={'en': 'Location'},
        location_name_plural={'en': 'Locations'},
        admin_only=False,
        enable_parent_location=True,
        enable_sub_locations=False,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=True,
        show_location_log=False,
    )
    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': {"en": "Example Location 2"},
        'description': {"en": "This is an example location 2"},
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"Parent location type #{sampledb.logic.locations.LocationType.LOCATION} does not allow having sub locations.",
        "errors": [],
        "status": 400,
        "title": "The location type does not allow sub locations.",
        "type": "http://localhost/api/v2/errors/LocationTypeDoesNotAllowSubLocations",
    }

    sampledb.logic.locations.update_location_type(
        location_type_id=sampledb.logic.locations.LocationType.LOCATION,
        name={'en': 'Location'},
        location_name_singular={'en': 'Location'},
        location_name_plural={'en': 'Locations'},
        admin_only=False,
        enable_parent_location=False,
        enable_sub_locations=True,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=True,
        show_location_log=False,
    )
    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': {"en": "Example Location 2"},
        'description': {"en": "This is an example location 2"},
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"Location type #{sampledb.logic.locations.LocationType.LOCATION} does not allow having a parent location.",
        "errors": [],
        "status": 400,
        "title": "The location type does not allow parent locations.",
        "type": "http://localhost/api/v2/errors/LocationTypeDoesNotAllowParentLocations",
    }

    sampledb.logic.locations.update_location_type(
        location_type_id=sampledb.logic.locations.LocationType.LOCATION,
        name={'en': 'Location'},
        location_name_singular={'en': 'Location'},
        location_name_plural={'en': 'Locations'},
        admin_only=False,
        enable_parent_location=True,
        enable_sub_locations=True,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=True,
        show_location_log=False,
    )
    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': {"en": "Example Location 2"},
        'description': {"en": "This is an example location 2"},
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 200
    assert r.json() == requests.get(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth).json()
    location = sampledb.logic.locations.get_location(location.id)
    assert location.parent_location_id == parent_location.id

    data = {
        'location_id': location.id,
        'name': {"en": "Example Location 2"},
        'description': {"en": "This is an example location 2"},
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION + 1,
        'is_hidden': False,
        'enable_object_assignments': True,
    }
    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json=data)
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Location type should exist (type_id)",
        "errors": [
            {
                "detail": "Location type should exist (type_id)",
                "input": data,
                "json_pointer": "/",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    r = requests.put(flask_server.base_url + f'api/v2/locations/{location.id}', auth=auth, json={
        'location_id': location.id + 1,
        'name': {"en": "Example Location 2"},
        'description': {"en": "This is an example location 2"},
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"Input should be {location.id} (location_id)",
        "errors": [
            {
                "detail": f"Input should be {location.id}",
                "input": location.id + 1,
                "json_pointer": "/location_id",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
