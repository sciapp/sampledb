# coding: utf-8
"""

"""

import requests
import pytest
import json

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
def other_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Other User", email="other@fz-juelich.de", type=sampledb.models.UserType.PERSON)
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
        name="",
        description="",
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

@pytest.fixture
def object_id(action, user):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    return object.object_id


def test_get_user_object_permissions(flask_server, auth, user, other_user, object_id):
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "grant"
    r = requests.get(flask_server.base_url + 'api/v1/objects/42/permissions/users/{}'.format(user.id), auth=auth)
    assert r.status_code == 404
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    sampledb.logic.object_permissions.set_user_object_permissions(object_id, other_user.id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"
    sampledb.logic.object_permissions.set_user_object_permissions(object_id, other_user.id, sampledb.models.Permissions.WRITE)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "write"
    sampledb.logic.object_permissions.set_user_object_permissions(object_id, other_user.id, sampledb.models.Permissions.NONE)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"

    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id).id
    sampledb.logic.object_permissions.set_group_object_permissions(object_id, group_id, sampledb.models.Permissions.READ)
    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id
    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.WRITE)

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), params={'include_groups': True}, auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), params={'include_projects': True}, auth=auth)
    assert r.status_code == 200
    assert r.json() == "write"
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, 42), auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "user 42 does not exist"
    }


def test_set_user_object_permissions(flask_server, auth, user, other_user, object_id):
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id, other_user.id, False, False, False) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), json="read", auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id, other_user.id, False, False, False) == sampledb.models.Permissions.READ
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), json="write", auth=auth)
    assert r.status_code == 200
    assert r.json() == "write"
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id, other_user.id, False, False, False) == sampledb.models.Permissions.WRITE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), json="grant", auth=auth)
    assert r.status_code == 200
    assert r.json() == "grant"
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id, other_user.id, False, False, False) == sampledb.models.Permissions.GRANT
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), json="none", auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id, other_user.id, False, False, False) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), json="all", auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "Permissions name required"
    }
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id, other_user.id, False, False, False) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id), json={"permissions": "read"}, auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "JSON string body required"
    }
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id, other_user.id, False, False, False) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, 42), json="read", auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "user 42 does not exist"
    }
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id, other_user.id, False, False, False) == sampledb.models.Permissions.NONE


def test_get_group_object_permissions(flask_server, auth, other_user, object_id):
    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id).id
    
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    r = requests.get(flask_server.base_url + 'api/v1/objects/42/permissions/groups/{}'.format(group_id), auth=auth)
    assert r.status_code == 404
    sampledb.logic.object_permissions.set_group_object_permissions(object_id, group_id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"
    sampledb.logic.object_permissions.set_group_object_permissions(object_id, group_id, sampledb.models.Permissions.WRITE)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "write"
    sampledb.logic.object_permissions.set_group_object_permissions(object_id, group_id, sampledb.models.Permissions.NONE)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"

    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id
    sampledb.logic.projects.add_group_to_project(project_id, group_id, sampledb.models.Permissions.GRANT)
    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.WRITE)

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), params={'include_projects': True}, auth=auth)
    assert r.status_code == 200
    assert r.json() == "write"
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, 42), auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "group 42 does not exist"
    }


def test_set_group_object_permissions(flask_server, auth, other_user, object_id):
    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id).id
    
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id, False).get(group_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), json="read", auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id, False).get(group_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.READ
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), json="write", auth=auth)
    assert r.status_code == 200
    assert r.json() == "write"
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id, False).get(group_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.WRITE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), json="grant", auth=auth)
    assert r.status_code == 200
    assert r.json() == "grant"
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id, False).get(group_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.GRANT
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), json="none", auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id, False).get(group_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), json="all", auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "Permissions name required"
    }
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id, False).get(group_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), json={"permissions": "read"}, auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "JSON string body required"
    }
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id, False).get(group_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, 42), json="read", auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "group 42 does not exist"
    }
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id, False).get(group_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE


def test_get_project_object_permissions(flask_server, auth, other_user, object_id):
    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id
    
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    r = requests.get(flask_server.base_url + 'api/v1/objects/42/permissions/projects/{}'.format(project_id), auth=auth)
    assert r.status_code == 404
    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"
    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.WRITE)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "write"
    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.NONE)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, 42), auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "project 42 does not exist"
    }


def test_set_project_object_permissions(flask_server, auth, other_user, object_id):
    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id
    
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id).get(project_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), json="read", auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id).get(project_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.READ
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), json="write", auth=auth)
    assert r.status_code == 200
    assert r.json() == "write"
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id).get(project_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.WRITE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), json="grant", auth=auth)
    assert r.status_code == 200
    assert r.json() == "grant"
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id).get(project_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.GRANT
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), json="none", auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id).get(project_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), json="all", auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "Permissions name required"
    }
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id).get(project_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), json={"permissions": "read"}, auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "JSON string body required"
    }
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id).get(project_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, 42), json="read", auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "project 42 does not exist"
    }
    assert sampledb.logic.object_permissions.get_object_permissions_for_projects(object_id).get(project_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE


def test_get_users_object_permissions(flask_server, auth, user, other_user, object_id):
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        str(user.id): "grant"
    }
    
    sampledb.logic.object_permissions.set_user_object_permissions(object_id, other_user.id, sampledb.models.Permissions.READ)
    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id).id
    sampledb.logic.object_permissions.set_group_object_permissions(object_id, group_id, sampledb.models.Permissions.WRITE)
    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id
    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.GRANT)

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        str(user.id): "grant",
        str(other_user.id): "read"
    }
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/'.format(object_id), params={"include_groups": True}, auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        str(user.id): "grant",
        str(other_user.id): "write"
    }
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/'.format(object_id), params={"include_projects": True}, auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        str(user.id): "grant",
        str(other_user.id): "grant"
    }


def test_get_groups_object_permissions(flask_server, auth, user, other_user, object_id):
    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id).id

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {}

    sampledb.logic.object_permissions.set_group_object_permissions(object_id, group_id, sampledb.models.Permissions.WRITE)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        str(group_id): "write"
    }

    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id
    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.GRANT)
    sampledb.logic.projects.add_group_to_project(project_id, group_id, sampledb.models.Permissions.GRANT)

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        str(group_id): "write"
    }
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/'.format(object_id), params={"include_projects": True}, auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        str(group_id): "grant"
    }


def test_get_projects_object_permissions(flask_server, auth, user, other_user, object_id):
    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {}

    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.WRITE)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        str(project_id): "write"
    }


def test_get_object_public(flask_server, auth, object_id):
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/public'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() is False

    sampledb.logic.object_permissions.set_object_public(object_id, True)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/public'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() is True


def test_set_object_public(flask_server, auth, object_id):
    assert sampledb.logic.object_permissions.object_is_public(object_id) is False

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/public'.format(object_id), json=True, auth=auth)
    assert r.status_code == 200
    assert r.json() is True
    assert sampledb.logic.object_permissions.object_is_public(object_id) is True

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/public'.format(object_id), json=False, auth=auth)
    assert r.status_code == 200
    assert r.json() is False
    assert sampledb.logic.object_permissions.object_is_public(object_id) is False

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/public'.format(object_id), json="True", auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "JSON boolean body required"
    }
    assert sampledb.logic.object_permissions.object_is_public(object_id) is False
