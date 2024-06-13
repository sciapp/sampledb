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

