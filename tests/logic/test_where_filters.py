# coding: utf-8
"""

"""

import datetime
import json

import pytest
import sqlalchemy as db

import sampledb
import sampledb.utils
from sampledb.logic import datatypes, where_filters
from sampledb.models.versioned_json_object_tables import VersionedJSONSerializableObjectTables

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class Object(VersionedJSONSerializableObjectTables.VersionedJSONSerializableObject):
    pass


@pytest.fixture
def engine():
    sampledb_app = sampledb.create_app()
    db_url = sampledb_app.config['SQLALCHEMY_DATABASE_URI']
    engine = db.create_engine(
        db_url,
        echo=False,
        json_serializer=lambda obj: json.dumps(obj, cls=datatypes.JSONEncoder),
        json_deserializer=lambda obj: json.loads(obj, object_hook=datatypes.JSONEncoder.object_hook)
    )

    sampledb.utils.empty_database(engine)
    return engine


@pytest.fixture
def objects(engine):
    objects = VersionedJSONSerializableObjectTables(
        'objects', object_type=Object
    )
    objects.bind = engine

    # create the object tables
    objects.metadata.create_all(engine)
    return objects


def test_text_equals(objects):
    objects.create_object(action_id=0, data={'t': datatypes.Text("Beispiel")}, schema={}, user_id=0)
    object1 = objects.create_object(action_id=0, data={'t': datatypes.Text("Example")}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.text_equals(data['t'], 'Example'))


def test_text_contains(objects):
    objects.create_object(action_id=0, data={'t': datatypes.Text("Beispiel")}, schema={}, user_id=0)
    object1 = objects.create_object(action_id=0, data={'t': datatypes.Text("Example")}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.text_contains(data['t'], 'amp'))


def test_boolean_equals(objects):
    object1 = objects.create_object(action_id=0, data={'b': datatypes.Boolean(True)}, schema={}, user_id=0)
    object2 = objects.create_object(action_id=0, data={'b': datatypes.Boolean(False)}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.boolean_equals(data['b'], True))
    assert [object2] == objects.get_current_objects(lambda data: where_filters.boolean_equals(data['b'], False))


def test_boolean_true(objects):
    object1 = objects.create_object(action_id=0, data={'b': datatypes.Boolean(True)}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'b': datatypes.Boolean(False)}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.boolean_true(data['b']))


def test_boolean_false(objects):
    objects.create_object(action_id=0, data={'b': datatypes.Boolean(True)}, schema={}, user_id=0)
    object1 = objects.create_object(action_id=0, data={'b': datatypes.Boolean(False)}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.boolean_false(data['b']))


def test_quantity_equals(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'kilometer')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_equals(data['q'], datatypes.Quantity(100, 'centimeters')))


def test_quantity_equals_epsilon(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(10, 'mg')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(9.99, 'mg')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_equals(data['q'], datatypes.Quantity(0.00001, 'kg')))


def test_quantity_less_than(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'kilometer')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_less_than(data['q'], datatypes.Quantity(1.5, 'meters')))


def test_quantity_less_than_equals(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'kilometer')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_less_than_equals(data['q'], datatypes.Quantity(1, 'meter')))


def test_quantity_greater_than(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_greater_than(data['q'], datatypes.Quantity(0.5, 'meters')))


def test_quantity_greater_than_equals(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_greater_than_equals(data['q'], datatypes.Quantity(1, 'meter')))


def test_quantity_between(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(10, 'centimeters'), datatypes.Quantity(1, 'meter')))
    assert [] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(10, 'centimeters'), datatypes.Quantity(1, 'second')))


def test_quantity_between_excluding(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'centimeter')}, schema={}, user_id=0)
    assert [] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(10, 'centimeters'), datatypes.Quantity(1, 'meter'), including=False))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(10, 'centimeters'), datatypes.Quantity(1.1, 'meter'), including=False))


def test_datetime_equals(objects):
    utc_datetime = datetime.datetime.utcnow()
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime - datetime.timedelta(days=1))}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_equals(data['dt'], datatypes.DateTime(utc_datetime)))


def test_datetime_less_than(objects):
    utc_datetime = datetime.datetime.utcnow()
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    assert [] == objects.get_current_objects(lambda data: where_filters.datetime_less_than(data['dt'], datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_less_than(data['dt'], datatypes.DateTime(utc_datetime + datetime.timedelta(days=1))))


def test_datetime_less_than_equals(objects):
    utc_datetime = datetime.datetime.utcnow()
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_less_than_equals(data['dt'], datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_less_than_equals(data['dt'], datatypes.DateTime(utc_datetime + datetime.timedelta(seconds=1))))


def test_datetime_greater_than(objects):
    utc_datetime = datetime.datetime.utcnow()
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    assert [] == objects.get_current_objects(lambda data: where_filters.datetime_greater_than(data['dt'], datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_greater_than(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(days=1))))


def test_datetime_greater_than_equals(objects):
    utc_datetime = datetime.datetime.utcnow()
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_greater_than_equals(data['dt'], datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_greater_than_equals(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(seconds=1))))


def test_datetime_between(objects):
    utc_datetime = datetime.datetime.utcnow()
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime - datetime.timedelta(days=1))}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_between(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(seconds=1)), datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_between(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(seconds=1)), datatypes.DateTime(utc_datetime + datetime.timedelta(seconds=1))))


def test_datetime_between_excluding(objects):
    utc_datetime = datetime.datetime.utcnow()
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime - datetime.timedelta(days=1))}, schema={}, user_id=0)
    assert [] == objects.get_current_objects(lambda data: where_filters.datetime_between(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(days=1)), datatypes.DateTime(utc_datetime), including=False))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_between(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(days=1)), datatypes.DateTime(utc_datetime + datetime.timedelta(days=1)), including=False))


def test_sample_equals(objects):
    object1 = objects.create_object(action_id=0, data={}, schema={}, user_id=0)
    object2 = objects.create_object(action_id=0, data={'t': {'_type': 'sample', 'object_id': object1.object_id}}, schema={}, user_id=0)
    assert [object2] == objects.get_current_objects(lambda data: where_filters.sample_equals(data['t'], object1.object_id))
