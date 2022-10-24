import datetime

import pytest

import sampledb.models
import sampledb.logic
from sampledb import db
from sampledb.logic import errors
from sampledb.logic.components import add_component
from sampledb.logic.users import create_user_alias, get_user_alias, get_user_aliases_for_user, update_user_alias, \
    get_user_aliases_for_component
from sampledb.models import User, UserType, UserFederationAlias

UUID_1 = '28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71'
UUID_2 = '1e59c517-bd11-4390-aeb4-971f20b06612'


@pytest.fixture
def user(flask_server):
    with flask_server.app.app_context():
        user = sampledb.models.User(name="Basic User", email="example@example.com", type=sampledb.models.UserType.PERSON)
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        # force attribute refresh
        assert user.id is not None
    return sampledb.logic.users.User.from_database(user)


@pytest.fixture
def component():
    component = add_component(address=None, uuid=UUID_1, name='Example component', description='')
    return component


def test_get_users_by_name():
    user1 = sampledb.logic.users.create_user(
        name="User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )
    user2 = sampledb.logic.users.create_user(
        name="User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )

    users = sampledb.logic.users.get_users_by_name("User")
    assert len(users) == 2
    assert user1 in users
    assert user2 in users

    sampledb.logic.users.update_user(
        user2.id, None, name="Test-User"
    )
    user2 = sampledb.logic.users.get_user(user2.id)

    users = sampledb.logic.users.get_users_by_name("User")
    assert len(users) == 1
    assert user1 in users
    assert user2 not in users


def test_get_users_exclude_hidden():
    user1 = sampledb.logic.users.create_user(
        name="User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )
    user2 = sampledb.logic.users.create_user(
        name="User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON
    )

    users = sampledb.logic.users.get_users()
    users.sort(key=lambda u: u.id)
    assert users == [user1, user2]

    sampledb.logic.users.set_user_hidden(user1.id, True)
    user1 = sampledb.logic.users.get_user(user1.id)

    users = sampledb.logic.users.get_users()
    users.sort(key=lambda u: u.id)
    assert users == [user1, user2]

    users = sampledb.logic.users.get_users(exclude_hidden=True)
    users.sort(key=lambda u: u.id)
    assert users == [user2]


def test_set_user_hidden(user):
    user = sampledb.logic.users.get_user(user.id)
    assert not user.is_hidden
    sampledb.logic.users.set_user_hidden(user.id, True)
    user = sampledb.logic.users.get_user(user.id)
    assert user.is_hidden
    sampledb.logic.users.set_user_hidden(user.id, False)
    user = sampledb.logic.users.get_user(user.id)
    assert not user.is_hidden


def test_set_user_readonly(user):
    user = sampledb.logic.users.get_user(user.id)
    assert not user.is_readonly
    sampledb.logic.users.set_user_readonly(user.id, True)
    user = sampledb.logic.users.get_user(user.id)
    assert user.is_readonly
    sampledb.logic.users.set_user_readonly(user.id, False)
    user = sampledb.logic.users.get_user(user.id)
    assert not user.is_readonly


def test_set_user_administrator(user):
    user = sampledb.logic.users.get_user(user.id)
    assert not user.is_admin
    sampledb.logic.users.set_user_administrator(user.id, True)
    user = sampledb.logic.users.get_user(user.id)
    assert user.is_admin
    sampledb.logic.users.set_user_administrator(user.id, False)
    user = sampledb.logic.users.get_user(user.id)
    assert not user.is_admin


def test_create_user():
    assert len(User.query.all()) == 0
    ts = datetime.datetime.utcnow()
    user = sampledb.logic.users.create_user(name='User', email='user@example.com', type=UserType.PERSON)
    assert ts <= user.last_modified <= datetime.datetime.utcnow()
    assert len(User.query.all()) == 1
    assert user.name == 'User'
    assert user.email == 'user@example.com'


def test_update_user():
    user = sampledb.logic.users.create_user(name='User', email='user@example.com', type=UserType.PERSON)
    assert len(User.query.all()) == 1
    ts = datetime.datetime.utcnow()
    sampledb.logic.users.update_user(user.id, name='Updated User', email='up.user@example.com', updating_user_id=user.id)
    user = sampledb.logic.users.get_user(user.id)
    assert ts <= user.last_modified <= datetime.datetime.utcnow()
    assert len(User.query.all()) == 1
    assert user.name == 'Updated User'
    assert user.email == 'up.user@example.com'
    previous_last_modified = user.last_modified
    sampledb.logic.users.update_user(user.id, name='Updated User 2', email='up.user2@example.com', updating_user_id=None)
    user = sampledb.logic.users.get_user(user.id)
    assert user.last_modified == previous_last_modified
    assert len(User.query.all()) == 1
    assert user.name == 'Updated User 2'
    assert user.email == 'up.user2@example.com'


def test_create_user_fed(component):
    assert len(User.query.all()) == 0
    ts = datetime.datetime.utcnow()
    user = sampledb.logic.users.create_user(name='User', email='user@example.com', fed_id=1, component_id=component.id, type=UserType.FEDERATION_USER)
    assert ts <= user.last_modified <= datetime.datetime.utcnow()
    assert len(User.query.all()) == 1
    assert user.name == 'User'
    assert user.email == 'user@example.com'
    assert user.fed_id == 1
    assert user.component_id == component.id
    ts = datetime.datetime.utcnow()
    user = sampledb.logic.users.create_user(name=None, email=None, fed_id=2, component_id=component.id, affiliation='Scientific IT Systems', type=UserType.FEDERATION_USER)
    assert ts <= user.last_modified <= datetime.datetime.utcnow()
    assert len(User.query.all()) == 2
    assert user.name is None
    assert user.email is None
    assert user.affiliation =='Scientific IT Systems'
    assert user.fed_id == 2
    assert user.component_id == component.id


def test_create_user_exceptions(component):
    assert len(User.query.all()) == 0
    with pytest.raises(TypeError):
        sampledb.logic.users.create_user(name=None, email=None, fed_id=1, type=UserType.FEDERATION_USER)
    with pytest.raises(TypeError):
        sampledb.logic.users.create_user(name=None, email=None, component_id=component.id, type=UserType.FEDERATION_USER)
    with pytest.raises(TypeError):
        sampledb.logic.users.create_user(name='User', email=None, type=UserType.FEDERATION_USER)
    with pytest.raises(TypeError):
        sampledb.logic.users.create_user(name=None, email='user@example.com', type=UserType.FEDERATION_USER)
    with pytest.raises(errors.ComponentDoesNotExistError):
        sampledb.logic.users.create_user(name=None, email=None, fed_id=1, component_id=component.id + 1, type=UserType.FEDERATION_USER)
    assert len(User.query.all()) == 0


def test_get_user_fed(component):
    user_created = sampledb.logic.users.create_user(name=None, email=None, fed_id=1, component_id=component.id, type=UserType.FEDERATION_USER)
    user = sampledb.logic.users.get_user(1, component.id)
    assert user_created == user


def test_get_user_exceptions(component):
    with pytest.raises(errors.UserDoesNotExistError):
        sampledb.logic.users.get_user(1)
    with pytest.raises(errors.UserDoesNotExistError):
        sampledb.logic.users.get_user(1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        sampledb.logic.users.get_user(1, component.id + 1)


def test_create_user_alias(component, user):
    assert len(UserFederationAlias.query.all()) == 0
    utc_datetime_before = datetime.datetime.utcnow()
    alias = create_user_alias(user.id, component.id, 'Testuser', False, 'test@example.com', False, None, False, None, False, None, True)
    assert alias.last_modified >= utc_datetime_before
    assert alias.last_modified <= datetime.datetime.utcnow()
    assert len(UserFederationAlias.query.all()) == 1
    assert alias.user_id == user.id
    assert alias.component_id == component.id
    assert alias.name == 'Testuser'
    assert alias.use_real_name is False
    assert alias.email == 'test@example.com'
    assert alias.use_real_email is False
    assert alias.orcid is None
    assert alias.use_real_orcid is False
    assert alias.affiliation is None
    assert alias.use_real_affiliation is False
    assert alias.role is None
    assert alias.use_real_role is True
    with pytest.raises(errors.UserAliasAlreadyExistsError):
        create_user_alias(user.id, component.id, 'Testuser', False, 'test@example.com', False, None, False, None, False, None, True)


def test_get_user_alias(component, user):
    with pytest.raises(errors.UserAliasDoesNotExistError):
        get_user_alias(user.id, component.id)
    with pytest.raises(errors.UserDoesNotExistError):
        get_user_alias(user.id + 1, component.id)
    with pytest.raises(errors.ComponentDoesNotExistError):
        get_user_alias(user.id, component.id + 1)
    utc_datetime_before = datetime.datetime.utcnow()
    created_alias = create_user_alias(user.id, component.id, 'Testuser', False, 'test@example.com', False, None, False, None, False, None, False)
    alias = get_user_alias(user.id, component.id)
    assert alias.last_modified >= utc_datetime_before
    assert alias.last_modified <= datetime.datetime.utcnow()
    assert alias.user_id == created_alias.user_id
    assert alias.component_id == created_alias.component_id
    assert alias.name == created_alias.name
    assert alias.email == created_alias.email
    assert alias.orcid == created_alias.orcid
    assert alias.affiliation == created_alias.affiliation
    assert alias.role == created_alias.role


def test_get_user_aliases_for_user():
    component1 = add_component(address=None, uuid=UUID_1, name='Example component 1', description='')
    component2 = add_component(address=None, uuid=UUID_2, name='Example component 2', description='')
    user1 = sampledb.models.User(name="Basic User 1", email="example1@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user1)
    sampledb.db.session.commit()
    user2 = sampledb.models.User(name="Basic User 2", email="example2@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()
    alias_user1_component1 = create_user_alias(user1.id, component1.id, 'B. User 1', False, None, False, None, False, None, False, None, False)
    alias_user1_component2 = create_user_alias(user1.id, component2.id, None, False, None, False, None, False, None, False, None, False)
    alias_user2_component1 = create_user_alias(user2.id, component1.id, 'B. User 2', False, None, False, None, False, None, False, None, False)
    alias_user2_component2 = create_user_alias(user2.id, component2.id, 'B. User 2', False, 'contact@example.com', False, None, False, None, False, None, False)
    user_aliases = get_user_aliases_for_user(user1.id)
    assert alias_user1_component1 in user_aliases
    assert alias_user1_component2 in user_aliases
    assert len(user_aliases) == 2
    user_aliases = get_user_aliases_for_user(user2.id)
    assert alias_user2_component1 in user_aliases
    assert alias_user2_component2 in user_aliases
    assert len(user_aliases) == 2
    with pytest.raises(errors.UserDoesNotExistError):
        get_user_aliases_for_user(user2.id + 1)


def test_update_user_alias(component, user):
    with pytest.raises(errors.UserAliasDoesNotExistError):
        update_user_alias(user.id, component.id, 'User', False, 'contact@example.com', False, None, False, 'Company ltd.', False, 'Scientist', False)
    create_user_alias(user.id, component.id, 'Testuser', False, 'test@example.com', False, None, False, None, False, None, False)
    utc_datetime_before = datetime.datetime.utcnow()
    update_user_alias(user.id, component.id, 'User', False, 'contact@example.com', False, None, False, 'Company ltd.', False, 'Scientist', False)
    alias = get_user_alias(user.id, component.id)
    assert alias.last_modified >= utc_datetime_before
    assert alias.last_modified <= datetime.datetime.utcnow()
    assert alias.user_id == user.id
    assert alias.component_id == component.id
    assert alias.name == 'User'
    assert alias.email == 'contact@example.com'
    assert alias.orcid is None
    assert alias.affiliation == 'Company ltd.'
    assert alias.role == 'Scientist'
    with pytest.raises(errors.UserDoesNotExistError):
        update_user_alias(user.id + 1, component.id, 'User', False, 'contact@example.com', False, None, False, 'Company ltd.', False, 'Scientist', False)
    with pytest.raises(errors.ComponentDoesNotExistError):
        update_user_alias(user.id, component.id + 1, 'User', False, 'contact@example.com', False, None, False, 'Company ltd.', False, 'Scientist', False)


def test_get_user_aliases_for_component():
    component1 = add_component(address=None, uuid=UUID_1, name='Example component 1', description='')
    component2 = add_component(address=None, uuid=UUID_2, name='Example component 2', description='')
    user1 = sampledb.models.User(name="Basic User 1", email="example1@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user1)
    sampledb.db.session.commit()
    user2 = sampledb.models.User(name="Basic User 2", email="example2@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()
    ts1 = datetime.datetime.utcnow()
    alias_user1_component1 = create_user_alias(user1.id, component1.id, 'B. User 1', False, None, False, None, False, None, False, None, False)
    alias_user1_component2 = create_user_alias(user1.id, component2.id, None, False, None, False, None, False, None, False, None, False)
    ts2 = datetime.datetime.utcnow()
    alias_user2_component1 = create_user_alias(user2.id, component1.id, 'B. User 2', False, None, False, None, False, None, False, None, False)
    alias_user2_component2 = create_user_alias(user2.id, component2.id, 'B. User 2', False, 'contact@example.com', False, None, False, None, False, None, False)
    ts3 = datetime.datetime.utcnow()
    user_aliases = get_user_aliases_for_component(component1.id)
    assert alias_user1_component1 in user_aliases
    assert alias_user2_component1 in user_aliases
    assert len(user_aliases) == 2
    user_aliases = get_user_aliases_for_component(component2.id)
    assert alias_user1_component2 in user_aliases
    assert alias_user2_component2 in user_aliases
    assert len(user_aliases) == 2
    with pytest.raises(errors.ComponentDoesNotExistError):
        get_user_aliases_for_component(component2.id + 1)

    user_aliases = get_user_aliases_for_component(component1.id, modified_since=ts1)
    assert alias_user1_component1 in user_aliases
    assert alias_user2_component1 in user_aliases
    assert len(user_aliases) == 2
    user_aliases = get_user_aliases_for_component(component1.id, modified_since=ts2)
    assert alias_user2_component1 in user_aliases
    assert len(user_aliases) == 1
    user_aliases = get_user_aliases_for_component(component1.id, modified_since=ts3)
    assert len(user_aliases) == 0


def test_get_user_aliases_for_component_use_real_data():
    component = add_component(address=None, uuid=UUID_1, name='Example component 1', description='')
    user1 = sampledb.models.User(name="Basic User 1", email="example1@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user1)
    sampledb.db.session.commit()
    user2 = sampledb.models.User(name="Basic User 2", email="example2@example.com", type=sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user2)
    sampledb.db.session.commit()
    ts1 = datetime.datetime.utcnow()
    alias_user1 = create_user_alias(user1.id, component.id, None, True, None, False, None, False, None, False, None, False)
    ts2 = datetime.datetime.utcnow()
    alias_user2 = create_user_alias(user2.id, component.id, 'B. User 2', False, None, False, None, False, None, False, None, False)
    ts3 = datetime.datetime.utcnow()

    user_aliases = get_user_aliases_for_component(component.id, modified_since=ts1)
    assert alias_user1 in user_aliases
    assert alias_user2 in user_aliases
    assert len(user_aliases) == 2
    user_aliases = get_user_aliases_for_component(component.id, modified_since=ts2)
    assert alias_user2 in user_aliases
    assert len(user_aliases) == 1
    user_aliases = get_user_aliases_for_component(component.id, modified_since=ts3)
    assert len(user_aliases) == 0

    ts4 = datetime.datetime.utcnow()
    sampledb.logic.users.update_user(user1.id, name='User Name', updating_user_id=user1.id)
    sampledb.logic.users.update_user(user2.id, email='user@example.com', updating_user_id=user1.id)    # not using real data -> ignore profile update
    user_aliases = get_user_aliases_for_component(component.id, modified_since=ts4)
    alias_user1 = get_user_alias(user1.id, component.id)
    assert alias_user1.name == 'User Name'
    assert alias_user1 in user_aliases
    assert len(user_aliases) == 1
