# coding: utf-8
"""

"""

import pytest
import sampledb
import sampledb.logic
import sampledb.models

from ..test_utils import app_context, app


def test_create_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.projects.Project.query.all()) == 0

    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert len(sampledb.models.projects.Project.query.all()) == 1
    project = sampledb.models.projects.Project.query.get(project_id)
    assert project is not None
    assert project.id == project_id
    assert project.name == "Example Project"
    assert project.description == ""


def test_create_project_with_user_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.projects.Project.query.all()) == 0

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.create_project("Example Project", "", user.id+1)

    assert len(sampledb.models.projects.Project.query.all()) == 0


def test_create_duplicate_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Example Project", "", user.id)
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.ProjectAlreadyExistsError):
        sampledb.logic.projects.create_project("Example Project", "", user.id)

    assert len(sampledb.models.projects.Project.query.all()) == 1


def test_create_project_with_empty_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.projects.Project.query.all()) == 0

    with pytest.raises(sampledb.logic.errors.InvalidProjectNameError):
        sampledb.logic.projects.create_project("", "", user.id)

    assert len(sampledb.models.projects.Project.query.all()) == 0


def test_create_project_with_long_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.projects.Project.query.all()) == 0

    with pytest.raises(sampledb.logic.errors.InvalidProjectNameError):
        sampledb.logic.projects.create_project("A"*101, "", user.id)

    assert len(sampledb.models.projects.Project.query.all()) == 0

    project_id = sampledb.logic.projects.create_project("A"*100, "", user.id).id

    assert len(sampledb.models.projects.Project.query.all()) == 1
    project = sampledb.models.projects.Project.query.get(project_id)
    assert project is not None
    assert project.id == project_id
    assert project.name == "A"*100
    assert project.description == ""


def test_get_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    project = sampledb.logic.projects.get_project(project_id)

    assert project.id == project_id
    assert project.name == "Example Project"
    assert project.description == ""


def test_get_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.get_project(project_id+1)


def test_get_projects():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    projects = sampledb.logic.projects.get_projects()
    assert len(projects) == 0

    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    projects = sampledb.logic.projects.get_projects()
    assert len(projects) == 1
    project = projects[0]
    assert project.id == project_id
    assert project.name == "Example Project"
    assert project.description == ""

    sampledb.logic.projects.delete_project(project_id)
    projects = sampledb.logic.projects.get_projects()
    assert len(projects) == 0

    sampledb.logic.projects.create_project("Example Project 1", "", user.id)
    sampledb.logic.projects.create_project("Example Project 2", "", user.id)
    projects = sampledb.logic.projects.get_projects()
    assert len(projects) == 2
    assert {projects[0].name, projects[1].name} == {"Example Project 1", "Example Project 2"}


def test_update_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    sampledb.logic.projects.update_project(project_id, "Test Project", "Test Description")

    project = sampledb.models.projects.Project.query.get(project_id)
    assert project is not None
    assert project.id == project_id
    assert project.name == "Test Project"
    assert project.description == "Test Description"


def test_update_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.update_project(project_id+1, "Test Project", "Test Description")

    project = sampledb.models.projects.Project.query.get(project_id)
    assert project is not None
    assert project.id == project_id
    assert project.name == "Example Project"
    assert project.description == ""


def test_update_project_with_existing_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Example Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project 2", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 2

    with pytest.raises(sampledb.logic.errors.ProjectAlreadyExistsError):
        sampledb.logic.projects.update_project(project_id, "Example Project", "")

    project = sampledb.models.projects.Project.query.get(project_id)
    assert project is not None
    assert project.id == project_id
    assert project.name == "Example Project 2"
    assert project.description == ""


def test_update_project_with_empty_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.InvalidProjectNameError):
        sampledb.logic.projects.update_project(project_id, "", "Test Description")

    project = sampledb.models.projects.Project.query.get(project_id)
    assert project is not None
    assert project.id == project_id
    assert project.name == "Example Project"
    assert project.description == ""


def test_update_project_with_long_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.InvalidProjectNameError):
        sampledb.logic.projects.update_project(project_id, "A"*101, "")

    project = sampledb.models.projects.Project.query.get(project_id)
    assert project is not None
    assert project.id == project_id
    assert project.name == "Example Project"
    assert project.description == ""

    sampledb.logic.projects.update_project(project_id, "A"*100, "")

    project = sampledb.models.projects.Project.query.get(project_id)
    assert project is not None
    assert project.id == project_id
    assert project.name == "A"*100
    assert project.description == ""


def test_delete_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    assert project.name == "Test Project"
    assert project.description == "Test Description"


def test_delete_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Test Project", "Test Description", user.id).id
    assert len(sampledb.models.projects.Project.query.all()) == 1

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.delete_project(project_id+1)

    assert len(sampledb.models.projects.Project.query.all()) == 1
    project = sampledb.models.projects.Project.query.get(project_id)
    assert project is not None
    assert project.id == project_id
    assert project.name == "Test Project"
    assert project.description == "Test Description"


def test_add_user_to_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    project_creator = user
    user_permissions = sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id)
    assert len(user_permissions) == 1
    assert user_permissions[project_creator.id] == sampledb.models.Permissions.GRANT

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user.id, permissions=sampledb.models.Permissions.WRITE)

    user_permissions = sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id)
    assert len(user_permissions) == 2
    assert user_permissions[project_creator.id] == sampledb.models.Permissions.GRANT
    assert user_permissions[user.id] == sampledb.models.Permissions.WRITE


def test_add_user_to_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.add_user_to_project(project_id+1, user.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_add_user_that_does_not_exist_to_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.add_user_to_project(project_id, user.id+1, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_add_user_that_is_already_a_member_to_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user2.id, permissions=sampledb.models.Permissions.NONE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }



# def test_send_confirm_email_to_invite_user_to_project(app):
#     app.config['SERVER_NAME'] = 'localhost'
#     with app.app_context():
#         user = sampledb.models.User("Inviting User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
#         sampledb.db.session.add(user)
#         sampledb.db.session.commit()
#         project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
#         project = sampledb.models.projects.Project.query.get(project_id)
#
#         user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
#         sampledb.db.session.add(user2)
#         sampledb.db.session.commit()
#
#         assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
#             user.id: sampledb.models.Permissions.GRANT
#         }
#
#         with sampledb.mail.record_messages() as outbox:
#             sampledb.logic.utils.send_confirm_email_to_invite_user_to_project(project_id, user2.id)
#
#         assert len(outbox) == 1
#         assert 'example@fz-juelich.de' in outbox[0].recipients
#         message = outbox[0].html
#         assert 'Join project {}'.format(project.name) in message
#         assert 'You have been invited to be a member of the project {}.'.format(project.name) in message


def test_invite_user_to_project_does_not_exist():

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.invite_user_to_project(project_id + 1, user.id)


def test_invite_user_to_project_user_does_not_exist():

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.invite_user_to_project(project_id, 2)


def test_invite_user_that_is_already_a_member_to_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    with pytest.raises(sampledb.logic.errors.UserAlreadyMemberOfProjectError):
        sampledb.logic.projects.invite_user_to_project(project_id, user.id)


def test_invite_user_to_project(app):
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        user = sampledb.models.User("Inviting User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
        project = sampledb.models.projects.Project.query.get(project_id)

        user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user2)
        sampledb.db.session.commit()

        assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
             user.id: sampledb.models.Permissions.GRANT
         }

        with sampledb.mail.record_messages() as outbox:
            sampledb.logic.utils.send_confirm_email_to_invite_user_to_project(project_id, user2.id)

        assert len(outbox) == 1
        assert 'example@fz-juelich.de' in outbox[0].recipients
        message = outbox[0].html
        assert 'Join project {}'.format(project.name) in message
        assert 'You have been invited to be a member of the project {}.'.format(project.name) in message


def test_remove_user_from_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    sampledb.logic.projects.remove_user_from_project(project_id, user.id)

    assert len(sampledb.models.projects.Project.query.all()) == 0


def test_remove_user_from_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.remove_user_from_project(project_id+1, user.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_remove_user_that_does_not_exist_from_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.remove_user_from_project(project_id, user.id+1)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_remove_user_that_is_not_a_member_from_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    assert project.name == "Example Project"
    assert project.description == ""


def test_get_user_projects_for_user_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.get_user_projects(user.id+1)


def test_get_user_project_permissions():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.GRANT


    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.NONE

    sampledb.logic.projects.add_user_to_project(project_id, user.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.WRITE


def test_get_user_project_permissions_including_groups():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user.id, sampledb.models.Permissions.READ)

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.READ

    group = sampledb.logic.groups.create_group("Example Group", "", user.id)

    sampledb.logic.projects.add_group_to_project(project_id, group.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id) == sampledb.models.Permissions.READ
    assert sampledb.logic.projects.get_user_project_permissions(project_id, user.id, include_groups=True) == sampledb.models.Permissions.WRITE


def test_get_project_member_ids_for_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id
    sampledb.models.projects.Project.query.get(project_id)

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id+1)

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id+1)


def test_add_group_to_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.add_group_to_project(project_id+1, group.id, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}


def test_add_group_that_does_not_exist_to_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}

    group = sampledb.logic.groups.create_group("Example Group", "", user2.id)

    with pytest.raises(sampledb.logic.errors.GroupDoesNotExistError):
        sampledb.logic.projects.add_group_to_project(project_id, group.id+1, sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {}


def test_add_group_that_is_already_a_member_to_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
        sampledb.logic.projects.remove_group_from_project(project_id+1, group.id)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }


def test_remove_group_that_does_not_exist_from_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
        sampledb.logic.projects.remove_group_from_project(project_id, group.id+1)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.WRITE
    }


def test_remove_group_that_is_not_a_member_from_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()

    sampledb.logic.projects.add_user_to_project(project_id, user2.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.WRITE
    }

    with pytest.raises(sampledb.logic.errors.NoMemberWithGrantPermissionsForProjectError):
        sampledb.logic.projects.update_user_project_permissions(project_id, user.id, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT,
        user2.id: sampledb.models.Permissions.WRITE
    }


def test_update_user_project_permissions_for_user_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.UserDoesNotExistError):
        sampledb.logic.projects.update_user_project_permissions(project_id, user.id+1, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_update_user_project_permissions_for_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    with pytest.raises(sampledb.logic.errors.ProjectDoesNotExistError):
        sampledb.logic.projects.update_user_project_permissions(project_id+1, user.id, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }


def test_update_user_project_permissions_for_user_that_is_no_member_of_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
        sampledb.logic.projects.update_group_project_permissions(project_id, group.id+1, permissions=sampledb.models.Permissions.GRANT)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.READ
    }


def test_update_group_project_permissions_for_project_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
        sampledb.logic.projects.update_group_project_permissions(project_id+1, group.id, permissions=sampledb.models.Permissions.WRITE)

    assert sampledb.logic.projects.get_project_member_user_ids_and_permissions(project_id) == {
        user.id: sampledb.models.Permissions.GRANT
    }

    assert sampledb.logic.projects.get_project_member_group_ids_and_permissions(project_id) == {
        group.id: sampledb.models.Permissions.READ
    }


def test_update_group_project_permissions_for_user_that_is_no_member_of_project():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    assert project.name == "Example Project"
    assert project.description == ""


def test_get_group_projects_for_group_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    group = sampledb.logic.groups.create_group("Example Group", "", user.id)

    with pytest.raises(sampledb.logic.errors.GroupDoesNotExistError):
        sampledb.logic.projects.get_group_projects(group.id+1)


def test_get_project_member_user_ids_including_groups():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user2 = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.projects.create_project("Test Project", "", user.id)
    project_id = sampledb.logic.projects.create_project("Example Project", "", user.id).id

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
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
    assert project.name == "Example Project"
    assert project.description == ""
