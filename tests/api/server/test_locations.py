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
    r = requests.get(flask_server.base_url + 'api/v1/locations/{}'.format(location.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'location_id': location.id,
        'name': "Example Location",
        'description': "This is an example location",
        'parent_location_id': parent_location.id,
        'type_id': location.type_id,
        'is_hidden': True,
        'enable_object_assignments': True,
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
            'type_id': location.type_id,
            'is_hidden': False,
            'enable_object_assignments': True,
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

def test_create_location_assignment(flask_server, auth, user, action):
    r = requests.post(flask_server.base_url + 'api/v1/objects/1/locations/', auth=auth, json={
        'location_id': 2,
        'responsible_user_id': user.id,
        'description': 'This is an example description',
    })
    assert r.status_code == 404
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 0

    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
        'description': 'This is an example description',
    })
    assert r.status_code == 400
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 0

    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
        'description': 'This is an example description',
        'location_id': 1
    })
    assert r.status_code == 400
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 0

    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
        'description': 'This is an example description',
        'responsible_user_id': user.id + 1
    })
    assert r.status_code == 400
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 0

    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
        'description': 'This is an example description',
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

    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
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

    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
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

    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
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

    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
        'object_id': object.id + 1,
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 400
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 4

    sampledb.logic.object_permissions.set_user_object_permissions(object.id, user.id, sampledb.models.Permissions.READ)
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 403
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
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 400
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
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 403
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
    r = requests.post(flask_server.base_url + f'api/v1/objects/{object.id}/locations/', auth=auth, json={
        'location_id': location.id,
        'responsible_user_id': user.id,
    })
    assert r.status_code == 400
    assert len(sampledb.logic.locations.get_object_location_assignments(object.id)) == 4


def test_create_location(flask_server, auth, user):
    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth)
    assert r.status_code == 400
    assert len(sampledb.logic.locations.get_locations()) == 0

    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
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

    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
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

    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
        'type_id': location_type.id + 1,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 400
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
    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 403
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
    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 400
    assert len(sampledb.logic.locations.get_locations()) == 2

    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
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
        enable_parent_location=False,
        enable_sub_locations=False,
        enable_object_assignments=True,
        enable_responsible_users=True,
        enable_instruments=True,
        enable_capacities=True,
        show_location_log=False,
    )

    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 400
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

    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 201
    assert len(sampledb.logic.locations.get_locations()) == 4

    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
        'type_id': location_type.id,
        'parent_location_id': parent_location_id + 100
    })
    assert r.status_code == 400
    assert len(sampledb.logic.locations.get_locations()) == 4

    sampledb.logic.location_permissions.set_user_location_permissions(parent_location_id, user.id, sampledb.models.Permissions.READ)
    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 403
    assert len(sampledb.logic.locations.get_locations()) == 4
    sampledb.logic.location_permissions.set_user_location_permissions(parent_location_id, user.id, sampledb.models.Permissions.WRITE)

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
    r = requests.post(flask_server.base_url + 'api/v1/locations/', auth=auth, json={
        'name': 'Example Location',
        'description': 'This is an example action.',
        'type_id': location_type.id,
        'parent_location_id': parent_location_id
    })
    assert r.status_code == 400
    assert len(sampledb.logic.locations.get_locations()) == 4


def test_update_location(flask_server, auth, user):
    r = requests.put(flask_server.base_url + 'api/v1/locations/1', auth=auth)
    assert r.status_code == 404

    location = sampledb.logic.locations.create_location(
        name={'en': 'Example Location'},
        description={'en': 'This is an example location'},
        parent_location_id=None,
        user_id=user.id,
        type_id=sampledb.logic.locations.LocationType.LOCATION
    )

    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth)
    assert r.status_code == 403

    sampledb.logic.location_permissions.set_user_location_permissions(location.id, user.id, sampledb.models.Permissions.WRITE)

    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth)
    assert r.status_code == 400

    location_json = requests.get(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth).json()

    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json=location_json)
    assert r.status_code == 200
    assert r.json() == requests.get(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth).json()
    location = sampledb.logic.locations.get_location(location.id)
    assert location.name == {'en': 'Example Location'}
    assert location.description == {'en': 'This is an example location'}
    assert location.parent_location_id is None
    assert location.type_id == sampledb.logic.locations.LocationType.LOCATION
    assert location.is_hidden == False
    assert location.enable_object_assignments == True

    for key in location_json:
        r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
            k: v
            for k, v in location_json.items()
            if key != k
        })
        if key == 'location_id':
            assert r.status_code == 200
        else:
            assert r.status_code == 400

    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': 'Example Location',
        'description': 'This is an example location',
        'parent_location_id': None,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 200
    assert r.json() == requests.get(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth).json()
    location = sampledb.logic.locations.get_location(location.id)
    assert location.name == {'en': 'Example Location'}
    assert location.description == {'en': 'This is an example location'}
    assert location.parent_location_id is None
    assert location.type_id == sampledb.logic.locations.LocationType.LOCATION
    assert location.is_hidden == False
    assert location.enable_object_assignments == True

    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': 'Example Location 2',
        'description': 'This is an example location 2',
        'parent_location_id': None,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 200
    assert r.json() == requests.get(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth).json()
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

    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': 'Example Location 2',
        'description': 'This is an example location 2',
        'parent_location_id': parent_location.id + 1,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 400

    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': 'Example Location 2',
        'description': 'This is an example location 2',
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 403

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
    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': 'Example Location 2',
        'description': 'This is an example location 2',
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 400

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
    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': 'Example Location 2',
        'description': 'This is an example location 2',
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 400

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
    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': 'Example Location 2',
        'description': 'This is an example location 2',
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 200
    assert r.json() == requests.get(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth).json()
    location = sampledb.logic.locations.get_location(location.id)
    assert location.parent_location_id == parent_location.id

    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
        'location_id': location.id,
        'name': 'Example Location 2',
        'description': 'This is an example location 2',
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION + 1,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 400

    r = requests.put(flask_server.base_url + f'api/v1/locations/{location.id}', auth=auth, json={
        'location_id': location.id + 1,
        'name': 'Example Location 2',
        'description': 'This is an example location 2',
        'parent_location_id': parent_location.id,
        'type_id': sampledb.logic.locations.LocationType.LOCATION,
        'is_hidden': False,
        'enable_object_assignments': True,
    })
    assert r.status_code == 400
