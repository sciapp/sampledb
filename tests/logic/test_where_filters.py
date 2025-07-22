# coding: utf-8
"""

"""

import datetime
import json

import flask
import pytest
import sqlalchemy as db

import sampledb
import sampledb.utils
from sampledb.logic import datatypes, where_filters, files
from sampledb.models.versioned_json_object_tables import VersionedJSONSerializableObjectTables, Object

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@pytest.fixture
def engine():
    sampledb_app = sampledb.create_app()
    db_url = sampledb_app.config['SQLALCHEMY_DATABASE_URI']
    engine = db.create_engine(
        db_url,
        echo=False,
        json_serializer=lambda obj: json.dumps(obj, cls=datatypes.JSONEncoder),
        json_deserializer=lambda obj: json.loads(obj, object_hook=datatypes.JSONEncoder.object_hook),
        **sampledb.config.SQLALCHEMY_ENGINE_OPTIONS
    )

    sampledb.utils.empty_database(engine, only_delete=False)
    return engine


@pytest.fixture
def objects(engine):
    objects = VersionedJSONSerializableObjectTables('objects')
    objects.bind = engine

    # create the object tables
    objects.metadata.create_all(engine)
    return objects


@pytest.fixture
def languages(engine):
    sampledb.models.Language.__table__.create(bind=engine)
    with engine.begin() as connection:
        query = db.text('''
            INSERT INTO languages
            (id, lang_code, names, datetime_format_datetime, datetime_format_moment, enabled_for_input)
            VALUES
            (:language_id, :lang_code, '{}', '', '', true)
        ''')
        connection.execute(query, {
            'language_id': sampledb.models.Language.ENGLISH,
            'lang_code': 'en'
        })
        connection.execute(query, {
            'language_id': sampledb.models.Language.GERMAN,
            'lang_code': 'de'
        })


def test_text_equals(objects, languages):
    objects.create_object(action_id=0, data={'t': datatypes.Text("Beispiel")}, schema={}, user_id=0)
    object1 = objects.create_object(action_id=0, data={'t': datatypes.Text("Example")}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.text_equals(data['t'], 'Example'))


def test_text_equals_multiple_languages(objects, languages):
    objects.create_object(action_id=0, data={'t': datatypes.Text("Beispiel")}, schema={}, user_id=0)
    object1 = objects.create_object(action_id=0, data={'t': datatypes.Text({'en': "Example", 'de': "Beispiel"})}, schema={}, user_id=0)
    assert len(objects.get_current_objects(lambda data: where_filters.text_equals(data['t'], 'Beispiel'))) == 2
    assert [object1] == objects.get_current_objects(lambda data: where_filters.text_equals(data['t'], 'Example'))


def test_text_contains(objects, languages):
    objects.create_object(action_id=0, data={'t': datatypes.Text("Beispiel")}, schema={}, user_id=0)
    object1 = objects.create_object(action_id=0, data={'t': datatypes.Text("Example")}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.text_contains(data['t'], 'amp'))


def test_text_contains_multiple_languages(objects, languages):
    objects.create_object(action_id=0, data={'t': datatypes.Text("Beispiel")}, schema={}, user_id=0)
    object1 = objects.create_object(action_id=0, data={'t': datatypes.Text({'en': "Example", 'de': "Beispiel"})}, schema={}, user_id=0)
    assert len(objects.get_current_objects(lambda data: where_filters.text_contains(data['t'], 'spiel'))) == 2
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

    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(-1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(-1, 'kilometer')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_equals(data['q'], datatypes.Quantity(-100, 'centimeters')))


def test_quantity_equals_epsilon(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(10, 'mg')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(9.99, 'mg')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_equals(data['q'], datatypes.Quantity(0.00001, 'kg')))

    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(-10, 'mg')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(-9.99, 'mg')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_equals(data['q'], datatypes.Quantity(-0.00001, 'kg')))


def test_quantity_less_than(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'kilometer')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_less_than(data['q'], datatypes.Quantity(1.5, 'meters')))

    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(-1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'kilometer')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_less_than(data['q'], datatypes.Quantity(-0.5, 'meters')))


def test_quantity_less_than_equals(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'kilometer')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_less_than_equals(data['q'], datatypes.Quantity(1, 'meter')))

    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(-1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'kilometer')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_less_than_equals(data['q'], datatypes.Quantity(-1, 'meter')))


def test_quantity_greater_than(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(-1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(-200, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_greater_than(data['q'], datatypes.Quantity(-1.5, 'meters')))

    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_greater_than(data['q'], datatypes.Quantity(0.5, 'meters')))


def test_quantity_greater_than_equals(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(-1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(-200, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_greater_than_equals(data['q'], datatypes.Quantity(-1, 'meter')))

    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_greater_than_equals(data['q'], datatypes.Quantity(1, 'meter')))


def test_quantity_between(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(10, 'centimeters'), datatypes.Quantity(1, 'meter')))
    assert [] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(10, 'centimeters'), datatypes.Quantity(1, 'second')))

    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(-1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(-1, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(-1, 'meter'), datatypes.Quantity(-10, 'centimeters')))


def test_quantity_between_excluding(objects):
    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(1, 'centimeter')}, schema={}, user_id=0)
    assert [] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(10, 'centimeters'), datatypes.Quantity(1, 'meter'), including=False))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(10, 'centimeters'), datatypes.Quantity(1.1, 'meter'), including=False))

    object1 = objects.create_object(action_id=0, data={'q': datatypes.Quantity(-1, 'meter')}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'q': datatypes.Quantity(-10, 'centimeter')}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(-1.1, 'meter'), datatypes.Quantity(-10, 'centimeters'), including=False))


def test_quantity_old_dimensionality(engine, objects):
    object1 = objects.create_object(
        action_id=0,
        data={
            "q": {
                "_type": "quantity",
                "magnitude": 1,
                "magnitude_in_base_units": 1,
                "units": "W",
                "dimensionality": "[length] ** 2 * [mass] / [time] ** 3"
            }
        },
        schema={},
        user_id=0
    )
    object2 = objects.create_object(
        action_id=0,
        data={
            "q": {
                "_type": "quantity",
                "magnitude": 1,
                "magnitude_in_base_units": 1,
                "units": "W",
                "dimensionality": "[mass] * [length] ** 2 / [time] ** 3"
            }
        },
        schema={},
        user_id=0
    )
    assert {object1.object_id, object2.object_id} == {object.object_id for object in objects.get_current_objects(lambda data: where_filters.quantity_equals(data['q'], datatypes.Quantity(1, 'W')))}
    assert {object1.object_id, object2.object_id} == {object.object_id for object in objects.get_current_objects(lambda data: where_filters.quantity_greater_than(data['q'], datatypes.Quantity(0.5, 'W')))}
    assert {object1.object_id, object2.object_id} == {object.object_id for object in objects.get_current_objects(lambda data: where_filters.quantity_greater_than_equals(data['q'], datatypes.Quantity(0.5, 'W')))}
    assert {object1.object_id, object2.object_id} == {object.object_id for object in objects.get_current_objects(lambda data: where_filters.quantity_less_than(data['q'], datatypes.Quantity(1.5, 'W')))}
    assert {object1.object_id, object2.object_id} == {object.object_id for object in objects.get_current_objects(lambda data: where_filters.quantity_less_than_equals(data['q'], datatypes.Quantity(1.5, 'W')))}
    assert {object1.object_id, object2.object_id} == {object.object_id for object in objects.get_current_objects(lambda data: where_filters.quantity_between(data['q'], datatypes.Quantity(0.5, 'W'),  datatypes.Quantity(1.5, 'W')))}


def test_datetime_equals(objects):
    utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime - datetime.timedelta(days=1))}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_equals(data['dt'], datatypes.DateTime(utc_datetime)))


def test_datetime_less_than(objects):
    utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    assert [] == objects.get_current_objects(lambda data: where_filters.datetime_less_than(data['dt'], datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_less_than(data['dt'], datatypes.DateTime(utc_datetime + datetime.timedelta(days=1))))


def test_datetime_less_than_equals(objects):
    utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_less_than_equals(data['dt'], datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_less_than_equals(data['dt'], datatypes.DateTime(utc_datetime + datetime.timedelta(seconds=1))))


def test_datetime_greater_than(objects):
    utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    assert [] == objects.get_current_objects(lambda data: where_filters.datetime_greater_than(data['dt'], datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_greater_than(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(days=1))))


def test_datetime_greater_than_equals(objects):
    utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_greater_than_equals(data['dt'], datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_greater_than_equals(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(seconds=1))))


def test_datetime_between(objects):
    utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime - datetime.timedelta(days=1))}, schema={}, user_id=0)
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_between(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(seconds=1)), datatypes.DateTime(utc_datetime)))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_between(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(seconds=1)), datatypes.DateTime(utc_datetime + datetime.timedelta(seconds=1))))


def test_datetime_between_excluding(objects):
    utc_datetime = datetime.datetime.now(datetime.timezone.utc)
    object1 = objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime)}, schema={}, user_id=0)
    objects.create_object(action_id=0, data={'dt': datatypes.DateTime(utc_datetime - datetime.timedelta(days=1))}, schema={}, user_id=0)
    assert [] == objects.get_current_objects(lambda data: where_filters.datetime_between(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(days=1)), datatypes.DateTime(utc_datetime), including=False))
    assert [object1] == objects.get_current_objects(lambda data: where_filters.datetime_between(data['dt'], datatypes.DateTime(utc_datetime - datetime.timedelta(days=1)), datatypes.DateTime(utc_datetime + datetime.timedelta(days=1)), including=False))


def test_sample_equals(objects):
    object1 = objects.create_object(action_id=0, data={}, schema={}, user_id=0)
    object2 = objects.create_object(action_id=0, data={'t': {'_type': 'sample', 'object_id': object1.object_id}}, schema={}, user_id=0)
    assert [object2] == objects.get_current_objects(lambda data: where_filters.sample_equals(data['t'], object1.object_id))


def test_reference_equals(objects):
    object1 = objects.create_object(action_id=0, data={}, schema={}, user_id=0)
    object2 = objects.create_object(action_id=0, data={'t': {'_type': 'sample', 'object_id': object1.object_id}}, schema={}, user_id=0)
    object3 = objects.create_object(action_id=0, data={'t': {'_type': 'measurement', 'object_id': object1.object_id}}, schema={}, user_id=0)
    object4 = objects.create_object(action_id=0, data={'t': {'_type': 'object_reference', 'object_id': object1.object_id}}, schema={}, user_id=0)
    object5 = objects.create_object(action_id=0, data={'t': {'_type': 'user', 'user_id': object1.object_id}}, schema={}, user_id=0)
    object6 = objects.create_object(action_id=0, data={'t': {'_type': 'object_reference', 'object_id': object1.object_id + 1}}, schema={}, user_id=0)
    object7 = objects.create_object(action_id=0, data={'t': {'_type': 'user', 'user_id': object1.object_id + 1}}, schema={}, user_id=0)
    found_objects = objects.get_current_objects(lambda data: where_filters.reference_equals(data['t'], object1.object_id))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {
        object2.id, object3.id, object4.id, object5.id
    }


def test_file_name_contains(flask_server):
    user = sampledb.logic.users.create_user(
        name="Test User",
        email="example@example.org",
        type=sampledb.logic.users.UserType.PERSON
    )
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema={
            "type": "object",
            "title": "Test Object",
            "properties": {
                "name": {
                    "type": "text",
                    "title": "Name"
                }
            },
            "required": ["name"]
        }
    )
    data = {
        "name": {
            "_type": "text",
            "text": "Name"
        }
    }
    flask.current_app.config['DOWNLOAD_SERVICE_WHITELIST'] = {'/test/': [user.id]}
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_url_file(object_id=object1.object_id, user_id=user.id, url="http://example.org/test/test")
    object2 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_url_file(object_id=object2.object_id, user_id=user.id, url="http://example.org/test/test2")
    object3 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_database_file(object_id=object3.object_id, user_id=user.id, file_name="test.txt", save_content=lambda stream: None)
    object4 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_database_file(object_id=object4.object_id, user_id=user.id, file_name="test2.txt", save_content=lambda stream: None)
    object5 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_local_file_reference(object_id=object5.object_id, user_id=user.id, filepath="/test/test.txt")
    object6 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_local_file_reference(object_id=object6.object_id, user_id=user.id, filepath="/test/test2.txt")
    object7 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_contains(data, "test2"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {
        object2.id, object4.id, object6.id
    }
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_contains(data, "/test/"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {
        object1.id, object2.id, object5.id, object6.id
    }
    sampledb.logic.files.hide_file(object_id=object1.id, file_id=0, user_id=user.id, reason='')
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_contains(data, "/test/"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {
        object2.id, object5.id, object6.id
    }
    sampledb.db.session.add(sampledb.models.FileLogEntry(object_id=object1.id, file_id=0, user_id=user.id, type=sampledb.models.FileLogEntryType.UNHIDE_FILE, data={}))
    sampledb.db.session.commit()
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_contains(data, "/test/"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {
        object1.id, object2.id, object5.id, object6.id
    }

    files.create_url_file(object_id=object2.object_id, user_id=user.id, url="http://example.org/test/test2")
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_contains(data, "http://example.org/test/test2"))
    found_object_ids = [
        object.id
        for object in found_objects
    ]
    assert found_object_ids == [object2.id]


def test_file_name_equals(flask_server):
    user = sampledb.logic.users.create_user(
        name="Test User",
        email="example@example.org",
        type=sampledb.logic.users.UserType.PERSON
    )
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema={
            "type": "object",
            "title": "Test Object",
            "properties": {
                "name": {
                    "type": "text",
                    "title": "Name"
                }
            },
            "required": ["name"]
        }
    )
    data = {
        "name": {
            "_type": "text",
            "text": "Name"
        }
    }
    flask.current_app.config['DOWNLOAD_SERVICE_WHITELIST'] = {'/test/': [user.id]}
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_url_file(object_id=object1.object_id, user_id=user.id, url="http://example.org/test/test")
    object2 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_url_file(object_id=object2.object_id, user_id=user.id, url="http://example.org/test/test2")
    object3 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_database_file(object_id=object3.object_id, user_id=user.id, file_name="test.txt", save_content=lambda stream: None)
    object4 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_database_file(object_id=object4.object_id, user_id=user.id, file_name="test2.txt", save_content=lambda stream: None)
    object5 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_local_file_reference(object_id=object5.object_id, user_id=user.id, filepath="/test/test.txt")
    object6 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    files.create_local_file_reference(object_id=object6.object_id, user_id=user.id, filepath="/test/test2.txt")
    object7 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_equals(data, "http://example.org/test/test"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {object1.id}
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_equals(data, "test.txt"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {object3.id}
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_equals(data, "/test/test.txt"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {object5.id}
    sampledb.logic.files.hide_file(object_id=object1.id, file_id=0, user_id=user.id, reason='')
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_equals(data, "http://example.org/test/test"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert not found_object_ids
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_equals(data, "test.txt"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {object3.id}
    sampledb.db.session.add(sampledb.models.FileLogEntry(object_id=object1.id, file_id=0, user_id=user.id, type=sampledb.models.FileLogEntryType.UNHIDE_FILE, data={}))
    sampledb.db.session.commit()
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_equals(data, "http://example.org/test/test"))
    found_object_ids = {
        object.id
        for object in found_objects
    }
    assert found_object_ids == {object1.id}

    files.create_url_file(object_id=object1.object_id, user_id=user.id, url="http://example.org/test/test")
    found_objects = sampledb.models.objects.Objects.get_current_objects(lambda data: where_filters.file_name_equals(data, "http://example.org/test/test"))
    found_object_ids = [
        object.id
        for object in found_objects
    ]
    assert found_object_ids == [object1.id]
