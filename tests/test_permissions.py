# coding: utf-8
"""

"""

import pytest
import sampledb
from sampledb.authentication import User, UserType
from sampledb.instruments import Action, Instrument
from sampledb.object_database import Objects
from sampledb.permissions import logic
from sampledb.permissions.models import Permissions, UserObjectPermissions, PublicObjects

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture(autouse=True)
def app_context():
    app = sampledb.create_app()
    with app.app_context():
        # fully empty the database first
        sampledb.db.MetaData(reflect=True, bind=sampledb.db.engine).drop_all()
        # recreate the tables used by this application
        sampledb.db.metadata.create_all(bind=sampledb.db.engine)
        yield app


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
        name='Example Action',
        schema={},
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
        name='Example Action',
        schema={},
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
    objects = [Objects.create_object(user_id=users[1].id, action_id=action.id, data={}, schema={}) for action in actions]
    return objects


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
    assert not logic.object_is_public(object_id)
    logic.set_object_public(object_id)
    assert logic.object_is_public(object_id)
    logic.set_object_public(object_id, False)
    assert not logic.object_is_public(object_id)


def test_default_user_object_permissions(user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE


def test_get_user_object_permissions(user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.WRITE


def test_get_instrument_responsible_user_object_permissions(user, instrument, instrument_action_object):
    user_id = user.id
    object_id = instrument_action_object.object_id
    instrument.responsible_users.append(user)
    sampledb.db.session.add(instrument)
    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.GRANT


def test_get_user_public_object_permissions(user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    logic.set_object_public(object_id)
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ


def test_get_object_permissions(user, instrument, instrument_action_object):
    user_id = user.id
    object_id = instrument_action_object.object_id
    assert logic.get_object_permissions(object_id=object_id) == {None: Permissions.NONE}
    logic.set_object_public(object_id)
    assert logic.get_object_permissions(object_id=object_id) == {None: Permissions.READ}
    sampledb.db.session.add(UserObjectPermissions(user_id=user_id, object_id=object_id, permissions=Permissions.WRITE))
    sampledb.db.session.commit()
    assert logic.get_object_permissions(object_id=object_id) == {
        None: Permissions.READ,
        user_id: Permissions.WRITE
    }
    instrument.responsible_users.append(user)
    sampledb.db.session.add(instrument)
    sampledb.db.session.commit()
    assert logic.get_object_permissions(object_id=object_id) == {
        None: Permissions.READ,
        user_id: Permissions.GRANT
    }


def test_update_object_permissions(user, independent_action_object):
    user_id = user.id
    object_id = independent_action_object.object_id
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    logic.set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=Permissions.WRITE)
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.WRITE
    logic.set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=Permissions.READ)
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.READ
    logic.set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=Permissions.NONE)
    assert logic.get_user_object_permissions(user_id=user_id, object_id=object_id) == Permissions.NONE
    assert logic.get_object_permissions(object_id=object_id) == {None: Permissions.NONE}