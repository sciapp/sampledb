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
def other_user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        assert user.id is not None
    return user


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
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id + 1, user.id), auth=auth)
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
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id + 1), auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "user {} does not exist".format(other_user.id + 1)
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
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/users/{}'.format(object_id, other_user.id + 1), json="read", auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "user {} does not exist".format(other_user.id + 1)
    }
    assert sampledb.logic.object_permissions.get_user_object_permissions(object_id, other_user.id, False, False, False) == sampledb.models.Permissions.NONE


def test_get_group_object_permissions(flask_server, auth, other_user, object_id):
    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id).id

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id + 1, group_id), auth=auth)
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
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id + 1), auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "group {} does not exist".format(group_id + 1)
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
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/groups/{}'.format(object_id, group_id + 1), json="read", auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "group {} does not exist".format(group_id + 1)
    }
    assert sampledb.logic.object_permissions.get_object_permissions_for_groups(object_id, False).get(group_id, sampledb.models.Permissions.NONE) == sampledb.models.Permissions.NONE


def test_get_project_object_permissions(flask_server, auth, other_user, object_id):
    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id + 1, project_id), auth=auth)
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

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id + 1), auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "project {} does not exist".format(project_id + 1)
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
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/projects/{}'.format(object_id, project_id + 1), json="read", auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "message": "project {} does not exist".format(project_id + 1)
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

    sampledb.logic.object_permissions.set_object_permissions_for_all_users(object_id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/public'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() is True


def test_set_object_public(flask_server, auth, object_id):
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id)

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/public'.format(object_id), json=True, auth=auth)
    assert r.status_code == 200
    assert r.json() is True
    assert sampledb.models.Permissions.READ in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id)

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/public'.format(object_id), json=False, auth=auth)
    assert r.status_code == 200
    assert r.json() is False
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id)

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/public'.format(object_id), json="True", auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "JSON boolean body required"
    }
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id)


def test_get_all_user_object_permissions(flask_server, auth, object_id):
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/authenticated_users'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"

    sampledb.logic.object_permissions.set_object_permissions_for_all_users(object_id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/authenticated_users'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"


def test_set_all_user_object_permissions(flask_server, auth, object_id):
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id)

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/authenticated_users'.format(object_id), json="read", auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"
    assert sampledb.models.Permissions.READ in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id)

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/authenticated_users'.format(object_id), json="none", auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id)

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/authenticated_users'.format(object_id), json=True, auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "JSON string body required"
    }
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_all_users(object_id)


def test_get_anonymous_user_object_permissions(flask_server, auth, object_id):
    flask_server.app.config['ENABLE_ANONYMOUS_USERS'] = True

    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/anonymous_users'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"

    sampledb.logic.object_permissions.set_object_permissions_for_anonymous_users(object_id, sampledb.models.Permissions.READ)
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/anonymous_users'.format(object_id), auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"

    flask_server.app.config['ENABLE_ANONYMOUS_USERS'] = False
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/anonymous_users'.format(object_id), auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "anonymous users are disabled"
    }


def test_set_anonymous_user_object_permissions(flask_server, auth, object_id):
    flask_server.app.config['ENABLE_ANONYMOUS_USERS'] = True
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_anonymous_users(object_id)

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/anonymous_users'.format(object_id), json="read", auth=auth)
    assert r.status_code == 200
    assert r.json() == "read"
    assert sampledb.models.Permissions.READ in sampledb.logic.object_permissions.get_object_permissions_for_anonymous_users(object_id)

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/anonymous_users'.format(object_id), json="none", auth=auth)
    assert r.status_code == 200
    assert r.json() == "none"
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_anonymous_users(object_id)

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/anonymous_users'.format(object_id), json=True, auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "JSON string body required"
    }
    assert sampledb.models.Permissions.READ not in sampledb.logic.object_permissions.get_object_permissions_for_anonymous_users(object_id)

    flask_server.app.config['ENABLE_ANONYMOUS_USERS'] = False
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions/anonymous_users'.format(object_id), auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "anonymous users are disabled"
    }


def test_get_all_object_permissions(flask_server, auth, user, other_user, object_id):
    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id).id
    sampledb.logic.object_permissions.set_group_object_permissions(object_id, group_id, sampledb.models.Permissions.WRITE)
    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id
    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.GRANT)
    sampledb.logic.projects.add_group_to_project(project_id, group_id, sampledb.models.Permissions.GRANT)
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=object_id, user_id=user.id, permissions=sampledb.models.Permissions.READ)
    sampledb.logic.object_permissions.set_user_object_permissions(object_id=object_id, user_id=other_user.id, permissions=sampledb.models.Permissions.READ)

    r_all = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(object_id), auth=auth)
    r_users = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/users'.format(object_id), auth=auth)
    r_groups = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/groups'.format(object_id), auth=auth)
    r_projects = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/projects'.format(object_id), auth=auth)
    r_authenticated = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/authenticated_users'.format(object_id), auth=auth)
    r_anonymous = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions/anonymous_users'.format(object_id), auth=auth)

    assert r_all.status_code == 200
    assert r_all.json()["users"] == r_users.json()
    assert r_all.json()["groups"] == r_groups.json()
    assert r_all.json()["projects"] == r_projects.json()
    assert r_all.json()["authenticated_users"] == r_authenticated.json()
    assert r_all.json()["anonymous_users"] == (r_anonymous.json() if r_anonymous.ok else 'none')

    r_all = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(object_id+1), auth=auth)
    assert r_all.status_code == 404


def test_set_object_permissions(flask_server, auth, user, other_user, object_id):
    # Apply perms for 2 out of 3 (users, groups, projects)
    # Stick with the first permission;
    # Remove (change) perm for second;
    # Add perm for third (user, group, project)
    sampledb.logic.object_permissions.set_user_object_permissions(
        object_id,
        user.id,
        sampledb.models.Permissions.GRANT
    )
    sampledb.logic.object_permissions.set_user_object_permissions(
        object_id,
        other_user.id,
        sampledb.models.Permissions.GRANT
    )
    with flask_server.app.app_context():
        third_user = sampledb.models.User(name="Third User", email="third_user@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(third_user)
        sampledb.db.session.commit()
        assert third_user.id is not None
    group_ids = [sampledb.logic.groups.create_group(f"Example Group{i}", "", other_user.id).id for i in range(3)]
    [
        sampledb.logic.object_permissions.set_group_object_permissions(
            object_id,
            group_id,
            sampledb.models.Permissions.WRITE,
        )
        for group_id in group_ids
    ]
    project_ids = [sampledb.logic.projects.create_project(f"Example Project{i}", "", other_user.id).id for i in range(3)]
    [
        sampledb.logic.object_permissions.set_project_object_permissions(
            object_id,
            project_id,
            sampledb.models.Permissions.GRANT,
        )
        for project_id in project_ids
    ]

    sampledb.logic.object_permissions.set_object_permissions_for_all_users(object_id,sampledb.models.Permissions.READ)
    flask_server.app.config['ENABLE_ANONYMOUS_USERS'] = True
    sampledb.logic.object_permissions.set_object_permissions_for_anonymous_users(object_id,sampledb.models.Permissions.READ)
    request_json = {
        "users": {
            other_user.id: "none",
            third_user.id: "read",
        },
        "groups": {
            group_ids[1]: 'none',
            group_ids[2]: 'read',
        },
        "projects": {
            project_ids[1]: 'none',
            project_ids[2]: 'read',
        },
    }
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(object_id), json=request_json, auth=auth)
    assert r.status_code == 200

    assert all([
        r.json()["users"][str(user.id)] == 'grant',
        r.json()["users"].get(str(other_user.id)) == None,
        r.json()["users"][str(third_user.id)] == "read"
    ])
    assert all([
        r.json()["groups"][str(group_ids[0])] == 'write',
        r.json()["groups"].get(str(group_ids[1])) == None,
        r.json()["groups"][str(group_ids[2])] == 'read',
    ])
    assert all([
        r.json()["projects"][str(project_ids[0])] == 'grant',
        r.json()["projects"].get(str(project_ids[1])) == None,
        r.json()["projects"][str(project_ids[2])] == 'read',
    ])
    assert r.json()["authenticated_users"] == 'read'
    assert r.json()["anonymous_users"] == 'read'

    request_json = {
        'authenticated_users': 'none',
        'anonymous_users': 'none',
    }
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(object_id), json=request_json, auth=auth)
    assert r.status_code == 200
    assert r.json()["authenticated_users"] == 'none'
    assert r.json()["anonymous_users"] == 'none'

    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(object_id+1), json=request_json, auth=auth)
    assert r.status_code == 404

    flask_server.app.config['ENABLE_ANONYMOUS_USERS'] = False
    request_json = {
        'anonymous_users': 'read',
    }
    r = requests.put(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(object_id), json=request_json, auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "message": "anonymous users are disabled"
    }


def test_copy_object_permissions(flask_server, auth, user, other_user, object_id, action):
    data = {
        'name': {
            '_type': 'text',
            'text': 'Example'
        }
    }
    sampledb.logic.object_permissions.set_user_object_permissions(object_id, other_user.id, sampledb.models.Permissions.GRANT)
    group_id = sampledb.logic.groups.create_group("Example Group", "", other_user.id).id
    sampledb.logic.object_permissions.set_group_object_permissions(object_id, group_id, sampledb.models.Permissions.WRITE)
    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id
    sampledb.logic.object_permissions.set_project_object_permissions(object_id, project_id, sampledb.models.Permissions.WRITE)
    other_object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    other_object_id = other_object.object_id
    request_json = {
        "source_object_id": object_id,
        "target_object_id": other_object_id,
    }
    r = requests.post(flask_server.base_url + '/api/v1/objects/permissions/copy/', json=request_json, auth=auth)
    assert r.status_code == 200
    r = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(other_object_id), json=request_json, auth=auth)
    assert r.status_code == 200
    perms_source_object = sampledb.api.server.object_permissions.all_object_permissions_dict_to_json(sampledb.logic.object_permissions.get_all_object_permissions(object_id))
    perms_source_object["users"] = {str(k): v for k,v in perms_source_object["users"].items()} if perms_source_object.get("users") else None
    perms_source_object["groups"] = {str(k): v for k,v in perms_source_object["groups"].items()} if perms_source_object.get("groups") else None
    perms_source_object["projects"] = {str(k): v for k,v in perms_source_object["projects"].items()} if perms_source_object.get("projects") else None

    for key in perms_source_object.keys():
        assert r.json()[key] == perms_source_object[key]

    # Multiple copy requests at once
    b_object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    b_object_id = b_object.object_id
    c_object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    c_object_id = c_object.object_id

    # Make sure c_object and b_object do not have the same permissions as object
    perms_source = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(object_id), json=request_json, auth=auth).json()
    perms_b_obj = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(b_object_id), json=request_json, auth=auth).json()
    perms_c_obj = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(c_object_id), json=request_json, auth=auth).json()
    assert not all([perms_source.get(key, None) == perms_b_obj.get(key, None) for key in perms_source.keys()]) # Fails if object and b_object have same permissions
    assert not all([perms_source.get(key, None) == perms_c_obj.get(key, None) for key in perms_source.keys()]) # Failes if object and c_object have same permissions

    request_json = [
        {
        "source_object_id": object_id,
        "target_object_id": b_object_id,
        },
        {
        "source_object_id": object_id,
        "target_object_id": c_object_id,
        },
    ]
    r = requests.post(flask_server.base_url + '/api/v1/objects/permissions/copy/', json=request_json, auth=auth)
    assert r.status_code == 200
    perms_source = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(object_id), json=request_json, auth=auth).json()
    perms_b_obj = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(b_object_id), json=request_json, auth=auth).json()
    perms_c_obj = requests.get(flask_server.base_url + 'api/v1/objects/{}/permissions'.format(c_object_id), json=request_json, auth=auth).json()
    for key in perms_source.keys():
        assert perms_source[key] == perms_b_obj[key]
        assert perms_source[key] == perms_c_obj[key]

    request_json = {
        "source_object_id": object_id,
        "target_object_id": other_object_id,
    }

    # Not enough permission to view source object's permissions
    sampledb.logic.object_permissions.set_user_object_permissions(object_id, user.id, sampledb.models.Permissions.NONE)
    r = requests.post(flask_server.base_url + '/api/v1/objects/permissions/copy/', json=request_json, auth=auth)
    assert r.status_code == 403

    # Not enough permissions to perform a grant action on target object
    sampledb.logic.object_permissions.set_user_object_permissions(object_id, user.id, sampledb.models.Permissions.READ)
    sampledb.logic.object_permissions.set_user_object_permissions(other_object_id, user.id, sampledb.models.Permissions.READ)
    r = requests.post(flask_server.base_url + '/api/v1/objects/permissions/copy/', json=request_json, auth=auth)
    assert r.status_code == 403

    # Not existing object
    last_object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    last_object_id = last_object.object_id
    request_json = {
        "source_object_id": object_id,
        "target_object_id": last_object_id+1,
    }
    r = requests.post(flask_server.base_url + '/api/v1/objects/permissions/copy/', json=request_json, auth=auth)
    assert r.status_code == 404
