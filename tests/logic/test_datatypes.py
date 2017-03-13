# coding: utf-8
"""

"""

import datetime
import json

import jsonschema
import jsonschema.exceptions
import pytest

from sampledb.logic import datatypes

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def test_strict_serialization_toplevel():
    datatypes.JSONEncoder.STRICT = True
    # _type as key should raise an AssertionError
    with pytest.raises(AssertionError):
        json.dumps({'_type': 'datetime'}, cls=datatypes.JSONEncoder)
    datatypes.JSONEncoder.STRICT = False


def test_strict_serialization_nested():
    datatypes.JSONEncoder.STRICT = True
    # _type as key should raise an AssertionError
    with pytest.raises(AssertionError):
        json.dumps({'test': {'_type': 'datetime'}}, cls=datatypes.JSONEncoder)
    datatypes.JSONEncoder.STRICT = False


def test_strict_serialization_valid():
    datatypes.JSONEncoder.STRICT = True
    # other keys with leading underscores are valid
    json.dumps({'_typ': 'datetime'}, cls=datatypes.JSONEncoder)
    datatypes.JSONEncoder.STRICT = False


def test_strict_serialization_filter_types():
    datatypes.JSONEncoder.STRICT = True
    # objects of serializable types will be ignored
    json.dumps({'length': datatypes.Quantity(10, 'meter')}, cls=datatypes.JSONEncoder)
    datatypes.JSONEncoder.STRICT = False


def test_strict_serialization_unknown_types():
    datatypes.JSONEncoder.STRICT = True
    # other objects will raise TypeError
    with pytest.raises(TypeError):
        json.dumps({'length': datatypes.ureg.Quantity(10, 'meter')}, cls=datatypes.JSONEncoder)
    datatypes.JSONEncoder.STRICT = False


def test_strict_serialization_lists():
    datatypes.JSONEncoder.STRICT = True
    # lists will work fine
    json.dumps({'numbers': [0, 1, 2]}, cls=datatypes.JSONEncoder)
    datatypes.JSONEncoder.STRICT = False


def test_serialization_unknown_types():
    # other objects will raise TypeError
    with pytest.raises(TypeError):
        json.dumps({'length': datatypes.ureg.Quantity(10, 'meter')}, cls=datatypes.JSONEncoder)


def test_quantity_serialization_unitless():
    # when using None as unit, it's a dimensionless quantity
    s = json.dumps(datatypes.Quantity(3.5, None), cls=datatypes.JSONEncoder)
    assert json.loads(s) == {
        '_type': 'quantity',
        'units': None,
        'magnitude_in_base_units': 3.5,
        'dimensionality': 'dimensionless'
    }


def test_quantity_serialization_units():
    # units passed as strings are kept as is, even though they might not be in the canonical form
    s = json.dumps(datatypes.Quantity(3.5, 'meters'), cls=datatypes.JSONEncoder)
    assert json.loads(s) == {
        '_type': 'quantity',
        'units': 'meters',
        'magnitude_in_base_units': 3.5,
        'dimensionality': '[length]'
    }


def test_quantity_serialization_string():
    # The magnitude may be passed as anything that can be converted to a float
    s = json.dumps(datatypes.Quantity("3.5", None), cls=datatypes.JSONEncoder)
    assert json.loads(s) == {
        '_type': 'quantity',
        'units': None,
        'magnitude_in_base_units': 3.5,
        'dimensionality': 'dimensionless'
    }


def test_quantity_serialization_string_invalid():
    with pytest.raises(ValueError):
        json.dumps(datatypes.Quantity("3.5m", None), cls=datatypes.JSONEncoder)


def test_quantity_serialization_units_pint():
    # any unit recognized by pint can be used
    s = json.dumps(datatypes.Quantity(3.5, datatypes.ureg.Unit("kilometers")), cls=datatypes.JSONEncoder)
    assert json.loads(s) == {
        '_type': 'quantity',
        'units': 'kilometer',
        'magnitude_in_base_units': 3500,
        'dimensionality': '[length]'
    }


def test_quantity_deserialization():
    s = json.dumps(datatypes.Quantity(3.5, 'meters'), cls=datatypes.JSONEncoder)
    quantity = json.loads(s, object_hook=datatypes.JSONEncoder.object_hook)
    assert quantity.units == 'meters'
    assert quantity.magnitude == 3.5
    assert quantity.pint_units == datatypes.ureg.Unit('meter')


def test_quantity_deserialization_unitless():
    # when using None as unit, it's a dimensionless quantity
    s = json.dumps(datatypes.Quantity(3.5, None), cls=datatypes.JSONEncoder)
    quantity = json.loads(s, object_hook=datatypes.JSONEncoder.object_hook)
    assert quantity.units == None
    assert quantity.magnitude == 3.5
    assert quantity.pint_units == datatypes.ureg.Unit('1')


def test_quantity_deserialization_non_base_units():
    # when using None as unit, it's a dimensionless quantity
    s = json.dumps(datatypes.Quantity(3.5, 'kilometers'), cls=datatypes.JSONEncoder)
    quantity = json.loads(s, object_hook=datatypes.JSONEncoder.object_hook)
    assert quantity.units == 'kilometers'
    assert quantity.magnitude == 3.5
    assert quantity.pint_units == datatypes.ureg.Unit('kilometers')


def test_quantity_equals():
    assert datatypes.Quantity(1, None) == datatypes.Quantity(1, None)
    assert datatypes.Quantity(1, None) != datatypes.Quantity(2, None)
    assert datatypes.Quantity(1, 'meter') == datatypes.Quantity(0.001, 'kilometers')
    assert datatypes.Quantity(1, 'meter') != datatypes.Quantity(1, 'second')


def test_quantity_invalid_value():
    with pytest.raises(ValueError):
        datatypes.Quantity(1, 'invalid')


def test_quantity_invalid_json():
    quantity = {
        '_type': 'quantity',
        'units': None,
        'magnitude_in_base_units': 1,
        'dimensionality': 'dimensionless'
    }
    json.loads(json.dumps(quantity), object_hook=datatypes.JSONEncoder.object_hook)
    quantity['units'] = 'invalid'
    with pytest.raises(ValueError):
        json.loads(json.dumps(quantity), object_hook=datatypes.JSONEncoder.object_hook)


def test_quantity_valid_data():
    schema = {
        'type': 'object',
        'properties': {
            'test': datatypes.Quantity.JSON_SCHEMA
        }
    }
    data = {'test': datatypes.Quantity(1, 'm')}
    raw_data = json.loads(json.dumps(data, cls=datatypes.JSONEncoder))
    jsonschema.validate(raw_data, schema)


def test_quantity_valid_data_dimensionless():
    schema = {
        'type': 'object',
        'properties': {
            'test': datatypes.Quantity.JSON_SCHEMA
        }
    }
    data = {'test': datatypes.Quantity(1, None)}
    raw_data = json.loads(json.dumps(data, cls=datatypes.JSONEncoder))
    jsonschema.validate(raw_data, schema)


def test_quantity_invalid_data():
    schema = {
        'type': 'object',
        'properties': {
            'test': datatypes.Quantity.JSON_SCHEMA
        }
    }
    data = {'test': 1}
    raw_data = json.loads(json.dumps(data, cls=datatypes.JSONEncoder))
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(raw_data, schema)


def test_datetime_serialization():
    utc_datetime = datetime.datetime.utcnow()
    s = json.dumps(datatypes.DateTime(utc_datetime), cls=datatypes.JSONEncoder)
    assert json.loads(s) == {
        '_type': 'datetime',
        'utc_datetime': utc_datetime.strftime(datatypes.DateTime.FORMAT_STRING)
    }


def test_datetime_deserialization():
    utc_datetime = datetime.datetime.utcnow()
    s = json.dumps(datatypes.DateTime(utc_datetime), cls=datatypes.JSONEncoder)
    dt = json.loads(s, object_hook=datatypes.JSONEncoder.object_hook)
    # The datetime objects are stored with a precision of 1 second
    assert abs(dt.utc_datetime - utc_datetime) < datetime.timedelta(seconds=1)


def test_datetime_equals():
    utc_datetime = datetime.datetime.utcnow()
    assert datatypes.DateTime(utc_datetime) == datatypes.DateTime(utc_datetime)
    assert datatypes.DateTime(utc_datetime) != datatypes.DateTime(utc_datetime + datetime.timedelta(days=1))


def test_datetime_valid_data():
    schema = {
        'type': 'object',
        'properties': {
            'test': datatypes.DateTime.JSON_SCHEMA
        }
    }
    data = {'test': datatypes.DateTime(datetime.datetime.utcnow())}
    raw_data = json.loads(json.dumps(data, cls=datatypes.JSONEncoder))
    jsonschema.validate(raw_data, schema)


def test_datetime_invalid_data():
    schema = {
        'type': 'object',
        'properties': {
            'test': datatypes.DateTime.JSON_SCHEMA
        }
    }
    data = {'test': "2017-02-24 16:26:00"}
    raw_data = json.loads(json.dumps(data, cls=datatypes.JSONEncoder))
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(raw_data, schema)


def test_boolean_serialization_true():
    s = json.dumps(datatypes.Boolean(True), cls=datatypes.JSONEncoder)
    assert json.loads(s) == {
        '_type': 'bool',
        'value': True
    }


def test_boolean_serialization_false():
    s = json.dumps(datatypes.Boolean(False), cls=datatypes.JSONEncoder)
    assert json.loads(s) == {
        '_type': 'bool',
        'value': False
    }


def test_boolean_deserialization():
    s = json.dumps(datatypes.Boolean(True), cls=datatypes.JSONEncoder)
    b = json.loads(s, object_hook=datatypes.JSONEncoder.object_hook)
    assert b.value


def test_boolean_equals():
    assert datatypes.Boolean(True) == datatypes.Boolean(True)
    assert datatypes.Boolean(True) != datatypes.Boolean(False)


def test_boolean_valid_data():
    schema = {
        'type': 'object',
        'properties': {
            'test': datatypes.Boolean.JSON_SCHEMA
        }
    }
    data = {'test': datatypes.Boolean(True)}
    raw_data = json.loads(json.dumps(data, cls=datatypes.JSONEncoder))
    jsonschema.validate(raw_data, schema)


def test_boolean_invalid_data():
    schema = {
        'type': 'object',
        'properties': {
            'test': datatypes.Boolean.JSON_SCHEMA
        }
    }
    data = {'test': True}
    raw_data = json.loads(json.dumps(data, cls=datatypes.JSONEncoder))
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(raw_data, schema)


def test_text_serialization():
    s = json.dumps(datatypes.Text("Test"), cls=datatypes.JSONEncoder)
    assert json.loads(s) == {
        '_type': 'text',
        'text': 'Test'
    }


def test_text_deserialization():
    s = json.dumps(datatypes.Text("Test"), cls=datatypes.JSONEncoder)
    t = json.loads(s, object_hook=datatypes.JSONEncoder.object_hook)
    assert t.text == "Test"


def test_text_equals():
    assert datatypes.Text("Test") == datatypes.Text("Test")
    assert datatypes.Text("Test") != datatypes.Text("ABCD")


def test_text_valid_data():
    schema = {
        'type': 'object',
        'properties': {
            'test': datatypes.Text.JSON_SCHEMA
        }
    }
    data = {'test': datatypes.Text("Example")}
    raw_data = json.loads(json.dumps(data, cls=datatypes.JSONEncoder))
    jsonschema.validate(raw_data, schema)


def test_text_invalid_data():
    schema = {
        'type': 'object',
        'properties': {
            'test': datatypes.Text.JSON_SCHEMA
        }
    }
    data = {'test': "Example"}
    raw_data = json.loads(json.dumps(data, cls=datatypes.JSONEncoder))
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(raw_data, schema)
