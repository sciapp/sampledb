# coding: utf-8
"""

"""

import pytest

import sampledb
import sampledb.logic
from sampledb.logic import object_permissions, groups
from sampledb.models import User, UserType, Action, Instrument, Permissions, UserObjectPermissions


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
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
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
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
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
def objects(users, instrument_action, independent_action):
    actions = [instrument_action, independent_action]
    return [
        sampledb.logic.objects.create_object(user_id=users[1].id, action_id=action.id, data={
            'name': {
                '_type': 'text',
                'text': 'Name'
            }
        })
        for action in actions]


@pytest.fixture
def instrument_action_object(objects):
    return objects[0]


@pytest.fixture
def independent_action_object(objects):
    return objects[1]


@pytest.fixture
def user(users):
    return users[0]


def test_public_objects(independent_action_object):
    object_id = independent_action_object.object_id

    assert not object_permissions.object_is_public(object_id)
    object_permissions.set_object_public(object_id)
    assert object_permissions.object_is_public(object_id)
    object_permissions.set_object_public(object_id, False)
    assert not object_permissions.object_is_public(object_id)


def test_default_user_object_permissions(user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id

    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE


def test_get_user_object_permissions(user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.WRITE


def test_get_user_object_permissions_with_project(users, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id
    project_id = sampledb.logic.projects.create_project("Example Project", "", users[1].id).id
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    object_permissions.set_project_object_permissions(project_id=project_id, object_id=object_id, permissions=Permissions.GRANT)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    sampledb.logic.projects.add_user_to_project(project_id, user_id, Permissions.READ)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.WRITE
    sampledb.logic.projects.update_user_project_permissions(project_id, user_id, Permissions.GRANT)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.GRANT


def test_get_user_object_permissions_with_group_project(users, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id
    project_id = sampledb.logic.projects.create_project("Example Project", "", users[1].id).id
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    object_permissions.set_project_object_permissions(project_id=project_id, object_id=object_id, permissions=Permissions.GRANT)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    group_id = sampledb.logic.groups.create_group("Example Group", "", users[1].id).id
    sampledb.logic.projects.add_group_to_project(project_id, group_id, Permissions.READ)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    sampledb.logic.groups.add_user_to_group(group_id=group_id, user_id=user_id)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.WRITE
    sampledb.logic.projects.update_group_project_permissions(project_id, group_id, Permissions.GRANT)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.GRANT


def test_get_instrument_responsible_user_object_permissions(user, instrument, instrument_action_object):
    user_id = user.id
    object_id = instrument_action_object.object_id
    instrument.responsible_users.append(user)
    sampledb.db.session.add(instrument)
    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.GRANT


def test_get_user_public_object_permissions(user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    object_permissions.set_object_public(object_id)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ


def test_get_object_permissions(users, instrument, instrument_action_object):
    user_id = users[0].id
    object_id = instrument_action_object.object_id

    # by default, only the user who created an object has access to it
    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        users[1].id: Permissions.GRANT
    }
    assert not object_permissions.object_is_public(object_id)

    object_permissions.set_object_public(object_id)
    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        users[1].id: Permissions.GRANT
    }
    assert object_permissions.object_is_public(object_id)

    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.WRITE,
        users[1].id: Permissions.GRANT
    }
    assert object_permissions.object_is_public(object_id)

    instrument.responsible_users.append(users[0])
    sampledb.db.session.add(instrument)
    sampledb.db.session.commit()
    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.GRANT,
        users[1].id: Permissions.GRANT
    }
    assert object_permissions.object_is_public(object_id)


def test_get_object_permissions_with_projects(users, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        users[1].id: Permissions.GRANT
    }

    project_id = sampledb.logic.projects.create_project("Example Project", "", users[1].id).id

    object_permissions.set_project_object_permissions(object_id=object_id, project_id=project_id, permissions=Permissions.WRITE)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        users[1].id: Permissions.GRANT
    }

    sampledb.logic.projects.add_user_to_project(project_id, user_id, Permissions.READ)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id, include_projects=False) == {
        users[1].id: Permissions.GRANT
    }

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }

    group_id = sampledb.logic.groups.create_group("Example Group", "", users[1].id).id

    sampledb.logic.projects.add_group_to_project(project_id=project_id, group_id=group_id, permissions=Permissions.WRITE)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }

    sampledb.logic.groups.add_user_to_group(group_id=group_id, user_id=user_id)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id, include_groups=False) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.WRITE,
        users[1].id: Permissions.GRANT
    }

    sampledb.logic.groups.remove_user_from_group(group_id=group_id, user_id=user_id)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }


def test_update_object_permissions(users, independent_action_object):
    user_id = users[0].id
    object_id = independent_action_object.object_id

    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    object_permissions.set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=Permissions.WRITE)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.WRITE

    object_permissions.set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=Permissions.READ)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ

    object_permissions.set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=Permissions.NONE)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        users[1].id: Permissions.GRANT
    }
    assert not object_permissions.object_is_public(object_id)


def test_group_permissions(users, independent_action_object):
    user, creator = users
    object_id = independent_action_object.object_id
    group_id = groups.create_group("Example Group", "", creator.id).id

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        creator.id: Permissions.GRANT
    }
    assert not object_permissions.object_is_public(object_id)
    assert object_permissions.get_user_object_permissions(object_id=object_id, user_id=user.id) == Permissions.NONE

    object_permissions.set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=Permissions.WRITE)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        creator.id: Permissions.GRANT
    }
    assert not object_permissions.object_is_public(object_id)
    assert object_permissions.get_user_object_permissions(object_id=object_id, user_id=user.id) == Permissions.NONE

    groups.add_user_to_group(group_id=group_id, user_id=user.id)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.WRITE
    }
    assert not object_permissions.object_is_public(object_id)
    assert object_permissions.get_user_object_permissions(object_id=object_id, user_id=user.id) == Permissions.WRITE

    object_permissions.set_user_object_permissions(object_id=object_id, user_id=user.id, permissions=Permissions.READ)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.WRITE
    }
    assert not object_permissions.object_is_public(object_id)
    assert object_permissions.get_user_object_permissions(object_id=object_id, user_id=user.id) == Permissions.WRITE

    object_permissions.set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=Permissions.READ)
    object_permissions.set_user_object_permissions(object_id=object_id, user_id=user.id, permissions=Permissions.WRITE)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.WRITE
    }
    assert not object_permissions.object_is_public(object_id)
    assert object_permissions.get_user_object_permissions(object_id=object_id, user_id=user.id) == Permissions.WRITE

    object_permissions.set_user_object_permissions(object_id=object_id, user_id=user.id, permissions=Permissions.READ)
    object_permissions.set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=Permissions.GRANT)
    groups.remove_user_from_group(group_id=group_id, user_id=user.id)

    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.READ
    }
    assert not object_permissions.object_is_public(object_id)
    assert object_permissions.get_user_object_permissions(object_id=object_id, user_id=user.id) == Permissions.READ


def test_object_permissions_for_groups_with_project(users, independent_action_object):
    user, creator = users
    object_id = independent_action_object.object_id
    group_id = groups.create_group("Example Group", "", creator.id).id

    object_permissions.set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=Permissions.READ)

    assert object_permissions.get_object_permissions_for_groups(object_id) == {
        group_id: Permissions.READ
    }

    project_id = sampledb.logic.projects.create_project("Example Project", "", creator.id).id
    object_permissions.set_project_object_permissions(object_id=object_id, project_id=project_id, permissions=Permissions.GRANT)

    assert object_permissions.get_object_permissions_for_groups(object_id) == {
        group_id: Permissions.READ
    }

    sampledb.logic.projects.add_group_to_project(project_id=project_id, group_id=group_id, permissions=Permissions.WRITE)

    assert object_permissions.get_object_permissions_for_groups(object_id) == {
        group_id: Permissions.READ
    }

    assert object_permissions.get_object_permissions_for_groups(object_id, include_projects=True) == {
        group_id: Permissions.WRITE
    }

    sampledb.logic.projects.update_group_project_permissions(project_id=project_id, group_id=group_id, permissions=Permissions.GRANT)

    assert object_permissions.get_object_permissions_for_groups(object_id, include_projects=True) == {
        group_id: Permissions.GRANT
    }

    sampledb.logic.projects.remove_group_from_project(project_id=project_id, group_id=group_id)

    assert object_permissions.get_object_permissions_for_groups(object_id, include_projects=True) == {
        group_id: Permissions.READ
    }


def test_object_permissions_for_groups(users, independent_action_object):
    user, creator = users
    object_id = independent_action_object.object_id
    group_id = groups.create_group("Example Group", "", creator.id).id

    assert object_permissions.get_object_permissions_for_groups(object_id) == {}

    object_permissions.set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=Permissions.WRITE)

    assert object_permissions.get_object_permissions_for_groups(object_id) == {
        group_id: Permissions.WRITE
    }

    object_permissions.set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=Permissions.NONE)

    assert object_permissions.get_object_permissions_for_groups(object_id) == {}


def test_object_permissions_for_projects(users, independent_action_object):
    user, creator = users
    object_id = independent_action_object.object_id
    project_id = sampledb.logic.projects.create_project("Example Project", "", creator.id).id

    assert object_permissions.get_object_permissions_for_projects(object_id) == {}

    object_permissions.set_project_object_permissions(object_id=object_id, project_id=project_id, permissions=Permissions.WRITE)

    assert object_permissions.get_object_permissions_for_projects(object_id) == {
        project_id: Permissions.WRITE
    }

    object_permissions.set_project_object_permissions(object_id=object_id, project_id=project_id, permissions=Permissions.GRANT)

    assert object_permissions.get_object_permissions_for_projects(object_id) == {
        project_id: Permissions.GRANT
    }

    object_permissions.set_project_object_permissions(object_id=object_id, project_id=project_id, permissions=Permissions.NONE)

    assert object_permissions.get_object_permissions_for_projects(object_id) == {}


def test_default_permissions_for_users(users, independent_action):
    user, creator = users

    # unless set otherwise, no user beside the creator (and instrument responsible users) will get initial permissions
    assert object_permissions.get_default_permissions_for_users(creator_id=creator.id) == {
        creator.id: Permissions.GRANT
    }
    object = sampledb.logic.objects.create_object(user_id=creator.id, action_id=independent_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    assert object_permissions.get_object_permissions_for_users(object_id=object.id, include_instrument_responsible_users=False, include_groups=False) == {
        creator.id: Permissions.GRANT
    }

    object_permissions.set_default_permissions_for_user(creator_id=creator.id, user_id=user.id, permissions=Permissions.READ)

    assert object_permissions.get_default_permissions_for_users(creator_id=creator.id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.READ
    }

    object = sampledb.logic.objects.create_object(user_id=creator.id, action_id=independent_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    assert object_permissions.get_object_permissions_for_users(object_id=object.id, include_instrument_responsible_users=False, include_groups=False) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.READ
    }

    # the default permissions are only used when creating a new object.
    object_permissions.set_default_permissions_for_user(creator_id=creator.id, user_id=user.id, permissions=Permissions.WRITE)

    assert object_permissions.get_default_permissions_for_users(creator_id=creator.id) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.WRITE
    }
    assert object_permissions.get_object_permissions_for_users(object_id=object.id, include_instrument_responsible_users=False, include_groups=False) == {
        creator.id: Permissions.GRANT,
        user.id: Permissions.READ
    }


def test_default_permissions_for_creator(users):
    user, creator = users

    assert object_permissions.get_default_permissions_for_users(creator_id=creator.id) == {
        creator.id: Permissions.GRANT
    }

    # the creator cannot receive less than GRANT default permissions
    with pytest.raises(object_permissions.InvalidDefaultPermissionsError):
        object_permissions.set_default_permissions_for_user(creator_id=creator.id, user_id=creator.id, permissions=Permissions.WRITE)

    # setting the creator's default permissions to GRANT does nothing, but is acceptable
    object_permissions.set_default_permissions_for_user(creator_id=creator.id, user_id=creator.id, permissions=Permissions.GRANT)
    assert object_permissions.get_default_permissions_for_users(creator_id=creator.id) == {
        creator.id: Permissions.GRANT
    }


def test_default_permissions_for_groups(users, independent_action):
    user, creator = users
    group_id = groups.create_group("Example Group", "", creator.id).id

    assert object_permissions.get_default_permissions_for_groups(creator_id=creator.id) == {}
    object = sampledb.logic.objects.create_object(user_id=creator.id, action_id=independent_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    assert object_permissions.get_object_permissions_for_groups(object_id=object.id) == {}

    object_permissions.set_default_permissions_for_group(creator_id=creator.id, group_id=group_id, permissions=Permissions.READ)

    assert object_permissions.get_default_permissions_for_groups(creator_id=creator.id) == {
        group_id: Permissions.READ
    }

    object = sampledb.logic.objects.create_object(user_id=creator.id, action_id=independent_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    assert object_permissions.get_object_permissions_for_groups(object_id=object.id) == {
        group_id: Permissions.READ
    }

    # the default permissions are only used when creating a new object.
    object_permissions.set_default_permissions_for_group(creator_id=creator.id, group_id=group_id, permissions=Permissions.WRITE)

    assert object_permissions.get_default_permissions_for_groups(creator_id=creator.id) == {
        group_id: Permissions.WRITE
    }
    assert object_permissions.get_object_permissions_for_groups(object_id=object.id) == {
        group_id: Permissions.READ
    }


def test_default_permissions_for_projects(users, independent_action):
    user, creator = users
    project_id = sampledb.logic.projects.create_project("Example Project", "", creator.id).id

    assert object_permissions.get_default_permissions_for_projects(creator_id=creator.id) == {}
    object = sampledb.logic.objects.create_object(user_id=creator.id, action_id=independent_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    assert object_permissions.get_object_permissions_for_projects(object_id=object.id) == {}

    object_permissions.set_default_permissions_for_project(creator_id=creator.id, project_id=project_id, permissions=Permissions.READ)

    assert object_permissions.get_default_permissions_for_projects(creator_id=creator.id) == {
        project_id: Permissions.READ
    }

    object = sampledb.logic.objects.create_object(user_id=creator.id, action_id=independent_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    assert object_permissions.get_object_permissions_for_projects(object_id=object.id) == {
        project_id: Permissions.READ
    }

    # the default permissions are only used when creating a new object.
    object_permissions.set_default_permissions_for_project(creator_id=creator.id, project_id=project_id, permissions=Permissions.WRITE)

    assert object_permissions.get_default_permissions_for_projects(creator_id=creator.id) == {
        project_id: Permissions.WRITE
    }
    assert object_permissions.get_object_permissions_for_projects(object_id=object.id) == {
        project_id: Permissions.READ
    }


def test_default_public_permissions(users, independent_action):
    user, creator = users

    assert not object_permissions.default_is_public(creator_id=creator.id)
    object = sampledb.logic.objects.create_object(user_id=creator.id, action_id=independent_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    assert not object_permissions.object_is_public(object_id=object.id)

    object_permissions.set_default_public(creator_id=creator.id, is_public=True)
    assert object_permissions.default_is_public(creator_id=creator.id)
    object = sampledb.logic.objects.create_object(user_id=creator.id, action_id=independent_action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    })
    assert object_permissions.object_is_public(object_id=object.id)

    object_permissions.set_default_public(creator_id=creator.id, is_public=False)
    assert not object_permissions.default_is_public(creator_id=creator.id)
    assert object_permissions.object_is_public(object_id=object.id)


def test_get_object_permissions_for_readonly_users(users, instrument, instrument_action_object):
    user_id = users[0].id
    object_id = instrument_action_object.object_id

    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.WRITE,
        users[1].id: Permissions.GRANT
    }
    sampledb.logic.users.set_user_readonly(user_id, readonly=True)
    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }

    instrument.responsible_users.append(users[0])
    sampledb.db.session.add(instrument)
    sampledb.db.session.commit()
    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.READ,
        users[1].id: Permissions.GRANT
    }
    sampledb.logic.users.set_user_readonly(user_id, readonly=False)
    assert object_permissions.get_object_permissions_for_users(object_id=object_id) == {
        user_id: Permissions.GRANT,
        users[1].id: Permissions.GRANT
    }


def test_get_readonly_user_object_permissions(user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.WRITE
    sampledb.logic.users.set_user_readonly(user_id, readonly=True)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    sampledb.logic.users.set_user_readonly(user_id, readonly=False)
    assert object_permissions.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.WRITE
