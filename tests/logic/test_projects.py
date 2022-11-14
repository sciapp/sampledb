# coding: utf-8
"""

"""

import pytest
import requests

import sampledb
import sampledb.logic
import sampledb.models


def test_create_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.projects.Project.query.all()) == 0

    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert len(sampledb.models.projects.Project.query.all()) == 1
    project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()
    assert project is not None
    assert project.id == project_id
    assert project.name == {'en': "Example Project"}
    assert project.description == {}


def test_create_project_with_user_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.projects.Project.query.all()) == 0

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.create_project("Example Project", "", user.id + 1)

    assert len(sampledb.models.projects.Project.query.all()) == 0


def test_create_duplicate_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Example Project", "", user.id)
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.ProjectAlreadyExistsError):
        sampledb.logic.projects.create_project("Example Project", "", user.id)

    assert len(sampledb.models.projects.Project.query.all()) == 1


def test_create_project_with_empty_name():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.projects.Project.query.all()) == 0

    with pytest.raises(sampledb.logic.errors.InvalidProjectNameError):
        sampledb.logic.projects.create_project("", "", user.id)

    assert len(sampledb.models.projects.Project.query.all()) == 0


def test_create_project_with_long_name():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.projects.Project.query.all()) == 0

    with pytest.raises(sampledb.logic.errors.InvalidProjectNameError):
        sampledb.logic.projects.create_project("A" * 101, "", user.id)

    assert len(sampledb.models.projects.Project.query.all()) == 0

    project_id = sampledb.logic.projects.create_project("A" * 100, "", user.id).id

    assert len(sampledb.models.projects.Project.query.all()) == 1
    project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()
    assert project is not None
    assert project.id == project_id
    assert project.name == {'en': "A" * 100}
    assert project.description == {}


def test_get_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    project = sampledb.logic.projects.get_project(project_id)

    assert project.id == project_id
    assert project.name == {'en': "Example Project"}
    assert project.description == {}


def test_get_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.get_project(project_id + 1)


def test_get_projects():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    projects = sampledb.logic.projects.get_projects()
    assert len(projects) == 0

    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    projects = sampledb.logic.projects.get_projects()
    assert len(projects) == 1
    project = projects[0]
    assert project.id == project_id
    assert project.name == {'en': "Example Project"}
    assert project.description == {}

    sampledb.logic.projects.delete_project(project_id)
    projects = sampledb.logic.projects.get_projects()
    assert len(projects) == 0

    sampledb.logic.projects.create_project("Example Project 1", "", user.id)
    sampledb.logic.projects.create_project("Example Project 2", "", user.id)
    projects = sampledb.logic.projects.get_projects()
    assert len(projects) == 2
    assert {projects[0].name['en'], projects[1].name['en']} == {"Example Project 1", "Example Project 2"}


def test_update_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    sampledb.logic.projects.update_project(project_id, {'en': "Test Project"}, {'en': "Test Description"})

    project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()
    assert project is not None
    assert project.id == project_id
    assert project.name == {'en': "Test Project"}
    assert project.description == {'en': "Test Description"}


def test_update_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.update_project(project_id + 1, {'en': "Test Project"}, {'en': "Test Description"})

    project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()
    assert project is not None
    assert project.id == project_id
    assert project.name == {'en': "Example Project"}
    assert project.description == {}


def test_update_project_with_existing_name():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Example Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project 2", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 2

    with pytest.raises(sampledb.logic.errors.ProjectAlreadyExistsError):
        sampledb.logic.projects.update_project(project_id, {'en': "Example Project"}, {})

    project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()
    assert project is not None
    assert project.id == project_id
    assert project.name == {'en': "Example Project 2"}
    assert project.description == {}


def test_update_project_with_empty_name():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.InvalidProjectNameError):
        sampledb.logic.projects.update_project(project_id, {'en': ""}, {'en': "Test Description"})
    with pytest.raises(sampledb.logic.errors.MissingEnglishTranslationError):
        sampledb.logic.projects.update_project(project_id, {}, {'en': "Test Description"})

    project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()
    assert project is not None
    assert project.id == project_id
    assert project.name == {'en': "Example Project"}
    assert project.description == {}


def test_update_project_with_long_name():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.InvalidProjectNameError):
        sampledb.logic.projects.update_project(project_id, {'en': "A" * 101}, {})

    project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()
    assert project is not None
    assert project.id == project_id
    assert project.name == {'en': "Example Project"}
    assert project.description == {}

    sampledb.logic.projects.update_project(project_id, {'en': "A" * 100}, {})

    project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()
    assert project is not None
    assert project.id == project_id
    assert project.name == {'en': "A" * 100}
    assert project.description == {}


def test_delete_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "Test Description", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 2
    assert len(sampledb.models.projects.UserProjectPermissions.query.all()) == 2

    sampledb.logic.projects.delete_project(project_id)

    assert len(sampledb.models.projects.Project.query.all()) == 1
    assert len(sampledb.models.projects.UserProjectPermissions.query.all()) == 1
    project = sampledb.models.projects.Project.query.first()
    assert project is not None
    assert project.id != project_id
    assert project.name == {'en': "Test Project"}
    assert project.description == {'en': "Test Description"}


def test_delete_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Test Project", "Test Description", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.delete_project(project_id + 1)

    assert len(sampledb.models.projects.Project.query.all()) == 1
    project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()
    assert project is not None
    assert project.id == project_id
    assert project.name == {'en': "Test Project"}
    assert project.description == {'en': "Test Description"}


def test_add_user_to_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    project_creator = user
    user_permissions = sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id)
    assert len(user_permissions) == 1
    assert user_permissions[project_creator.id] == sampledb.models.Permissions.GRANT

    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user.id, permissions=sampledb.models.Permissions.WRITE)

    user_permissions = sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id)
    assert len(user_permissions) == 2
    assert user_permissions[project_creator.id] == sampledb.models.Permissions.GRANT
    assert user_permissions[user.id] == sampledb.models.Permissions.WRITE


def test_add_user_to_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.add_user_to_project(project_id + 1, user.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_add_user_that_does_not_exist_to_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.add_user_to_project(project_id, user.id + 1, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_add_user_that_is_already_a_member_to_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.UserAlreadyMemberOfProjectError):
        sampledb.logic.projects.add_user_to_project(project_id, user.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_add_user_to_project_without_permissions():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user2.id, permissions=sampledb.models.Permissions.NONE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_invite_user_to_project_does_not_exist():

    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.invite_user_to_project(project_id + 1, user.id, user.id)


def test_invite_user_to_project_user_does_not_exist():

    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.invite_user_to_project(project_id, user.id + 1, user.id)


def test_invite_user_that_is_already_a_member_to_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    with pytest.raises(sampledb.logic.errors.UserAlreadyMemberOfProjectError):
        sampledb.logic.projects.invite_user_to_project(project_id, user.id, user.id)


def test_invite_user_to_project(flask_server, app):
    server_name = app.config['SERVER_NAME']
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        user = sampledb.models.User("Inviting User", "example@example.com", sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
        project = sampledb.models.projects.Project.query.filter_by(id=project_id).first()

        other_user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
        sampledb.db.session.add(other_user)
        sampledb.db.session.commit()

        assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id=project.id) == {
            user.id: sampledb.logic.projects.Permissions.GRANT
        }

        permissions = sampledb.logic.projects.Permissions.WRITE
        sampledb.logic.projects.invite_user_to_project(project_id, other_user.id, user.id, permissions=permissions)

        notifications = sampledb.logic.notifications.get_notifications(other_user.id)
        assert len(notifications) > 0
        for notification in notifications:
            if notification.type == sampledb.logic.notifications.NotificationType.INVITED_TO_PROJECT:
                assert notification.data['project_id'] == project_id
                assert notification.data['inviter_id'] == user.id
                invitation_url = notification.data['confirmation_url']
                break
        else:
            assert False

        app.config['SERVER_NAME'] = server_name
        session = requests.session()
        assert session.get(flask_server.base_url + 'users/{}/autologin'.format(other_user.id)).status_code == 200
        invitation_url = invitation_url.replace('http://localhost/', flask_server.base_url)
        r = session.get(invitation_url)
        assert r.status_code == 200
        assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id=project.id)[other_user.id] == permissions


def test_remove_user_from_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user2.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.WRITE
    }

    sampledb.logic.projects.remove_user_from_project(project_id, user2.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_remove_last_grant_user_from_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user2.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.WRITE
    }

    with pytest.raises(sampledb.logic.errors.NoMemberWithGrantPermissionsForProjectError):
        sampledb.logic.projects.remove_user_from_project(project_id, user.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.WRITE
    }


def test_remove_last_user_from_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    sampledb.logic.projects.remove_user_from_project(project_id, user.id)

    assert len(sampledb.models.projects.Project.query.all()) == 0


def test_remove_user_from_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.remove_user_from_project(project_id + 1, user.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_remove_user_that_does_not_exist_from_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.remove_user_from_project(project_id, user.id + 1)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_remove_user_that_is_not_a_member_from_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.UserNotMemberOfProjectError):
        sampledb.logic.projects.remove_user_from_project(project_id, user2.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_get_user_projects():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    projects = sampledb.logic.projects.get_user_projects(user.id)

    assert len(projects) == 0

    sampledb.logic.projects.add_user_to_project(project_id, user.id, sampledb.models.Permissions.WRITE)
    sampledb.db.session.commit()

    projects = sampledb.logic.projects.get_user_projects(user.id)

    assert len(projects) == 1
    project = projects[0]
    assert project.id == project_id
    assert project.name == {'en': "Example Project"}
    assert project.description == {}


def test_get_user_projects_for_user_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.get_user_projects(user.id + 1)


def test_get_user_project_permissions():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.GRANT

    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.NONE

    sampledb.logic.projects.add_user_to_project(project_id, user.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.WRITE


def test_get_user_project_permissions_including_groups():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user.id, sampledb.models.Permissions.READ)

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.READ

    group = sampledb.logic.groups.create_group("Example Group", "", user.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.READ
    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id, include_groups=True) == sampledb.models.Permissions.WRITE


def test_get_project_member_ids_for_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    sampledb.models.projects.Project.query.filter_by(id=project_id).first()

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id + 1)

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id + 1)


def test_add_group_to_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }


def test_add_group_to_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.add_group_to_project(project_id + 1, group.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}


def test_add_group_that_does_not_exist_to_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    with pytest.raises(sampledb.logic.errors.GroupDoesNotExistError):
        sampledb.logic.projects.add_group_to_project(project_id, group.id + 1, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}


def test_add_group_that_is_already_a_member_to_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }

    with pytest.raises(sampledb.logic.errors.GroupAlreadyMemberOfProjectError):
        sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }


def test_add_group_to_project_without_permissions():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}

    sampledb.logic.projects.add_group_to_project(project_id, group.id, permissions=sampledb.models.Permissions.NONE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}


def test_remove_group_from_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }

    sampledb.logic.projects.remove_group_from_project(project_id, group.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}


def test_remove_last_user_from_project_with_member_group():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }

    with pytest.raises(sampledb.logic.errors.NoMemberWithGrantPermissionsForProjectError):
        sampledb.logic.projects.remove_user_from_project(project_id, user.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }


def test_remove_last_group_from_project_with_member_user():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }

    sampledb.logic.projects.remove_group_from_project(project_id, group.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}


def test_remove_group_from_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.remove_group_from_project(project_id + 1, group.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }


def test_remove_group_that_does_not_exist_from_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }

    with pytest.raises(sampledb.logic.errors.GroupDoesNotExistError):
        sampledb.logic.projects.remove_group_from_project(project_id, group.id + 1)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }


def test_remove_group_that_is_not_a_member_from_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)
    group2 = sampledb.logic.groups.create_group("Example Group 2", "", user2.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }

    with pytest.raises(sampledb.logic.errors.GroupNotMemberOfProjectError):
        sampledb.logic.projects.remove_group_from_project(project_id, group2.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }


def test_update_user_project_permissions():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user2.id, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.GRANT
    }

    sampledb.logic.projects.update_user_project_permissions(project_id, user.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.WRITE,
        user2.id: sampledb.models.Permissions.GRANT
    }


def test_update_user_project_permissions_to_none():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user2.id, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.GRANT
    }

    sampledb.logic.projects.update_user_project_permissions(project_id, user.id, permissions=sampledb.models.Permissions.NONE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user2.id: sampledb.models.Permissions.GRANT
    }


def test_update_last_grant_user_project_permissions():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user2.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.WRITE
    }

    sampledb.logic.projects.update_user_project_permissions(project_id, user.id, permissions=sampledb.models.Permissions.GRANT)

    with pytest.raises(sampledb.logic.errors.NoMemberWithGrantPermissionsForProjectError):
        sampledb.logic.projects.update_user_project_permissions(project_id, user.id, permissions=sampledb.models.Permissions.READ)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.WRITE
    }


def test_update_user_project_permissions_for_user_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.update_user_project_permissions(project_id, user.id + 1, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_update_user_project_permissions_for_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.update_user_project_permissions(project_id + 1, user.id, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_update_user_project_permissions_for_user_that_is_no_member_of_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.UserNotMemberOfProjectError):
        sampledb.logic.projects.update_user_project_permissions(project_id, user2.id, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_update_group_project_permissions():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)
    sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.READ)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.READ
    }

    sampledb.logic.projects.update_group_project_permissions(project_id, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }


def test_update_group_project_permissions_to_none():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)
    sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.READ)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.READ
    }

    sampledb.logic.projects.update_group_project_permissions(project_id, group.id, permissions=sampledb.models.Permissions.NONE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}


def test_update_group_project_permissions_for_user_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)
    sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.READ)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.READ
    }

    with pytest.raises(sampledb.logic.errors.GroupDoesNotExistError):
        sampledb.logic.projects.update_group_project_permissions(project_id, group.id + 1, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.READ
    }


def test_update_group_project_permissions_for_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)
    sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.READ)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.READ
    }

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.update_group_project_permissions(project_id + 1, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.READ
    }


def test_update_group_project_permissions_for_user_that_is_no_member_of_project():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}

    with pytest.raises(sampledb.logic.errors.GroupNotMemberOfProjectError):
        sampledb.logic.projects.update_group_project_permissions(project_id, group.id, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}


def test_get_group_projects():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    projects = sampledb.logic.projects.get_group_projects(group.id)

    assert len(projects) == 0

    sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.WRITE)
    sampledb.db.session.commit()

    projects = sampledb.logic.projects.get_group_projects(group.id)

    assert len(projects) == 1
    project = projects[0]
    assert project.id == project_id
    assert project.name == {'en': "Example Project"}
    assert project.description == {}


def test_get_group_projects_for_group_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user.id)

    with pytest.raises(sampledb.logic.errors.GroupDoesNotExistError):
        sampledb.logic.projects.get_group_projects(group.id + 1)


def test_get_project_member_user_ids_including_groups():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id, include_groups=True) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id, include_groups=True) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.WRITE
    }

    sampledb.logic.groups.add_user_to_group(group.id, user.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id, include_groups=True) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.WRITE
    }


def test_get_user_projects_including_groups():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    projects = sampledb.logic.projects.get_user_projects(user.id)

    assert len(projects) == 0

    group = sampledb.logic.groups.create_group("Example Group", "", user.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.WRITE)
    sampledb.db.session.commit()

    projects = sampledb.logic.projects.get_user_projects(user.id)

    assert len(projects) == 0

    projects = sampledb.logic.projects.get_user_projects(user.id, include_groups=True)

    assert len(projects) == 1
    project = projects[0]
    assert project.id == project_id
    assert project.name == {'en': "Example Project"}
    assert project.description == {}


def test_filter_child_project_candidates():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id1 = sampledb.logic.projects.create_project("Test Project 1", "", user.id).id
    project_id2 = sampledb.logic.projects.create_project("Test Project 2", "", user.id).id
    project_id3 = sampledb.logic.projects.create_project("Test Project 3", "", user.id).id
    project_id4 = sampledb.logic.projects.create_project("Test Project 4", "", user.id).id
    assert sampledb.logic.projects.filter_child_project_candidates(project_id1, [
        project_id2, project_id3
    ]) == [
        project_id2, project_id3
    ]
    sampledb.logic.projects.create_subproject_relationship(project_id1, project_id2)
    assert sampledb.logic.projects.filter_child_project_candidates(project_id1, [
        project_id2, project_id3
    ]) == [
        project_id3
    ]
    sampledb.logic.projects.create_subproject_relationship(project_id3, project_id4)
    assert sampledb.logic.projects.filter_child_project_candidates(project_id1, [
        project_id3, project_id4
    ]) == [
        project_id3, project_id4
    ]
    sampledb.logic.projects.create_subproject_relationship(project_id4, project_id1)
    assert sampledb.logic.projects.filter_child_project_candidates(project_id1, [
        project_id3, project_id4
    ]) == []


def test_existing_subproject_relationships():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id1 = sampledb.logic.projects.create_project("Test Project 1", "", user.id).id
    project_id2 = sampledb.logic.projects.create_project("Test Project 2", "", user.id).id
    sampledb.logic.projects.create_subproject_relationship(project_id1, project_id2)
    with pytest.raises(sampledb.logic.errors.InvalidSubprojectRelationshipError):
        sampledb.logic.projects.create_subproject_relationship(project_id1, project_id2)


def test_cyclic_subproject_relationships():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id1 = sampledb.logic.projects.create_project("Test Project 1", "", user.id).id
    project_id2 = sampledb.logic.projects.create_project("Test Project 2", "", user.id).id
    project_id3 = sampledb.logic.projects.create_project("Test Project 3", "", user.id).id

    sampledb.logic.projects.create_subproject_relationship(project_id1, project_id2)
    # Direct cycle
    with pytest.raises(sampledb.logic.errors.InvalidSubprojectRelationshipError):
        sampledb.logic.projects.create_subproject_relationship(project_id2, project_id1)

    sampledb.logic.projects.create_subproject_relationship(project_id2, project_id3)
    # Indirect cycle
    with pytest.raises(sampledb.logic.errors.InvalidSubprojectRelationshipError):
        sampledb.logic.projects.create_subproject_relationship(project_id3, project_id1)


def test_project_id_hierarchy_list():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id1 = sampledb.logic.projects.create_project("Test Project 1", "", user.id).id
    project_id2 = sampledb.logic.projects.create_project("Test Project 2", "", user.id).id
    project_id3 = sampledb.logic.projects.create_project("Test Project 3", "", user.id).id

    assert sampledb.logic.projects.get_project_id_hierarchy_list([
        project_id1, project_id2, project_id3
    ]) == [
        (0, project_id1), (0, project_id2), (0, project_id3)
    ]

    sampledb.logic.projects.create_subproject_relationship(project_id1, project_id2)

    assert sampledb.logic.projects.get_project_id_hierarchy_list([
        project_id1, project_id2, project_id3
    ]) == [
        (0, project_id1), (1, project_id2), (0, project_id3)
    ]

    sampledb.logic.projects.create_subproject_relationship(project_id2, project_id3)

    assert sampledb.logic.projects.get_project_id_hierarchy_list([
        project_id1, project_id2, project_id3
    ]) == [
        (0, project_id1), (1, project_id2), (2, project_id3)
    ]

    project_id4 = sampledb.logic.projects.create_project("Test Project 4", "", user.id).id
    project_id5 = sampledb.logic.projects.create_project("Test Project 5", "", user.id).id

    assert sampledb.logic.projects.get_project_id_hierarchy_list([
        project_id1, project_id2, project_id3, project_id4, project_id5
    ]) == [
        (0, project_id1), (1, project_id2), (2, project_id3), (0, project_id4), (0, project_id5)
    ]

    sampledb.logic.projects.create_subproject_relationship(project_id4, project_id5)

    assert sampledb.logic.projects.get_project_id_hierarchy_list([
        project_id1, project_id2, project_id3, project_id4, project_id5
    ]) == [
        (0, project_id1), (1, project_id2), (2, project_id3), (0, project_id4), (1, project_id5)
    ]

    sampledb.logic.projects.create_subproject_relationship(project_id1, project_id4)

    assert sampledb.logic.projects.get_project_id_hierarchy_list([
        project_id1, project_id2, project_id3, project_id4, project_id5
    ]) == [
        (0, project_id1), (1, project_id2), (2, project_id3), (1, project_id4), (2, project_id5)
    ]

    assert sampledb.logic.projects.get_project_id_hierarchy_list([
        project_id1, project_id2, project_id3, project_id5
    ]) == [
        (0, project_id1), (1, project_id2), (2, project_id3), (0, project_id5)
    ]

    assert sampledb.logic.projects.get_project_id_hierarchy_list([
        project_id2, project_id3, project_id4, project_id5
    ]) == [
        (0, project_id2), (1, project_id3), (0, project_id4), (1, project_id5)
    ]

    sampledb.logic.projects.create_subproject_relationship(project_id1, project_id5)

    assert sampledb.logic.projects.get_project_id_hierarchy_list([
        project_id1, project_id2, project_id3, project_id4, project_id5
    ]) == [
        (0, project_id1), (1, project_id2), (2, project_id3), (1, project_id4), (2, project_id5), (1, project_id5)
    ]


def test_project_object_link():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id1 = sampledb.logic.projects.create_project("Test Project 1", "", user.id).id
    project_id2 = sampledb.logic.projects.create_project("Test Project 2", "", user.id).id

    action_type = sampledb.models.ActionType.query.filter_by(id=sampledb.models.ActionType.SAMPLE_CREATION).first()
    action_type.enable_project_link = True
    sampledb.db.session.add(action_type)
    sampledb.db.session.commit()

    action = sampledb.logic.actions.create_action(
        action_type_id=action_type.id,
        schema={
            "title": "Test Action",
            "type": "object",
            "properties": {
                "name": {
                    "title": "Name",
                    "type": "text"
                }
            },
            "required": ["name"]
        }
    )
    object1 = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            "name": {
                "_type": "text",
                "text": "Object 1"
            }
        },
        user_id=user.id
    )
    object2 = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            "name": {
                "_type": "text",
                "text": "Object 2"
            }
        },
        user_id=user.id
    )
    assert sampledb.logic.projects.get_object_linked_to_project(project_id1) is None
    assert sampledb.logic.projects.get_project_linked_to_object(object1.id) is None
    assert sampledb.logic.projects.get_project_object_links() == []

    sampledb.logic.projects.link_project_and_object(project_id1, object1.id, user.id)
    assert sampledb.logic.projects.get_object_linked_to_project(project_id1).id == object1.id
    assert sampledb.logic.projects.get_project_linked_to_object(object1.id).id == project_id1
    assert sampledb.logic.projects.get_project_object_links() == [(project_id1, object1.id)]

    with pytest.raises(sampledb.logic.errors.ProjectObjectLinkAlreadyExistsError):
        sampledb.logic.projects.link_project_and_object(project_id2, object1.id, user.id)
    with pytest.raises(sampledb.logic.errors.ProjectObjectLinkAlreadyExistsError):
        sampledb.logic.projects.link_project_and_object(project_id1, object2.id, user.id)
    with pytest.raises(sampledb.logic.errors.ProjectObjectLinkAlreadyExistsError):
        sampledb.logic.projects.link_project_and_object(project_id1, object1.id, user.id)
    assert sampledb.logic.projects.get_object_linked_to_project(project_id1).id == object1.id
    assert sampledb.logic.projects.get_project_linked_to_object(object1.id).id == project_id1
    assert sampledb.logic.projects.get_project_object_links() == [(project_id1, object1.id)]

    sampledb.logic.projects.link_project_and_object(project_id2, object2.id, user.id)
    assert sampledb.logic.projects.get_object_linked_to_project(project_id2).id == object2.id
    assert sampledb.logic.projects.get_project_linked_to_object(object2.id).id == project_id2
    assert sampledb.logic.projects.get_project_object_links() == [(project_id1, object1.id), (project_id2, object2.id)]

    with pytest.raises(sampledb.logic.errors.ProjectObjectLinkDoesNotExistsError):
        sampledb.logic.projects.unlink_project_and_object(project_id1, object2.id, user.id)
    with pytest.raises(sampledb.logic.errors.ProjectObjectLinkDoesNotExistsError):
        sampledb.logic.projects.unlink_project_and_object(project_id2, object1.id, user.id)

    sampledb.logic.projects.unlink_project_and_object(project_id1, object1.id, user.id)
    assert sampledb.logic.projects.get_object_linked_to_project(project_id1) is None
    assert sampledb.logic.projects.get_project_linked_to_object(object1.id) is None
    assert sampledb.logic.projects.get_object_linked_to_project(project_id2).id == object2.id
    assert sampledb.logic.projects.get_project_linked_to_object(object2.id).id == project_id2
    assert sampledb.logic.projects.get_project_object_links() == [(project_id2, object2.id)]


def test_project_translations():
    user = sampledb.models.User("Example User", "example@example.com", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    project = sampledb.logic.projects.create_project(
        name="Example Project",
        description="This is an example project",
        initial_user_id=user.id
    )
    assert project.name == {
        'en': 'Example Project'
    }
    assert project.description == {
        'en': 'This is an example project'
    }

    with pytest.raises(Exception):
        sampledb.logic.projects.update_project(
            project_id=project.id,
            name="Example Project 2",
            description="This is an example project 2"
        )
    project = sampledb.logic.projects.get_project(project.id)
    assert project.name == {
        'en': 'Example Project'
    }
    assert project.description == {
        'en': 'This is an example project'
    }

    sampledb.logic.projects.update_project(
        project_id=project.id,
        name={'en': "Example Project 2"},
        description={'en': "This is an example project 2"},
    )
    project = sampledb.logic.projects.get_project(project.id)
    assert project.name == {
        'en': 'Example Project 2'
    }
    assert project.description == {
        'en': 'This is an example project 2'
    }

    german = sampledb.logic.languages.get_language_by_lang_code('de')
    sampledb.logic.languages.update_language(
        language_id=german.id,
        names=german.names,
        lang_code=german.lang_code,
        datetime_format_datetime=german.datetime_format_datetime,
        datetime_format_moment=german.datetime_format_moment,
        datetime_format_moment_output=german.datetime_format_moment_output,
        enabled_for_input=True,
        enabled_for_user_interface=True
    )

    sampledb.logic.projects.update_project(
        project_id=project.id,
        name={
            'en': "Example Project",
            'de': "Beispielprojekt"
        },
        description={
            'en': "This is an example project",
            'de': "Dies ist ein Beispielprojekt"
        }
    )
    project = sampledb.logic.projects.get_project(project.id)
    assert project.name == {
        'en': "Example Project",
        'de': "Beispielprojekt"
    }
    assert project.description == {
        'en': "This is an example project",
        'de': "Dies ist ein Beispielprojekt"
    }

    with pytest.raises(sampledb.logic.errors.LanguageDoesNotExistError):
        sampledb.logic.projects.update_project(
            project_id=project.id,
            name={
                'en': "Example Project",
                'xy': "Beispielprojekt"
            },
            description={
                'en': "This is an example project",
                'xy': "Dies ist ein Beispielprojekt"
            }
        )

    project = sampledb.logic.projects.get_project(project.id)
    assert project.name == {
        'en': "Example Project",
        'de': "Beispielprojekt"
    }
    assert project.description == {
        'en': "This is an example project",
        'de': "Dies ist ein Beispielprojekt"
    }

    with pytest.raises(sampledb.logic.errors.MissingEnglishTranslationError):
        sampledb.logic.projects.update_project(
            project_id=project.id,
            name={
                'de': "Beispielprojekt"
            },
            description={
                'de': "Dies ist ein Beispielprojekt"
            }
        )

    project = sampledb.logic.projects.get_project(project.id)
    assert project.name == {
        'en': "Example Project",
        'de': "Beispielprojekt"
    }
    assert project.description == {
        'en': "This is an example project",
        'de': "Dies ist ein Beispielprojekt"
    }

    with pytest.raises(sampledb.logic.errors.MissingEnglishTranslationError):
        sampledb.logic.projects.update_project(
            project_id=project.id,
            name={},
            description={}
        )

    project = sampledb.logic.projects.get_project(project.id)
    assert project.name == {
        'en': "Example Project",
        'de': "Beispielprojekt"
    }
    assert project.description == {
        'en': "This is an example project",
        'de': "Dies ist ein Beispielprojekt"
    }

    with pytest.raises(sampledb.logic.errors.LanguageDoesNotExistError):
        sampledb.logic.projects.create_project(
            name={
                'en': "Example Project 2",
                'xy': "Beispielprojekt 2"
            },
            description={
                'en': "This is an example project",
                'xy': "Dies ist ein Beispielprojekt"
            },
            initial_user_id=user.id
        )

    with pytest.raises(sampledb.logic.errors.MissingEnglishTranslationError):
        sampledb.logic.projects.create_project(
            name={
                'de': "Beispielort 2"
            },
            description={
                'de': "Dies ist ein Beispielprojekt"
            },
            initial_user_id=user.id
        )

    with pytest.raises(sampledb.logic.errors.MissingEnglishTranslationError):
        sampledb.logic.projects.create_project(
            name={},
            description={},
            initial_user_id=user.id
        )


def test_sort_project_id_hierarchy_list():
    user = sampledb.logic.users.create_user('User', 'example@example.org', sampledb.models.UserType.PERSON)
    project_id1 = sampledb.logic.projects.create_project({"en": "a"}, {"en": ""}, user.id).id
    project_id2 = sampledb.logic.projects.create_project({"en": "c"}, {"en": ""}, user.id).id
    project_id3 = sampledb.logic.projects.create_project({"en": "B"}, {"en": ""}, user.id).id
    project_id4 = sampledb.logic.projects.create_project({"en": "2-B"}, {"en": ""}, user.id).id
    project_id5 = sampledb.logic.projects.create_project({"en": "1-B"}, {"en": ""}, user.id).id
    sampledb.logic.projects.create_subproject_relationship(parent_project_id=project_id3, child_project_id=project_id4)
    sampledb.logic.projects.create_subproject_relationship(parent_project_id=project_id3, child_project_id=project_id5)
    project_id_hierarchy_list = sampledb.logic.projects.get_project_id_hierarchy_list([project_id1, project_id2, project_id3, project_id4, project_id5])
    project_id_hierarchy_list = sampledb.logic.projects.sort_project_id_hierarchy_list(project_id_hierarchy_list, key=lambda project: project.id)
    assert project_id_hierarchy_list == [(0, project_id1), (0, project_id2), (0, project_id3), (1, project_id4), (1, project_id5)]
    project_id_hierarchy_list = sampledb.logic.projects.sort_project_id_hierarchy_list(project_id_hierarchy_list, key=lambda project: project.name['en'])
    assert project_id_hierarchy_list == [(0, project_id3), (1, project_id5), (1, project_id4), (0, project_id1), (0, project_id2)]
    project_id_hierarchy_list = sampledb.logic.projects.sort_project_id_hierarchy_list(project_id_hierarchy_list, key=lambda project: project.name['en'].lower())
    assert project_id_hierarchy_list == [(0, project_id1), (0, project_id3), (1, project_id5), (1, project_id4), (0, project_id2)]