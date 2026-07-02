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


def test_get_project(flask_server, auth, user):
    r = requests.get(flask_server.base_url + 'api/v1/project/10', auth=auth)
    assert r.status_code == 404

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v1/projects/{project.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'project_id': project.id,
        'name': {"en": "Test Project"},
        'description': {},
        "member_users": [
            {
                "user_id": user.id,
                "permissions": "grant",
                "href": flask_server.base_url + f'api/v1/users/{user.id}',
            }
        ],
        "member_groups": []
    }

    group = sampledb.logic.groups.create_group(name='Test Group', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v1/projects/{project.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'project_id': project.id,
        'name': {"en": "Test Project"},
        'description': {},
        "member_users": [
            {
                "user_id": user.id,
                "permissions": "grant",
                "href": flask_server.base_url + f'api/v1/users/{user.id}',
            }
        ],
        "member_groups": []
    }

    sampledb.logic.projects.add_group_to_project(project_id=project.id, group_id=group.id, permissions=sampledb.models.Permissions.READ)

    r = requests.get(flask_server.base_url + f'api/v1/projects/{project.id}', auth=auth)
    assert r.status_code == 200
    assert r.json() == {
        'project_id': project.id,
        'name': {"en": "Test Project"},
        'description': {},
        "member_users": [
            {
                "user_id": user.id,
                "permissions": "grant",
                "href": flask_server.base_url + f'api/v1/users/{user.id}',
            }
        ],
        "member_groups": [
            {
                "group_id": group.id,
                "permissions": "read",
                "href": flask_server.base_url + f'api/v1/groups/{group.id}',
            }
        ]
    }


def test_get_projects(flask_server, auth, user):
    r = requests.get(flask_server.base_url + f'api/v1/projects/', auth=auth)
    assert r.status_code == 200
    assert r.json() == []

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v1/projects/', auth=auth)
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
                    "href": flask_server.base_url + f'api/v1/users/{user.id}',
                }
            ],
            "member_groups": []
        }
    ]


def test_get_project_member_users(flask_server, auth, user):
    r = requests.get(flask_server.base_url + f'api/v1/projects/10/member_users/', auth=auth)
    assert r.status_code == 403

    sampledb.logic.users.set_user_administrator(user.id, True)
    r = requests.get(flask_server.base_url + f'api/v1/projects/10/member_users/', auth=auth)
    assert r.status_code == 404

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth)
    assert r.json() == [
        {
            'user_id': user.id,
            'permissions': 'grant',
            'href': flask_server.base_url + f'api/v1/users/{user.id}',
        }
    ]

    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.logic.projects.add_user_to_project(project.id, other_user.id, sampledb.models.Permissions.READ)

    r = requests.get(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth)
    assert r.json() == [
        {
            'user_id': user.id,
            'permissions': 'grant',
            'href': flask_server.base_url + f'api/v1/users/{user.id}',
        },
        {
            'user_id': other_user.id,
            'permissions': 'read',
            'href': flask_server.base_url + f'api/v1/users/{other_user.id}',
        }
    ]


def test_post_project_member_user(flask_server, auth, user):
    r = requests.post(flask_server.base_url + f'api/v1/projects/10/member_users/', auth=auth)
    assert r.status_code == 403

    sampledb.logic.users.set_user_administrator(user.id, True)
    r = requests.post(flask_server.base_url + f'api/v1/projects/10/member_users/', auth=auth)
    assert r.status_code == 404

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.post(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth)
    assert r.status_code == 400

    r = requests.post(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth, json={})
    assert r.status_code == 400

    r = requests.post(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth, json={"user_id": "test", "permissions": "read"})
    assert r.status_code == 400

    r = requests.post(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth, json={"user_id": user.id + 1, "permissions": "read"})
    assert r.status_code == 400

    r = requests.post(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth, json={"user_id": user.id, "permissions": "read"})
    assert r.status_code == 400

    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)

    r = requests.post(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth, json={"user_id": other_user.id, "permissions": "invalid"})
    assert r.status_code == 400

    r = requests.post(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth, json={"user_id": other_user.id, "permissions": "read"})
    assert r.status_code == 201
    assert r.headers['Location'].endswith(f'/api/v1/projects/{project.id}/member_users/{other_user.id}')
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=other_user.id) == sampledb.models.Permissions.READ

    sampledb.logic.users.set_user_readonly(user.id, True)
    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)

    r = requests.post(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/', auth=auth, json={"user_id": other_user.id})
    assert r.status_code == 403

def test_get_project_member_user(flask_server, auth, user):
    r = requests.get(flask_server.base_url + f'api/v1/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 403

    sampledb.logic.users.set_user_administrator(user.id, True)
    r = requests.get(flask_server.base_url + f'api/v1/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 404

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.get(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{user.id + 1}', auth=auth)
    assert r.status_code == 404

    r = requests.get(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{user.id}', auth=auth)
    assert r.json() == {
        'user_id': user.id,
        'permissions': 'grant',
        'href': flask_server.base_url + f'api/v1/users/{user.id}',
    }


def test_put_project_member_user(flask_server, auth, user):
    r = requests.put(flask_server.base_url + f'api/v1/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 403

    sampledb.logic.users.set_user_administrator(user.id, True)
    r = requests.put(flask_server.base_url + f'api/v1/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 404

    sampledb.logic.users.set_user_readonly(user.id, True)
    r = requests.put(flask_server.base_url + f'api/v1/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 403
    sampledb.logic.users.set_user_readonly(user.id, False)

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.put(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{user.id + 1}', auth=auth)
    assert r.status_code == 404

    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.logic.projects.add_user_to_project(project_id=project.id, user_id=other_user.id, permissions=sampledb.models.Permissions.GRANT)

    r = requests.put(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{other_user.id}', auth=auth, json={"permissions": "invalid"})
    assert r.status_code == 400
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=other_user.id) == sampledb.models.Permissions.GRANT

    r = requests.put(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{other_user.id}', auth=auth, json={"permissions": "read"})
    assert r.status_code == 200
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=other_user.id) == sampledb.models.Permissions.READ

    # change last user with GRANT
    r = requests.put(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{user.id}', auth=auth, json={"permissions": "read"})
    assert r.status_code == 400
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=user.id) == sampledb.models.Permissions.GRANT


def test_delete_project_member_user(flask_server, auth, user):
    r = requests.delete(flask_server.base_url + f'api/v1/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 403

    sampledb.logic.users.set_user_administrator(user.id, True)
    r = requests.delete(flask_server.base_url + f'api/v1/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 404

    sampledb.logic.users.set_user_readonly(user.id, True)
    r = requests.delete(flask_server.base_url + f'api/v1/projects/10/member_users/{user.id}', auth=auth)
    assert r.status_code == 403
    sampledb.logic.users.set_user_readonly(user.id, False)

    project = sampledb.logic.projects.create_project(name='Test Project', description={}, initial_user_id=user.id)

    r = requests.delete(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{user.id + 1}', auth=auth)
    assert r.status_code == 404

    other_user = sampledb.logic.users.create_user(name="Other User", email="other@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.logic.projects.add_user_to_project(project_id=project.id, user_id=other_user.id, permissions=sampledb.models.Permissions.READ)

    r = requests.delete(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{user.id}', auth=auth)
    assert r.status_code == 400

    r = requests.delete(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{other_user.id}', auth=auth)
    assert r.status_code == 200
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project.id, user_id=other_user.id) == sampledb.models.Permissions.NONE

    r = requests.delete(flask_server.base_url + f'api/v1/projects/{project.id}/member_users/{user.id}', auth=auth)
    assert r.status_code == 200
    assert not sampledb.logic.projects.get_projects()