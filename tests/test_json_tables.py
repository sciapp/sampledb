# coding: utf-8
"""

"""

import datetime

import pytest
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import sampledb
from sampledb.object_database.versioned_json_object_tables import VersionedJSONSerializableObjectTables

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


class Object(VersionedJSONSerializableObjectTables.VersionedJSONSerializableObject):
    pass


@pytest.fixture
def engine():
    sampledb_app = sampledb.create_app()
    db_url = sampledb_app.config['SQLALCHEMY_DATABASE_URI']
    engine = db.create_engine(db_url, echo=False)

    # fully empty the database first
    db.MetaData(reflect=True, bind=engine).drop_all()
    return engine


@pytest.fixture
def session(engine):
    # create the user table
    Base.metadata.create_all(engine)

    Session = sessionmaker()
    session = Session(bind=engine)
    yield session
    session.close()


@pytest.fixture
def objects(engine):
    objects = VersionedJSONSerializableObjectTables(
        'objects', object_type=Object, user_id_column=User.id
    )
    objects.bind = engine

    # create the object tables
    objects.metadata.create_all(engine)
    return objects


def test_create_object(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    session.commit()
    object1 = objects.create_object({}, user_id=user.id)
    assert object1.version_id == 0
    assert object1.user_id is not None and object1.user_id == user.id
    assert object1.data == {}
    assert object1.utc_datetime < datetime.datetime.utcnow()
    assert object1.utc_datetime > datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)


def test_update_object(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user1 = User(name="User 1")
    session.add(user1)
    session.commit()
    object1 = objects.create_object({}, user_id=user1.id)
    assert [object1] == objects.get_current_objects()
    assert object1 == objects.get_current_object(object1.object_id)
    user2 = User(name="User 2")
    session.add(user2)
    session.commit()
    object2 = objects.update_object(object1.object_id, {'test': 1}, user2.id)
    assert object2.object_id == object1.object_id
    assert object2.version_id == 1
    assert object2.user_id is not None and object2.user_id == user2.id
    assert object2.data == {'test': 1}
    assert object2.utc_datetime < datetime.datetime.utcnow()
    assert object2.utc_datetime > datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    assert [object2] == objects.get_current_objects()
    assert object2 == objects.get_current_object(object2.object_id)


def test_get_current_objects(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    session.commit()
    object1 = objects.create_object({}, user_id=user.id)
    object2 = objects.create_object({}, user_id=user.id)
    current_objects = objects.get_current_objects()
    assert current_objects == [object1, object2] or current_objects == [object2, object1]


def test_get_current_object(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user = User(id=0, name="User")
    session.add(user)
    session.commit()
    object1 = objects.create_object({}, user_id=user.id)
    object2 = objects.create_object({}, user_id=user.id)
    assert object1 == objects.get_current_object(object1.object_id)
    assert object2 == objects.get_current_object(object2.object_id)


def test_get_object_versions(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user1 = User(name="User 1")
    session.add(user1)
    session.commit()
    object1 = objects.create_object({}, user_id=user1.id)
    user2 = User(name="User 2")
    session.add(user2)
    session.commit()
    object2 = objects.update_object(object1.object_id, {'test': 1}, user2.id)
    object_versions = objects.get_object_versions(object1.object_id)
    assert object_versions == [object1, object2]


def test_get_object_versions_errors(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    object_versions = objects.get_object_versions(0)
    assert object_versions == []


def test_get_object_version(session: sessionmaker(), objects: VersionedJSONSerializableObjectTables) -> None:
    user1 = User(name="User 1")
    session.add(user1)
    session.commit()
    object1 = objects.create_object({}, user_id=user1.id)
    user2 = User(name="User 2")
    session.add(user2)
    session.commit()
    object2 = objects.update_object(object1.object_id, {'test': 1}, user2.id)
    object_version1 = objects.get_object_version(object1.object_id, 0)
    object_version2 = objects.get_object_version(object1.object_id, 1)
    object_version3 = objects.get_object_version(object1.object_id, 2)
    assert object_version1 == object1
    assert object_version2 == object2
    assert object_version3 is None
