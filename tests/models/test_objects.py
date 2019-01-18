# coding: utf-8
"""

"""

import datetime

import jsonschema
import jsonschema.exceptions
import pytest
import sqlalchemy as db
import sqlalchemy.dialects.postgresql as postgresql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import sampledb
import sampledb.utils
from sampledb.models.versioned_json_object_tables import VersionedJSONSerializableObjectTables

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


class Action(Base):
    __tablename__ = 'actions'
    id = db.Column(db.Integer, primary_key=True)
    schema = db.Column(postgresql.JSONB)


class Object(VersionedJSONSerializableObjectTables.VersionedJSONSerializableObject):
    pass


@pytest.fixture
def engine():
    db_url = sampledb.config.SQLALCHEMY_DATABASE_URI
    engine = db.create_engine(db_url)
    sampledb.utils.empty_database(engine)
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
        'objects',
        object_type=Object,
        user_id_column=User.id,
        action_id_column=Action.id,
        action_schema_column=Action.schema,
        data_validator=lambda data, schema: jsonschema.validate(data, schema),
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
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id)
    assert object1.version_id == 0
    assert object1.action_id == action.id
    assert object1.user_id is not None and object1.user_id == user.id
    assert object1.data == {}
    assert object1.schema == {}
    assert object1.utc_datetime < datetime.datetime.utcnow()
    assert object1.utc_datetime > datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)


def test_create_object_with_action_schema(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema=None, user_id=user.id)
    assert object1.version_id == 0
    assert object1.action_id == action.id
    assert object1.user_id is not None and object1.user_id == user.id
    assert object1.data == {}
    assert object1.schema == {}
    assert object1.utc_datetime < datetime.datetime.utcnow()
    assert object1.utc_datetime > datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)


def test_create_object_with_missing_action(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    session.commit()
    with pytest.raises(ValueError):
        objects.create_object(action_id=0, data={}, schema=None, user_id=user.id)


def test_update_object(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user1 = User(name="User 1")
    session.add(user1)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user1.id)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)
    user2 = User(name="User 2")
    session.add(user2)
    session.commit()
    object2 = objects.update_object(object1.object_id, data={'test': 1}, schema={}, user_id=user2.id)
    assert object2.object_id == object1.object_id
    assert object2.version_id == 1
    assert object2.user_id is not None and object2.user_id == user2.id
    assert object2.data == {'test': 1}
    assert object2.schema == {}
    assert object2.utc_datetime < datetime.datetime.utcnow()
    assert object2.utc_datetime > datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    assert [object2] == objects.get_current_objects()
    assert object2 == objects.get_current_object(object2.object_id)


def test_get_current_objects(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id)
    object2 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id)
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
    object1 = objects.create_object(action_id=action1.id, data={}, schema={}, user_id=user.id)
    object2 = objects.create_object(action_id=action2.id, data={}, schema={}, user_id=user.id)

    current_objects = objects.get_current_objects(action_table=Action.__table__, action_filter=(Action.schema == {'x': 1}))
    assert current_objects == [object1]


def test_get_current_object(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id)
    object2 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id)
    assert object1 == objects.get_current_object(object1.object_id)
    assert object2 == objects.get_current_object(object2.object_id)


def test_get_object_versions(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user1 = User(name="User 1")
    session.add(user1)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user1.id)
    user2 = User(name="User 2")
    session.add(user2)
    session.commit()
    object2 = objects.update_object(object1.object_id, data={'test': 1}, schema={}, user_id=user2.id)
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
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user1.id)
    user2 = User(name="User 2")
    session.add(user2)
    session.commit()
    object2 = objects.update_object(object1.object_id, data={'test': 1}, schema={}, user_id=user2.id)
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
        objects.create_object(action_id=action.id, data={}, schema=schema, user_id=user.id)


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
        objects.create_object(action_id=action.id, data={'test': False}, schema=schema, user_id=user.id)


def test_update_object_invalid_schema(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(name="User 1")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)
    schema = {
        'type': 'invalid'
    }
    with pytest.raises(jsonschema.exceptions.SchemaError):
        objects.update_object(object1.object_id, data={'test': 1}, schema=schema, user_id=user.id)


def test_update_object_invalid_data(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(name="User 1")
    session.add(user)
    action = Action(id=0, schema={})
    session.add(action)
    session.commit()
    object1 = objects.create_object(action_id=action.id, data={}, schema={}, user_id=user.id)
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
        objects.update_object(object1.object_id, data={'test': '1'}, schema=schema, user_id=user.id)
