# coding: utf-8
"""

"""

import datetime

import jsonschema
import jsonschema.exceptions
import pytest
import sqlalchemy as db
import sqlalchemy.dialects.postgresql as postgresql
from sqlalchemy.orm import sessionmaker, declarative_base

import sampledb
import sampledb.utils
from sampledb.models.versioned_json_object_tables import VersionedJSONSerializableObjectTables, Object

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

Base = declarative_base()


class User(Base):
    __tablename__ = 'test_users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


class Action(Base):
    __tablename__ = 'test_actions'
    id = db.Column(db.Integer, primary_key=True)
    schema = db.Column(postgresql.JSONB)


@pytest.fixture
def engine():
    db_url = sampledb.config.SQLALCHEMY_DATABASE_URI
    engine = db.create_engine(db_url, **sampledb.config.SQLALCHEMY_ENGINE_OPTIONS)
    sampledb.utils.empty_database(engine, only_delete=False)
    return engine


@pytest.fixture
def session(engine):
    # create the user table
    Base.metadata.create_all(engine)

    Session = sessionmaker()
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def objects(engine):
    objects = VersionedJSONSerializableObjectTables(
        'test_objects',
        user_id_column=User.id,
        action_id_column=Action.id,
        action_schema_column=Action.schema,
        data_validator=lambda data, schema, component_id=None, allow_disabled_languages=False: jsonschema.validate(data, schema),
        schema_validator=lambda schema: jsonschema.Draft4Validator.check_schema(schema)
    )
    objects.bind = engine

    # create the object tables
    objects.metadata.create_all(engine)
    return objects


def test_create_object(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id, calculate_hashes=False)
    assert object1.version_id == 0
    assert object1.action_id == action.id
    assert object1.user_id is not None and object1.user_id == user.id
    assert object1.data == {}
    assert object1.schema == {}
    assert object1.utc_datetime < datetime.datetime.now(datetime.timezone.utc)
    assert object1.utc_datetime > datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=5)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)


def test_create_object_with_action_schema(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema=None, user_id=user.id, calculate_hashes=False)
    assert object1.version_id == 0
    assert object1.action_id == action.id
    assert object1.user_id is not None and object1.user_id == user.id
    assert object1.data == {}
    assert object1.schema == {}
    assert object1.utc_datetime < datetime.datetime.now(datetime.timezone.utc)
    assert object1.utc_datetime > datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=5)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)


def test_create_object_with_missing_action(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    session.commit()
    with pytest.raises(ValueError):
        objects.create_object(action_id=0, data={}, schema=None, user_id=user.id, calculate_hashes=False)


def test_update_object(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user1 = User(name="User 1")
    session.add(user1)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user1.id, calculate_hashes=False)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)
    user2 = User(name="User 2")
    session.add(user2)
    session.commit()
    object2 = objects.update_object(object1.object_id, data={'test': 1}, schema={}, user_id=user2.id, calculate_hashes=False)
    assert object2.object_id == object1.object_id
    assert object2.version_id == 1
    assert object2.user_id is not None and object2.user_id == user2.id
    assert object2.data == {'test': 1}
    assert object2.schema == {}
    assert object2.utc_datetime < datetime.datetime.now(datetime.timezone.utc)
    assert object2.utc_datetime > datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=5)
    assert [object2] == objects.get_current_objects()
    assert object2 == objects.get_current_object(object2.object_id)


def test_get_current_objects(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id, calculate_hashes=False)
    object2 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id, calculate_hashes=False)
    current_objects = objects.get_current_objects()
    assert current_objects == [object1, object2] or current_objects == [object2, object1]


def test_get_current_objects_action_filter(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action1 = Action(id=1, schema={'x': 1})
    action2 = Action(id=2, schema={})
    session.add(action1)
    session.add(action2)
    session.commit()
    object1 = objects.create_object(action_id=action1.id, data={}, schema={}, user_id=user.id, calculate_hashes=False)
    object2 = objects.create_object(action_id=action2.id, data={}, schema={}, user_id=user.id, calculate_hashes=False)

    current_objects = objects.get_current_objects(action_table=Action.__table__, action_filter=(Action.schema == {'x': 1}))
    assert current_objects == [object1]


def test_get_current_object(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id, calculate_hashes=False)
    object2 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id, calculate_hashes=False)
    assert object1 == objects.get_current_object(object1.object_id)
    assert object2 == objects.get_current_object(object2.object_id)


def test_get_object_versions(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user1 = User(name="User 1")
    session.add(user1)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user1.id, calculate_hashes=False)
    user2 = User(name="User 2")
    session.add(user2)
    session.commit()
    object2 = objects.update_object(object1.object_id, data={'test': 1}, schema={}, user_id=user2.id, calculate_hashes=False)
    object_versions = objects.get_object_versions(object1.object_id)
    assert object_versions == [object1, object2]


def test_get_object_versions_errors(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    object_versions = objects.get_object_versions(0)
    assert object_versions == []


def test_get_object_version(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user1 = User(name="User 1")
    session.add(user1)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user1.id, calculate_hashes=False)
    user2 = User(name="User 2")
    session.add(user2)
    session.commit()
    object2 = objects.update_object(object1.object_id, data={'test': 1}, schema={}, user_id=user2.id, calculate_hashes=False)
    object_version1 = objects.get_object_version(object1.object_id, 0)
    object_version2 = objects.get_object_version(object1.object_id, 1)
    object_version3 = objects.get_object_version(object1.object_id, 2)
    assert object_version1 == object1
    assert object_version2 == object2
    assert object_version3 is None


def test_create_object_invalid_schema(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    schema = {
        'type': 'invalid'
    }
    with pytest.raises(jsonschema.exceptions.SchemaError):
        objects.create_object(action_id=action.id, data={}, schema=schema, user_id=user.id, calculate_hashes=False)


def test_create_object_invalid_data(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    schema = {
        'type': 'object',
        'properties': {
            'test': {
                'type': 'integer'
            }
        }
    }
    with pytest.raises(jsonschema.exceptions.ValidationError):
        objects.create_object(action_id=action.id, data={'test': False}, schema=schema, user_id=user.id, calculate_hashes=False)


def test_update_object_invalid_schema(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(name="User 1")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id, calculate_hashes=False)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)
    schema = {
        'type': 'invalid'
    }
    with pytest.raises(jsonschema.exceptions.SchemaError):
        objects.update_object(object1.object_id, data={'test': 1}, schema=schema, user_id=user.id, calculate_hashes=False)


def test_update_object_invalid_data(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(name="User 1")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id, calculate_hashes=False)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)
    schema = {
        'type': 'object',
        'properties': {
            'test': {
                'type': 'integer'
            }
        }
    }
    with pytest.raises(jsonschema.exceptions.ValidationError):
        objects.update_object(object1.object_id, data={'test': '1'}, schema=schema, user_id=user.id, calculate_hashes=False)


def test_restore_object_version(engine, session: sessionmaker()) -> None:
    data_validator_calls = []

    def data_validator(*args, **kwargs):
        data_validator_calls.append((args, kwargs))
        return True

    schema_validator_calls = []

    def schema_validator(*args, **kwargs):
        schema_validator_calls.append((args, kwargs))
        return True

    objects = VersionedJSONSerializableObjectTables(
        'test_objects2',
        user_id_column=User.id,
        action_id_column=Action.id,
        action_schema_column=Action.schema,
        data_validator=data_validator,
        schema_validator=schema_validator
    )
    objects.bind = engine
    objects.metadata.create_all(engine)

    user = User(name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()

    object = objects.create_object(action_id=action.id, data={'d': 0}, schema={'s': 0}, user_id=user.id, calculate_hashes=False)
    assert data_validator_calls == [
        (({'d': 0}, {'s': 0}), {'allow_disabled_languages': False, 'component_id': None})
    ]
    assert schema_validator_calls == [
        (({'s': 0},), {})
    ]
    objects.update_object(object.object_id, data={'d': 1}, schema={'s': 1}, user_id=user.id, calculate_hashes=False)
    assert data_validator_calls == [
        (({'d': 0}, {'s': 0}), {'allow_disabled_languages': False, 'component_id': None}),
        (({'d': 1}, {'s': 1}), {'component_id': None})
    ]
    assert schema_validator_calls == [
        (({'s': 0},), {}),
        (({'s': 1},), {})
    ]
    objects.restore_object_version(object.object_id, version_id=0, user_id=user.id)
    assert data_validator_calls == [
        (({'d': 0}, {'s': 0}), {'allow_disabled_languages': False, 'component_id': None}),
        (({'d': 1}, {'s': 1}), {'component_id': None}),
        (({'d': 0}, {'s': 0}), {'allow_disabled_languages': True, 'component_id': None})
    ]
    assert schema_validator_calls == [
        (({'s': 0},), {}),
        (({'s': 1},), {}),
        (({'s': 0},), {})
    ]
    object = objects.get_current_object(object.object_id)
    assert object.data == {'d': 0}
    assert object.schema == {'s': 0}


def test_get_previous_subversion(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    v1_datetime = datetime.datetime.now(datetime.timezone.utc)
    v2_datetime = v1_datetime + datetime.timedelta(seconds=10)
    object = objects.create_object(action_id=None, data=None, schema=None, user_id=None, utc_datetime=v1_datetime, component_id=1, fed_object_id=1, fed_version_id=1, calculate_hashes=False)
    objects.update_object_version(object_id=object.object_id, version_id=object.version_id, action_id=None, data=None, schema=None, user_id=None, utc_datetime=v2_datetime, hash_metadata='')
    previous_subversion = objects.get_previous_subversion(object_id=object.object_id, version_id=object.version_id)
    assert previous_subversion is not None
    assert previous_subversion.utc_datetime == v1_datetime
