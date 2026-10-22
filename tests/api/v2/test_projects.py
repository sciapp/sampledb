# coding: utf-8
"""

"""
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


def test_get_project(flask_server, auth, user):
    server_name = flask.current_app.config["SERVER_NAME"]
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.get(flask_server.base_url + 'api/v2/projects/10', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Project group #10 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested project group does not exist.",
        "type": "http://localhost/api/v2/errors/ProjectNotFound"
    }

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    flask.current_app.config["SERVER_NAME"] = server_name
    r = requests.get(flask_server.base_url + f'api/v2/projects/{project.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'project_id': project.id,
        'name': {"en": "Test Project"},
        'description': {},
        "member_users": [
            {
                "user_id": user.id,
                "permissions": "grant",
                "href": flask_server.base_url + f'api/v2/users/{user.id}',
            }
        ],
        "member_groups": []
    }

    group = sampledb.logic.groups.create_group(name='Test Group', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v2/projects/{project.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'project_id': project.id,
        'name': {"en": "Test Project"},
        'description': {},
        "member_users": [
            {
                "user_id": user.id,
                "permissions": "grant",
                "href": flask_server.base_url + f'api/v2/users/{user.id}',
            }
        ],
        "member_groups": []
    }

    sampledb.logic.projects.add_group_to_project(project_id=project.id, group_id=group.id, permissions=sampledb.models.Permissions.READ)

    r = requests.get(flask_server.base_url + f'api/v2/projects/{project.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'project_id': project.id,
        'name': {"en": "Test Project"},
        'description': {},
        "member_users": [
            {
                "user_id": user.id,
                "permissions": "grant",
                "href": flask_server.base_url + f'api/v2/users/{user.id}',
            }
        ],
        "member_groups": [
            {
                "group_id": group.id,
                "permissions": "read",
                "href": flask_server.base_url + f'api/v2/groups/{group.id}',
            }
        ]
    }


def test_get_projects(flask_server, auth, user):
    r = requests.get(flask_server.base_url + f'api/v2/projects/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v2/projects/', auth=auth)
    assert r.status_code == 200
    assert r.json() == [
        {
            'project_id': project.id,
            'name': {"en": "Test Project"},
            'description': {},
            "member_users": [
                {
                    "user_id": user.id,
                    "permissions": "grant",
                    "href": flask_server.base_url + f'api/v2/users/{user.id}',
                }
            ],
            "member_groups": []
        }
    ]


def test_get_project_member_users(flask_server, auth, user):
    server_name = flask.current_app.config["SERVER_NAME"]
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.get(flask_server.base_url + f'api/v2/projects/10/member_users/', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} is no administrator, but only administrators may manage project groups.",
        "errors": [],
        "status": 403,
        "title": "Only administrators may manage project groups.",
        "type": "http://localhost/api/v2/errors/OnlyAdminsMayManageProjects",
    }

    sampledb.logic.users.set_user_administrator(user.id, True)
    r = requests.get(flask_server.base_url + f'api/v2/projects/10/member_users/', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Project group #10 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested project group does not exist.",
        "type": "http://localhost/api/v2/errors/ProjectNotFound",
    }

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    flask.current_app.config["SERVER_NAME"] = server_name
    r = requests.get(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth)
    assert r.json() == [
        {
            'user_id': user.id,
            'permissions': 'grant',
            'href': flask_server.base_url + f'api/v2/users/{user.id}',
        }
    ]

    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.logic.projects.add_user_to_project(project.id, other_user.id, sampledb.models.Permissions.READ)

    r = requests.get(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth)
    assert r.json() == [
        {
            'user_id': user.id,
            'permissions': 'grant',
            'href': flask_server.base_url + f'api/v2/users/{user.id}',
        },
        {
            'user_id': other_user.id,
            'permissions': 'read',
            'href': flask_server.base_url + f'api/v2/users/{other_user.id}',
        }
    ]


def test_post_project_member_user(flask_server, auth, user):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)
    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)

    r = requests.post(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth, json={})
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Field required (permissions)",
        "errors": [
            {
                "detail": "Field required",
                "input": None,
                "json_pointer": "/permissions",
            },
            {
                "detail": "Field required",
                "input": None,
                "json_pointer": "/user_id",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    r = requests.post(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth, json={"user_id": "test", "permissions": "read"})
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Input should be a valid integer, unable to parse string as an integer (user_id)",
        "errors": [
            {
                "detail": "Input should be a valid integer, unable to parse string as an integer",
                "input": "test",
                "json_pointer": "/user_id",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)

    r = requests.post(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth, json={"user_id": other_user.id, "permissions": "invalid"})
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Input should be 'read', 'write' or 'grant' (permissions)",
        "errors": [
            {
                "detail": "Input should be 'read', 'write' or 'grant'",
                "input": "invalid",
                "json_pointer": "/permissions",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }

    r = requests.post(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth, json={"user_id": other_user.id, "permissions": "read"})
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} is no administrator, but only administrators may manage project groups.",
        "errors": [],
        "status": 403,
        "title": "Only administrators may manage project groups.",
        "type": "http://localhost/api/v2/errors/OnlyAdminsMayManageProjects",
    }
    sampledb.logic.users.set_user_administrator(user.id, True)

    sampledb.logic.users.set_user_readonly(user.id, True)
    r = requests.post(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth, json={"user_id": other_user.id, "permissions": "read"})
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"The POST method for this resource is used to make changes, however user #{user.id} is set read-only, and read-only users may not make any changes via the API.",
        "errors": [],
        "status": 403,
        "title": "Read-only users may not make changes via the API.",
        "type": "http://localhost/api/v2/errors/MethodNotAllowedForReadOnlyUsers",
    }
    sampledb.logic.users.set_user_readonly(user.id, False)

    r = requests.post(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth, json={"user_id": other_user.id, "permissions": "read"})
    assert r.status_code == 201
    assert r.headers['Location'].endswith(f'/api/v2/projects/{project.id}/member_users/{other_user.id}')
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=other_user.id) == sampledb.models.Permissions.READ

    r = requests.post(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth, json={"user_id": other_user.id, "permissions": "read"})
    assert r.status_code == 400
    assert r.json() == { 
        "detail": f"User {other_user.id} is already a member of project group #{user.id}.",
        "errors": [],
        "status": 400,
        "title": "The user is already a member of this project group.",
        "type": "http://localhost/api/v2/errors/UserAlreadyIsProjectMember",
    }

    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)
    r = requests.post(flask_server.base_url + f'api/v2/projects/{project.id + 1}/member_users/', auth=auth, json={"user_id": other_user.id, "permissions": "read"})
    assert r.status_code == 404
    assert r.json() == {
        "detail": f"Project group #{project.id + 1} does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested project group does not exist.",
        "type": "http://localhost/api/v2/errors/ProjectNotFound",
    }

    r = requests.post(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/', auth=auth, json={"user_id": other_user.id + 1, "permissions": "read"})
    assert r.status_code == 400
    assert r.json() == {
        "detail": "User should exist (user_id)",
        "errors": [
            {
                "detail": "User should exist",
                "input": other_user.id + 1,
                "json_pointer": "/user_id",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }


def test_get_project_member_user(flask_server, auth, user):
    server_name = flask.current_app.config["SERVER_NAME"]
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.get(flask_server.base_url + f'api/v2/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} is no administrator, but only administrators may manage project groups.",
        "errors": [],
        "status": 403,
        "title": "Only administrators may manage project groups.",
        "type": "http://localhost/api/v2/errors/OnlyAdminsMayManageProjects",
    }

    sampledb.logic.users.set_user_administrator(user.id, True)
    r = requests.get(flask_server.base_url + f'api/v2/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Project group #10 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested project group does not exist.",
        "type": "http://localhost/api/v2/errors/ProjectNotFound",
    }

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{user.id + 1}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": f"User #{user.id + 1} is not a member of project group #{project.id}.",
        "errors": [],
        "status": 404,
        "title": "The user is not a member of this project group.",
        "type": "http://localhost/api/v2/errors/UserIsNoProjectMember",
    }

    flask.current_app.config["SERVER_NAME"] = server_name
    r = requests.get(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{user.id}', auth=auth)
    assert r.json() == {
        'user_id': user.id,
        'permissions': 'grant',
        'href': flask_server.base_url + f'api/v2/users/{user.id}',
    }


def test_put_project_member_user(flask_server, auth, user):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.put(flask_server.base_url + f'api/v2/projects/10/member_users/{user.id}', auth=auth, json={"permissions": "read"})
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} is no administrator, but only administrators may manage project groups.",
        "errors": [],
        "status": 403,
        "title": "Only administrators may manage project groups.",
        "type": "http://localhost/api/v2/errors/OnlyAdminsMayManageProjects",
    }

    sampledb.logic.users.set_user_administrator(user.id, True)
    r = requests.put(flask_server.base_url + f'api/v2/projects/10/member_users/{user.id}', auth=auth, json={"permissions": "read"})
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Project group #10 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested project group does not exist.",
        "type": "http://localhost/api/v2/errors/ProjectNotFound",
    }

    sampledb.logic.users.set_user_readonly(user.id, True)
    r = requests.put(flask_server.base_url + f'api/v2/projects/10/member_users/{user.id}', auth=auth, json={"permissions": "read"})
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"The PUT method for this resource is used to make changes, however user #{user.id} is set read-only, and read-only users may not make any changes via the API.",
        "errors": [],
        "status": 403,
        "title": "Read-only users may not make changes via the API.",
        "type": "http://localhost/api/v2/errors/MethodNotAllowedForReadOnlyUsers",
    }
    sampledb.logic.users.set_user_readonly(user.id, False)

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.put(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{user.id + 1}', auth=auth, json={"permissions": "read"})
    assert r.status_code == 404
    assert r.json() == {
        "detail": f"User #{user.id + 1} is not a member of project group #{project.id}.",
        "errors": [],
        "status": 404,
        "title": "The user is not a member of this project group.",
        "type": "http://localhost/api/v2/errors/UserIsNoProjectMember",
    }

    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.logic.projects.add_user_to_project(project_id=project.id, user_id=other_user.id, permissions=sampledb.models.Permissions.GRANT)

    r = requests.put(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{other_user.id}', auth=auth, json={"permissions": "invalid"})
    assert r.status_code == 400
    assert r.json() == {
        "detail": "Input should be 'read', 'write' or 'grant' (permissions)",
        "errors": [
            {
                "detail": "Input should be 'read', 'write' or 'grant'",
                "input": "invalid",
                "json_pointer": "/permissions",
            },
        ],
        "status": 400,
        "title": "Failed to validate request body data.",
        "type": "http://localhost/api/v2/errors/RequestBodyValidationFailed",
    }
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=other_user.id) == sampledb.models.Permissions.GRANT

    r = requests.put(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{other_user.id}', auth=auth, json={"permissions": "read"})
    assert r.status_code == 200
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=other_user.id) == sampledb.models.Permissions.READ

    # change last user with GRANT
    r = requests.put(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{user.id}', auth=auth, json={"permissions": "read"})
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"User #{user.id} is the only user with GRANT permissions for project group #{project.id}.",
        "errors": [],
        "status": 400,
        "title": "Cannot change the permissions for the only user with GRANT permissions in a project group.",
        "type": "http://localhost/api/v2/errors/CannotChangePermissionsOfOnlyGrantUserInProject",
    }
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=user.id) == sampledb.models.Permissions.GRANT


def test_delete_project_member_user(flask_server, auth, user):
    flask.current_app.config["SERVER_NAME"] = "localhost"
    r = requests.delete(flask_server.base_url + f'api/v2/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"User #{user.id} is no administrator, but only administrators may manage project groups.",
        "errors": [],
        "status": 403,
        "title": "Only administrators may manage project groups.",
        "type": "http://localhost/api/v2/errors/OnlyAdminsMayManageProjects",
    }

    sampledb.logic.users.set_user_administrator(user.id, True)
    r = requests.delete(flask_server.base_url + f'api/v2/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Project group #10 does not exist.",
        "errors": [],
        "status": 404,
        "title": "The requested project group does not exist.",
        "type": "http://localhost/api/v2/errors/ProjectNotFound",
    }

    sampledb.logic.users.set_user_readonly(user.id, True)
    r = requests.delete(flask_server.base_url + f'api/v2/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 403
    assert r.json() == {
        "detail": f"The DELETE method for this resource is used to make changes, however user #{user.id} is set read-only, and read-only users may not make any changes via the API.",
        "errors": [],
        "status": 403,
        "title": "Read-only users may not make changes via the API.",
        "type": "http://localhost/api/v2/errors/MethodNotAllowedForReadOnlyUsers",
    }
    sampledb.logic.users.set_user_readonly(user.id, False)

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.delete(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{user.id + 1}', auth=auth)
    assert r.status_code == 404
    assert r.json() == {
        "detail": f"User #{user.id + 1} is not a member of project group #{project.id}.",
        "errors": [],
        "status": 404,
        "title": "The user is not a member of this project group.",
        "type": "http://localhost/api/v2/errors/UserIsNoProjectMember",
    }

    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.logic.projects.add_user_to_project(project_id=project.id, user_id=other_user.id, permissions=sampledb.models.Permissions.READ)

    r = requests.delete(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{user.id}', auth=auth)
    assert r.status_code == 400
    assert r.json() == {
        "detail": f"User #{user.id} is the only user with GRANT permissions for project group #{project.id} and there are still other members in the project group.",
        "errors": [],
        "status": 400,
        "title": "Cannot remove the only user with GRANT permissions from a project group while there are still other members in the project group.",
        "type": "http://localhost/api/v2/errors/CannotRemoveOnlyGrantUserFromProject",
    }

    r = requests.delete(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{other_user.id}', auth=auth)
    assert r.status_code == 204
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=other_user.id) == sampledb.models.Permissions.NONE

    r = requests.delete(flask_server.base_url + f'api/v2/projects/{project.id}/member_users/{user.id}', auth=auth)
    assert r.status_code == 204
    assert not sampledb.logic.projects.get_projects()