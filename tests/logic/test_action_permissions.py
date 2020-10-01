# coding: utf-8
"""

"""

import pytest

import sampledb
import sampledb.logic
from sampledb.logic import action_permissions, groups
from sampledb.models import User, UserType, Action, Instrument, Permissions, UserActionPermissions


__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture
def users():
    names = ['User 1', 'User 2']
    users = [User(name=name, email="example@fz-juelich.de", type=UserType.PERSON) for name in names]
    for user in users:
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return users


@pytest.fixture
def independent_action():
    action = Action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Action',
            'type': 'action',
            'properties': {}
        },
        description='',
        instrument_id=None
    )
    sampledb.db.session.add(action)
    sampledb.db.session.commit()
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def user_action(users):
    action = Action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Action',
            'type': 'action',
            'properties': {}
        },
        description='',
        instrument_id=None,
        user_id=users[1].id
    )
    sampledb.db.session.add(action)
    sampledb.db.session.commit()
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def instrument():
    instrument = Instrument(
        name='Example Action',
        description=''
    )
    sampledb.db.session.add(instrument)
    sampledb.db.session.commit()
    # force attribute refresh
    assert instrument.id is not None
    return instrument


@pytest.fixture
def instrument_action(instrument):
    action = Action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name='Example Action',
        schema={
            'title': 'Example Action',
            'type': 'action',
            'properties': {}
        },
        description='',
        instrument_id=instrument.id
    )
    sampledb.db.session.add(action)
    sampledb.db.session.commit()
    # force attribute refresh
    assert action.id is not None
    return action


@pytest.fixture
def user(users):
    return users[0]


def test_public_actions(independent_action, user_action):
    # non-user actions will always
    action_id = independent_action.id
    assert action_permissions.action_is_public(action_id)
    action_permissions.set_action_public(action_id)
    assert action_permissions.action_is_public(action_id)
    action_permissions.set_action_public(action_id, False)
    assert action_permissions.action_is_public(action_id)

    action_id = user_action.id
    assert not action_permissions.action_is_public(action_id)
    action_permissions.set_action_public(action_id)
    assert action_permissions.action_is_public(action_id)
    action_permissions.set_action_public(action_id, False)
    assert not action_permissions.action_is_public(action_id)


def test_get_user_action_permissions(user, independent_action):
    user_id = user.id
    action_id = independent_action.id
    sampledb.db.session.add(UserActionPermissions(user_id=user_id, action_id=action_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.WRITE


def test_get_user_action_permissions_with_project(users, user_action):
    user_id = users[0].id
    action_id = user_action.id
    project_id = sampledb.logic.projects.create_project("Example Project", "", users[1].id).id
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.NONE
    action_permissions.set_project_action_permissions(project_id=project_id, action_id=action_id, permissions=Permissions.GRANT)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.NONE
    sampledb.logic.projects.add_user_to_project(project_id, user_id, Permissions.READ)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.READ
    sampledb.db.session.add(UserActionPermissions(user_id=user_id, action_id=action_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.WRITE
    sampledb.logic.projects.update_user_project_permissions(project_id, user_id, Permissions.GRANT)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.GRANT


def test_get_user_action_permissions_with_group_project(users, user_action):
    user_id = users[0].id
    action_id = user_action.id
    project_id = sampledb.logic.projects.create_project("Example Project", "", users[1].id).id
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.NONE
    action_permissions.set_project_action_permissions(project_id=project_id, action_id=action_id, permissions=Permissions.GRANT)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.NONE
    group_id = sampledb.logic.groups.create_group("Example Group", "", users[1].id).id
    sampledb.logic.projects.add_group_to_project(project_id, group_id, Permissions.READ)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.NONE
    sampledb.logic.groups.add_user_to_group(group_id=group_id, user_id=user_id)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.READ
    sampledb.db.session.add(UserActionPermissions(user_id=user_id, action_id=action_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.WRITE
    sampledb.logic.projects.update_group_project_permissions(project_id, group_id, Permissions.GRANT)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.GRANT


def test_get_instrument_responsible_user_action_permissions(user, instrument, instrument_action):
    user_id = user.id
    action_id = instrument_action.id
    instrument.responsible_users.append(user)
    sampledb.db.session.add(instrument)
    sampledb.db.session.add(UserActionPermissions(user_id=user_id, action_id=action_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.GRANT


def test_get_user_user_action_permissions(users, user_action):
    action_id = user_action.id

    user_id = users[0].id
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.NONE

    user_id = users[1].id
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.GRANT


def test_get_user_public_action_permissions(user, user_action, independent_action):
    user_id = user.id
    action_id = user_action.id
    action_permissions.set_action_public(action_id)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.READ

    action_id = independent_action.id
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.READ


def test_get_action_permissions(users, user_action):
    user_id = users[0].id
    action_id = user_action.id

    # by default, only the user who created an action has access to it
    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        users[1].id: Permissions.GRANT
    }
    assert not action_permissions.action_is_public(action_id)

    action_permissions.set_action_public(action_id)
    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        users[1].id: Permissions.GRANT
    }
    assert action_permissions.action_is_public(action_id)

    sampledb.db.session.add(UserActionPermissions(user_id=user_id, action_id=action_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        user_id: Permissions.WRITE,
        users[1].id: Permissions.GRANT
    }
    assert action_permissions.action_is_public(action_id)


def test_get_action_permissions_with_projects(users, user_action):
    user_id = users[0].id
    action_id = user_action.id

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        users[1].id: Permissions.GRANT
    }

    project_id = sampledb.logic.projects.create_project("Example Project", "", users[1].id).id

    action_permissions.set_project_action_permissions(action_id=action_id, project_id=project_id, permissions=Permissions.WRITE)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        users[1].id: Permissions.GRANT
    }

    sampledb.logic.projects.add_user_to_project(project_id, user_id, Permissions.READ)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id, include_projects=False) == {
        users[1].id: Permissions.GRANT
    }

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }

    group_id = sampledb.logic.groups.create_group("Example Group", "", users[1].id).id

    sampledb.logic.projects.add_group_to_project(project_id=project_id, group_id=group_id, permissions=Permissions.WRITE)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }

    sampledb.logic.groups.add_user_to_group(group_id=group_id, user_id=user_id)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id, include_groups=False) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        user_id: Permissions.WRITE,
        users[1].id: Permissions.GRANT
    }

    sampledb.logic.groups.remove_user_from_group(group_id=group_id, user_id=user_id)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }


def test_update_action_permissions(users, user_action):
    user_id = users[0].id
    action_id = user_action.id

    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.NONE
    action_permissions.set_user_action_permissions(action_id=action_id, user_id=user_id, permissions=Permissions.WRITE)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.WRITE

    action_permissions.set_user_action_permissions(action_id=action_id, user_id=user_id, permissions=Permissions.READ)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.READ

    action_permissions.set_user_action_permissions(action_id=action_id, user_id=user_id, permissions=Permissions.NONE)
    assert action_permissions.get_user_action_permissions(user_id=user_id, action_id=action_id) == Permissions.NONE
    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        users[1].id: Permissions.GRANT
    }
    assert not action_permissions.action_is_public(action_id)


def test_group_permissions(users, user_action):
    user, creator = users
    action_id = user_action.id
    group_id = groups.create_group("Example Group", "", creator.id).id

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        creator.id: Permissions.GRANT
    }
    assert not action_permissions.action_is_public(action_id)
    assert action_permissions.get_user_action_permissions(action_id=action_id, user_id=user.id) == Permissions.NONE

    action_permissions.set_group_action_permissions(action_id=action_id, group_id=group_id, permissions=Permissions.WRITE)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        creator.id: Permissions.GRANT
    }
    assert not action_permissions.action_is_public(action_id)
    assert action_permissions.get_user_action_permissions(action_id=action_id, user_id=user.id) == Permissions.NONE

    groups.add_user_to_group(group_id=group_id, user_id=user.id)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.WRITE
    }
    assert not action_permissions.action_is_public(action_id)
    assert action_permissions.get_user_action_permissions(action_id=action_id, user_id=user.id) == Permissions.WRITE

    action_permissions.set_user_action_permissions(action_id=action_id, user_id=user.id, permissions=Permissions.READ)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.WRITE
    }
    assert not action_permissions.action_is_public(action_id)
    assert action_permissions.get_user_action_permissions(action_id=action_id, user_id=user.id) == Permissions.WRITE

    action_permissions.set_group_action_permissions(action_id=action_id, group_id=group_id, permissions=Permissions.READ)
    action_permissions.set_user_action_permissions(action_id=action_id, user_id=user.id, permissions=Permissions.WRITE)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.WRITE
    }
    assert not action_permissions.action_is_public(action_id)
    assert action_permissions.get_user_action_permissions(action_id=action_id, user_id=user.id) == Permissions.WRITE

    action_permissions.set_user_action_permissions(action_id=action_id, user_id=user.id, permissions=Permissions.READ)
    action_permissions.set_group_action_permissions(action_id=action_id, group_id=group_id, permissions=Permissions.GRANT)
    groups.remove_user_from_group(group_id=group_id, user_id=user.id)

    assert action_permissions.get_action_permissions_for_users(action_id=action_id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.READ
    }
    assert not action_permissions.action_is_public(action_id)
    assert action_permissions.get_user_action_permissions(action_id=action_id, user_id=user.id) == Permissions.READ


def test_action_permissions_for_groups_with_project(users, user_action):
    user, creator = users
    action_id = user_action.id
    group_id = groups.create_group("Example Group", "", creator.id).id

    action_permissions.set_group_action_permissions(action_id=action_id, group_id=group_id, permissions=Permissions.READ)

    assert action_permissions.get_action_permissions_for_groups(action_id) == {
        group_id: Permissions.READ
    }

    project_id = sampledb.logic.projects.create_project("Example Project", "", creator.id).id
    action_permissions.set_project_action_permissions(action_id=action_id, project_id=project_id, permissions=Permissions.GRANT)

    assert action_permissions.get_action_permissions_for_groups(action_id) == {
        group_id: Permissions.READ
    }

    sampledb.logic.projects.add_group_to_project(project_id=project_id, group_id=group_id, permissions=Permissions.WRITE)

    assert action_permissions.get_action_permissions_for_groups(action_id) == {
        group_id: Permissions.READ
    }

    assert action_permissions.get_action_permissions_for_groups(action_id, include_projects=True) == {
        group_id: Permissions.WRITE
    }

    sampledb.logic.projects.update_group_project_permissions(project_id=project_id, group_id=group_id, permissions=Permissions.GRANT)

    assert action_permissions.get_action_permissions_for_groups(action_id, include_projects=True) == {
        group_id: Permissions.GRANT
    }

    sampledb.logic.projects.remove_group_from_project(project_id=project_id, group_id=group_id)

    assert action_permissions.get_action_permissions_for_groups(action_id, include_projects=True) == {
        group_id: Permissions.READ
    }


def test_action_permissions_for_groups(users, user_action):
    user, creator = users
    action_id = user_action.id
    group_id = groups.create_group("Example Group", "", creator.id).id

    assert action_permissions.get_action_permissions_for_groups(action_id) == {}

    action_permissions.set_group_action_permissions(action_id=action_id, group_id=group_id, permissions=Permissions.WRITE)

    assert action_permissions.get_action_permissions_for_groups(action_id) == {
        group_id: Permissions.WRITE
    }

    action_permissions.set_group_action_permissions(action_id=action_id, group_id=group_id, permissions=Permissions.NONE)

    assert action_permissions.get_action_permissions_for_groups(action_id) == {}


def test_action_permissions_for_projects(users, user_action):
    user, creator = users
    action_id = user_action.id
    project_id = sampledb.logic.projects.create_project("Example Project", "", creator.id).id

    assert action_permissions.get_action_permissions_for_projects(action_id) == {}

    action_permissions.set_project_action_permissions(action_id=action_id, project_id=project_id, permissions=Permissions.WRITE)

    assert action_permissions.get_action_permissions_for_projects(action_id) == {
        project_id: Permissions.WRITE
    }

    action_permissions.set_project_action_permissions(action_id=action_id, project_id=project_id, permissions=Permissions.GRANT)

    assert action_permissions.get_action_permissions_for_projects(action_id) == {
        project_id: Permissions.GRANT
    }

    action_permissions.set_project_action_permissions(action_id=action_id, project_id=project_id, permissions=Permissions.NONE)

    assert action_permissions.get_action_permissions_for_projects(action_id) == {}

