# coding: utf-8
"""

"""

import requests
import pytest
from bs4 import BeautifulSoup

import sampledb
import sampledb.models
import sampledb.logic
from sampledb.logic.authentication import add_email_authentication


@pytest.fixture
def user_session(flask_server):
    user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(user.id)).status_code == 200
    session.user_id = user.id
    return session


@pytest.fixture
def user(flask_server):
    user = sampledb.models.User(name="Basic User2", email="example2@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    add_email_authentication(user.id, 'example@fz-juelich.de', 'abc.123', True)
    # force attribute refresh
    assert user.id is not None
    # Check if authentication-method add to db
    with flask_server.app.app_context():
        assert len(sampledb.models.Authentication.query.all()) == 1
    return user


def test_list_projects(flask_server, user_session):
    other_user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()

    r = user_session.get(flask_server.base_url + 'projects/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 0

    project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id

    r = user_session.get(flask_server.base_url + 'projects/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 1
    project_url = project_anchors[0]['href']
    assert project_url.endswith('/projects/{}'.format(project_id))


def test_list_user_projects(flask_server, user_session):
    other_user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format(user_session.user_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 0

    other_project_id = sampledb.logic.projects.create_project("Example Project", "", other_user.id).id

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format(user_session.user_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 0

    project_id = sampledb.logic.projects.create_project("Example Project 2", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format(user_session.user_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 1
    project_url = project_anchors[0]['href']
    assert project_url.endswith('/projects/{}'.format(project_id))

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format('unknown'))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    project_anchors = document.find('ul', id='projects_list').find_all('a')
    assert len(project_anchors) == 2
    assert any(project_anchor['href'].endswith('/projects/{}'.format(project_id)) for project_anchor in project_anchors)
    assert any(project_anchor['href'].endswith('/projects/{}'.format(other_project_id)) for project_anchor in project_anchors)

    r = user_session.get(flask_server.base_url + 'projects?user_id={}'.format(user_session.user_id+1))
    assert r.status_code == 403


def test_create_project(flask_server, user_session):
    r = user_session.get(flask_server.base_url + 'projects/')
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    create_project_form = document.find(id='createProjectModal').find('form')
    assert create_project_form is not None

    csrf_token = create_project_form.find('input', {'name': 'csrf_token'})['value']

    r = user_session.post(flask_server.base_url + 'projects/', data={
        'create': 'create',
        'csrf_token': csrf_token,
        'name': 'Example Project',
        'description': 'Example Description'
    }, allow_redirects=False)
    assert r.status_code == 302
    # Force reloading of objects
    sampledb.db.session.rollback()

    projects = sampledb.logic.projects.get_user_projects(user_session.user_id)
    assert len(projects) == 1
    project = projects[0]
    assert project.name == 'Example Project'
    assert project.description == 'Example Description'

    assert r.headers['Location'] == flask_server.base_url + 'projects/{}'.format(project.id)


def test_leave_project(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    leave_project_form = document.find('form', id='leaveProjectForm')
    csrf_token = leave_project_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(project_id), data={
        'leave': 'leave',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    assert len(sampledb.logic.projects.get_user_projects(user_session.user_id)) == 0


def test_edit_project(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    edit_project_form = document.find(id='editProjectModal').find('form')
    csrf_token = edit_project_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(project_id), data={
        'edit': 'edit',
        'csrf_token': csrf_token,
        'name': 'Test Project',
        'description': 'Test Description'
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    project = sampledb.logic.projects.get_project(project_id)
    assert project.name == 'Test Project'
    assert project.description == 'Test Description'


def test_add_user(flask_server, user_session, user):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    new_user = user

    assert len(sampledb.logic.projects.get_user_projects(new_user.id)) == 0

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    url = flask_server.base_url + 'projects/{}'.format(project_id)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    invite_user_form = document.find(id='inviteUserModal').find('form')
    csrf_token = invite_user_form.find('input', {'name': 'csrf_token'})['value']

    #  send invitation
    r = user_session.post(url, {
        'add_user': 'add_user',
        'csrf_token': csrf_token,
        'user_id': str(new_user.id)
    })
    assert r.status_code == 200

    # Check if an invitation notification was sent
    notifications = sampledb.logic.notifications.get_notifications(new_user.id)
    assert len(notifications) > 0
    for notification in notifications:
        if notification.type == sampledb.logic.notifications.NotificationType.INVITED_TO_PROJECT:
            assert notification.data['project_id'] == project_id
            assert notification.data['inviter_id'] == user_session.user_id
            invitation_url = notification.data['confirmation_url']
            break
        else:
            assert False

    assert len(sampledb.logic.projects.get_user_projects(new_user.id)) == 0

    assert invitation_url.startswith(flask_server.base_url + 'projects/1')
    r = user_session.get(invitation_url)
    assert r.status_code == 403
    assert 'Please sign in as user &#34;{}&#34; to accept this invitation'.format(user.name) in r.content.decode('utf-8')

    assert len(sampledb.logic.projects.get_user_projects(new_user.id)) == 0

    session = requests.session()
    assert session.get(flask_server.base_url + 'users/{}/autologin'.format(new_user.id)).status_code == 200
    assert session.get(flask_server.base_url + 'users/me/loginstatus').json() is True

    r = session.get(invitation_url)
    assert r.status_code == 200

    assert len(sampledb.logic.projects.get_user_projects(new_user.id)) == 1
    assert sampledb.logic.projects.get_user_projects(new_user.id)[0].id == project_id


def test_add_group(flask_server, user_session):
    group_id = sampledb.logic.groups.create_group("Example Group", "", user_session.user_id).id

    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    assert len(sampledb.logic.projects.get_group_projects(group_id)) == 0

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    url = flask_server.base_url + 'projects/{}'.format(project_id)
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    invite_user_form = document.find(id='inviteGroupModal').find('form')
    csrf_token = invite_user_form.find('input', {'name': 'csrf_token'})['value']

    r = user_session.post(url, {
        'add_group': 'add_group',
        'csrf_token': csrf_token,
        'group_id': str(group_id)
    })
    assert r.status_code == 200

    assert len(sampledb.logic.projects.get_group_projects(group_id)) == 1
    assert sampledb.logic.projects.get_group_projects(group_id)[0].id == project_id


def test_view_project(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')
    assert document.find('h3').text == 'Project #{}: Example Project'.format(project_id)


def test_remove_last_user_from_project_permissions(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}/permissions'.format(project_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    user_csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'user_permissions-0-csrf_token'})['value']

    form_data = {
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': csrf_token,
        'user_permissions-0-csrf_token': user_csrf_token,
        'user_permissions-0-user_id': str(user_session.user_id),
        'user_permissions-0-permissions': 'none',
    }

    r = user_session.post(flask_server.base_url + 'projects/{}/permissions'.format(project_id), data=form_data)
    assert r.status_code == 200
    assert r.url == flask_server.base_url + 'projects/'
    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.get_project(project_id)


def test_keep_project_permissions(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}/permissions'.format(project_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    user_csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'user_permissions-0-csrf_token'})['value']

    form_data = {
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': csrf_token,
        'user_permissions-0-csrf_token': user_csrf_token,
        'user_permissions-0-user_id': str(user_session.user_id),
        'user_permissions-0-permissions': 'grant',
    }

    r = user_session.post(flask_server.base_url + 'projects/{}/permissions'.format(project_id), data=form_data)
    assert r.status_code == 200
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project_id, user_id=user_session.user_id, include_groups=False) == sampledb.logic.object_permissions.Permissions.GRANT


def test_change_last_user_project_permissions(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}/permissions'.format(project_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    user_csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'user_permissions-0-csrf_token'})['value']

    form_data = {
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': csrf_token,
        'user_permissions-0-csrf_token': user_csrf_token,
        'user_permissions-0-user_id': str(user_session.user_id),
        'user_permissions-0-permissions': 'write',
    }

    r = user_session.post(flask_server.base_url + 'projects/{}/permissions'.format(project_id), data=form_data)
    assert r.status_code == 200
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project_id, user_id=user_session.user_id, include_groups=False) == sampledb.logic.object_permissions.Permissions.GRANT


def test_update_user_project_permissions(flask_server, user_session, user):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    sampledb.logic.projects.add_user_to_project(project_id, user.id, permissions=sampledb.logic.object_permissions.Permissions.READ)

    r = user_session.get(flask_server.base_url + 'projects/{}/permissions'.format(project_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    user_csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'user_permissions-0-csrf_token'})['value']

    form_data = {
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': csrf_token,
        'user_permissions-0-csrf_token': user_csrf_token,
        'user_permissions-0-user_id': str(user.id),
        'user_permissions-0-permissions': 'write',
    }

    r = user_session.post(flask_server.base_url + 'projects/{}/permissions'.format(project_id), data=form_data)
    assert r.status_code == 200
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project_id, user_id=user_session.user_id, include_groups=False) == sampledb.logic.object_permissions.Permissions.GRANT
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project_id, user_id=user.id, include_groups=False) == sampledb.logic.object_permissions.Permissions.WRITE


def test_swap_grant_project_permissions(flask_server, user_session, user):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    sampledb.logic.projects.add_user_to_project(project_id, user.id, permissions=sampledb.logic.object_permissions.Permissions.READ)

    r = user_session.get(flask_server.base_url + 'projects/{}/permissions'.format(project_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    user_csrf_token_0 = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'user_permissions-0-csrf_token'})['value']
    user_csrf_token_1 = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'user_permissions-1-csrf_token'})['value']

    form_data = {
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': csrf_token,
        'user_permissions-0-csrf_token': user_csrf_token_0,
        'user_permissions-0-user_id': str(user_session.user_id),
        'user_permissions-0-permissions': 'write',
        'user_permissions-1-csrf_token': user_csrf_token_1,
        'user_permissions-1-user_id': str(user.id),
        'user_permissions-1-permissions': 'grant'
    }

    r = user_session.post(flask_server.base_url + 'projects/{}/permissions'.format(project_id), data=form_data)
    assert r.status_code == 200
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project_id, user_id=user_session.user_id, include_groups=False) == sampledb.logic.object_permissions.Permissions.WRITE
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project_id, user_id=user.id, include_groups=False) == sampledb.logic.object_permissions.Permissions.GRANT


def test_update_project_permissions_without_grant(flask_server, user_session, user):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    r = user_session.get(flask_server.base_url + 'projects/{}/permissions'.format(project_id))
    assert r.status_code == 200
    assert BeautifulSoup(r.content, 'html.parser').find('form', {'id': 'form-project-permissions'}) is None
    assert BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'user_permissions-0-csrf_token'}) is None

    form_data = {
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': '',
        'user_permissions-0-csrf_token': '',
        'user_permissions-0-user_id': str(user.id),
        'user_permissions-0-permissions': 'write',
    }

    r = user_session.post(flask_server.base_url + 'projects/{}/permissions'.format(project_id), data=form_data)
    assert r.status_code == 403
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project_id, user_id=user.id, include_groups=False) == sampledb.logic.object_permissions.Permissions.GRANT


def test_update_project_permissions_without_project(flask_server, user_session):
    r = user_session.post(flask_server.base_url + 'projects/{}/permissions'.format(10))
    assert r.status_code == 404


def test_update_group_project_permissions(flask_server, user_session, user):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id).id
    sampledb.logic.projects.add_group_to_project(project_id, group_id, permissions=sampledb.logic.object_permissions.Permissions.READ)

    r = user_session.get(flask_server.base_url + 'projects/{}/permissions'.format(project_id))
    assert r.status_code == 200
    csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'csrf_token'})['value']
    group_csrf_token = BeautifulSoup(r.content, 'html.parser').find('input', {'name': 'group_permissions-0-csrf_token'})['value']

    form_data = {
        'edit_user_permissions': 'edit_user_permissions',
        'csrf_token': csrf_token,
        'group_permissions-0-csrf_token': group_csrf_token,
        'group_permissions-0-group_id': str(group_id),
        'group_permissions-0-permissions': 'write',
    }

    r = user_session.post(flask_server.base_url + 'projects/{}/permissions'.format(project_id), data=form_data)
    assert r.status_code == 200
    assert sampledb.logic.projects.get_user_project_permissions(project_id=project_id, user_id=user_session.user_id, include_groups=False) == sampledb.logic.object_permissions.Permissions.GRANT
    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id=project_id) == {
        group_id: sampledb.logic.object_permissions.Permissions.WRITE
    }


def test_add_subproject(flask_server, user_session):
    parent_project_id = sampledb.logic.projects.create_project("Example Project 1", "", user_session.user_id).id
    child_project_id = sampledb.logic.projects.create_project("Example Project 2", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(parent_project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    add_subproject_form = document.find('form', id='addSubprojectForm')
    add_subproject_dropdown = add_subproject_form.find('select')
    assert add_subproject_dropdown.find('option', value=str(child_project_id)) is not None
    csrf_token = add_subproject_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(parent_project_id), data={
        'add_subproject': 'add_subproject',
        'csrf_token': csrf_token,
        add_subproject_dropdown['name']: str(child_project_id)
    })
    assert r.status_code == 200

    assert sampledb.logic.projects.get_child_project_ids(parent_project_id) == [child_project_id]


def test_fail_add_subproject(flask_server, user_session):
    parent_project_id = sampledb.logic.projects.create_project("Example Project 1", "", user_session.user_id).id
    sampledb.logic.projects.create_project("Example Project 2", "", user_session.user_id)

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(parent_project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    add_subproject_form = document.find('form', id='addSubprojectForm')
    add_subproject_dropdown = add_subproject_form.find('select')
    assert add_subproject_dropdown.find('option', value=str(parent_project_id)) is None
    csrf_token = add_subproject_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(parent_project_id), data={
        'add_subproject': 'add_subproject',
        'csrf_token': csrf_token,
        add_subproject_dropdown['name']: str(parent_project_id)
    })
    assert r.status_code == 200
    assert 'Project #{} cannot become a subproject of this project.'.format(int(parent_project_id)) in r.content.decode('utf-8')

    assert sampledb.logic.projects.get_child_project_ids(parent_project_id) == []


def test_remove_subproject(flask_server, user_session):
    parent_project_id = sampledb.logic.projects.create_project("Example Project 1", "", user_session.user_id).id
    child_project_id = sampledb.logic.projects.create_project("Example Project 2", "", user_session.user_id).id
    sampledb.logic.projects.create_subproject_relationship(parent_project_id, child_project_id)

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(parent_project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    add_subproject_form = document.find('form', id='removeSubprojectForm')
    remove_subproject_dropdown = add_subproject_form.find('select')
    assert remove_subproject_dropdown.find('option', value=str(child_project_id)) is not None
    csrf_token = add_subproject_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(parent_project_id), data={
        'remove_subproject': 'remove_subproject',
        'csrf_token': csrf_token,
        remove_subproject_dropdown['name']: str(child_project_id)
    })
    assert r.status_code == 200

    assert sampledb.logic.projects.get_child_project_ids(parent_project_id) == []


def test_fail_remove_subproject(flask_server, user_session):
    parent_project_id = sampledb.logic.projects.create_project("Example Project 1", "", user_session.user_id).id
    child_project_id = sampledb.logic.projects.create_project("Example Project 2", "", user_session.user_id).id
    child_project_id2 = sampledb.logic.projects.create_project("Example Project 3", "", user_session.user_id).id
    sampledb.logic.projects.create_subproject_relationship(parent_project_id, child_project_id2)

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(parent_project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    add_subproject_form = document.find('form', id='removeSubprojectForm')
    remove_subproject_dropdown = add_subproject_form.find('select')
    assert remove_subproject_dropdown.find('option', value=str(child_project_id)) is None
    csrf_token = add_subproject_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(parent_project_id), data={
        'remove_subproject': 'remove_subproject',
        'csrf_token': csrf_token,
        remove_subproject_dropdown['name']: str(child_project_id)
    })
    assert r.status_code == 200
    assert 'Project #{} is not a subproject of this project.'.format(int(child_project_id)) in r.content.decode('utf-8')

    assert sampledb.logic.projects.get_child_project_ids(parent_project_id) == [child_project_id2]


def test_view_subprojects(flask_server, user_session):
    parent_project_id = sampledb.logic.projects.create_project("Example Project 1", "", user_session.user_id).id
    child_project_id1 = sampledb.logic.projects.create_project("Example Project 2", "", user_session.user_id).id
    sampledb.logic.projects.create_project("Example Project 3", "", user_session.user_id)
    sampledb.logic.projects.create_subproject_relationship(parent_project_id, child_project_id1)
    r = user_session.get(flask_server.base_url + 'projects/{}'.format(parent_project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    for header in document.find_all('h4'):
        if 'Subprojects' in header.text:
            subprojects_header = header
            break
    else:
        assert False
    subprojects_list = subprojects_header.find_next_sibling('ul')
    subprojects_items = subprojects_list.find_all('li')
    assert len(subprojects_items) == 1
    assert subprojects_items[0].find('a')['href'].endswith('projects/{}'.format(child_project_id1))


def test_use_project_and_parent_project_invitation_email(flask_server, app, user, user_session):
    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        inviting_user = sampledb.models.User("Inviting User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
        sampledb.db.session.add(inviting_user)
        sampledb.db.session.commit()
        parent_project_id = sampledb.logic.projects.create_project("Parent Project", "", inviting_user.id).id
        project_id = sampledb.logic.projects.create_project("Example Project", "", inviting_user.id).id
        sampledb.logic.projects.create_subproject_relationship(parent_project_id=parent_project_id, child_project_id=project_id, child_can_add_users_to_parent=True)
        project = sampledb.models.projects.Project.query.get(project_id)

        sampledb.logic.projects.invite_user_to_project(project.id, user_session.user_id, inviting_user.id, [parent_project_id])

        # Check if an invitation notification was sent
        notifications = sampledb.logic.notifications.get_notifications(user_session.user_id)
        assert len(notifications) > 0
        for notification in notifications:
            if notification.type == sampledb.logic.notifications.NotificationType.INVITED_TO_PROJECT:
                assert notification.data['project_id'] == project_id
                assert notification.data['inviter_id'] == inviting_user.id
                invitation_url = notification.data['confirmation_url']
                break
            else:
                assert False

    app.config['SERVER_NAME'] = server_name
    invitation_url = invitation_url.replace('http://localhost/', flask_server.base_url)
    r = user_session.get(invitation_url)
    assert r.status_code == 200
    assert user_session.user_id in sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id=project_id)
    assert user_session.user_id in sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id=parent_project_id)


def test_add_user_to_parent_project_already_a_member(user):
    inviting_user = sampledb.models.User("Inviting User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(inviting_user)
    sampledb.db.session.commit()
    parent_project_id = sampledb.logic.projects.create_project("Parent Project", "", inviting_user.id).id
    project_id = sampledb.logic.projects.create_project("Example Project", "", inviting_user.id).id
    sampledb.logic.projects.create_subproject_relationship(parent_project_id=parent_project_id, child_project_id=project_id, child_can_add_users_to_parent=True)
    sampledb.logic.projects.add_user_to_project(parent_project_id, user.id, permissions=sampledb.logic.object_permissions.Permissions.READ)
    assert user.id not in sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id=project_id)
    assert user.id in sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id=parent_project_id)
    sampledb.logic.projects.add_user_to_project(project_id, user.id, permissions=sampledb.logic.object_permissions.Permissions.READ, other_project_ids=[parent_project_id])
    assert user.id in sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id=project_id)
    assert user.id in sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id=parent_project_id)


def test_delete_project(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    delete_project_form = document.find('form', id='deleteProjectForm')
    csrf_token = delete_project_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(project_id), data={
        'delete': 'delete',
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    assert len(sampledb.logic.projects.get_projects()) == 0


def test_remove_member_from_project(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id

    other_user = sampledb.models.User(name="Basic User", email="example@fz-juelich.de", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(other_user)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, other_user.id, sampledb.logic.projects.Permissions.READ)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user_session.user_id: sampledb.logic.projects.Permissions.GRANT,
        other_user.id: sampledb.logic.projects.Permissions.READ
    }

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    remove_member_form = document.find('form', id='removeProjectMember{}Form'.format(other_user.id))
    csrf_token = remove_member_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(project_id), data={
        'remove_member': str(other_user.id),
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {user_session.user_id: sampledb.logic.projects.Permissions.GRANT}


def test_remove_group_from_project(flask_server, user_session):
    project_id = sampledb.logic.projects.create_project("Example Project", "", user_session.user_id).id
    group_id = sampledb.logic.groups.create_group("Example Group", "", user_session.user_id).id

    sampledb.logic.projects.add_group_to_project(project_id, group_id, sampledb.logic.projects.Permissions.READ)

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {group_id: sampledb.logic.projects.Permissions.READ}

    r = user_session.get(flask_server.base_url + 'projects/{}'.format(project_id))
    assert r.status_code == 200
    document = BeautifulSoup(r.content, 'html.parser')

    remove_member_form = document.find('form', id='removeProjectGroup{}Form'.format(group_id))
    csrf_token = remove_member_form.find('input', {'name': 'csrf_token'})['value']
    r = user_session.post(flask_server.base_url + 'projects/{}'.format(project_id), data={
        'remove_group': str(group_id),
        'csrf_token': csrf_token
    })
    assert r.status_code == 200
    # Force reloading of objects
    sampledb.db.session.rollback()

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}
