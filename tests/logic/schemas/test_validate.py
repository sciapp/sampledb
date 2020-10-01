# coding: utf-8
"""

"""
import datetime
import pytest

import sampledb
import sqlalchemy as db
from sampledb.logic.objects import create_object, get_object
from sampledb.logic.schemas import validate
from sampledb.logic.errors import ValidationError


def test_validate_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'str'
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_missing_type():
    schema = {
        'title': 'Example',
        '_type': 'text'
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_invalid_schema_type():
    schema = [{
        'title': 'Example',
        'type': 'text'
    }]
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_invalid_instance_type():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = None
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    validate(instance, schema)


def test_validate_text_invalid():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_missing_key():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'text'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'text',
        'text': 'test',
        'locale': 'en_US'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_choices():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': ["A", "B", "C"]
    }
    instance = {
        '_type': 'text',
        'text': 'B'
    }
    validate(instance, schema)


def test_validate_text_invalid_choice():
    schema = {
        'title': 'Example',
        'type': 'text',
        'choices': ['A', 'B', 'C']
    }
    instance = {
        '_type': 'text',
        'text': 'D'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_pattern():
    schema = {
        'title': 'Example',
        'type': 'text',
        'pattern': '^[1-9][0-9]*/[A-Za-z]+'
    }
    instance = {
        '_type': 'text',
        'text': '42/Test'
    }
    validate(instance, schema)


def test_validate_text_pattern_mismatch():
    schema = {
        'title': 'Example',
        'type': 'text',
        'pattern': '[1-9][0-9]*/[A-Za-z]+'
    }
    instance = {
        '_type': 'text',
        'text': '02/Test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 1
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    validate(instance, schema)


def test_validate_text_invalid_min_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'minLength': 10
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': 10
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    validate(instance, schema)


def test_validate_text_invalid_max_length():
    schema = {
        'title': 'Example',
        'type': 'text',
        'maxLength': 1
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_invalid_text_type():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'text',
        'text': b'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_text_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'text'
    }
    instance = {
        '_type': 'str',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'bool',
        'value': True
    }
    validate(instance, schema)


def test_validate_bool_invalid():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool_missing_key():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'bool'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'bool',
        'value': True,
        'default': True
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool_invalid_bool_type():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'bool',
        'value': 'True'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_bool_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'bool'
    }
    instance = {
        '_type': 'boolean',
        'value': True
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1e-3
    }
    validate(instance, schema)


def test_validate_quantity_invalid():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_missing_key():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'magnitude_in_base_units': 1e-3
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1e-3,
        'default': True
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_quantity_dimensionality_type():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'dimensionality': b'[length]',
        'magnitude_in_base_units': 1e-3
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_quantity_units_type():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    instance = {
        '_type': 'quantity',
        'units': b'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1e-3
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_quantity_magnitude_type():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    instance = {
        '_type': 'quantity',
        'units': 'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': '1e-3'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_quantity_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'quantity',
        'units': 'm'
    }
    instance = {
        '_type': 'Quantity',
        'units': 'm',
        'dimensionality': '[length]',
        'magnitude_in_base_units': 1e-3
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime',
        'utc_datetime': '2017-03-31 10:20:30'
    }
    validate(instance, schema)


def test_validate_datetime_invalid_datetime():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime',
        'utc_datetime': '2017-03-31 10:20:65'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_invalid():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_missing_key():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_invalid_key():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime',
        'utc_datetime': '2017-03-31 10:20:30',
        'timezone': 'UTC+2'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_invalid_datetime_type():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'datetime',
        'utc_datetime': datetime.datetime.now()
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_datetime_invalid_type():
    schema = {
        'title': 'Example',
        'type': 'datetime'
    }
    instance = {
        '_type': 'date',
        'utc_datetime': '2017-03-31 10:20:30'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_array():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    validate(instance, schema)


def test_validate_array_multiple_errors():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    instance = [
        {
            '_type': 'text'
        },
        {
            '_type': 'bool'
        },
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    with pytest.raises(ValidationError) as exc_info:
        validate(instance, schema)
    exception = exc_info.value
    assert len(exception.paths) == 2
    assert ['0'] in exception.paths
    assert ['1'] in exception.paths


def test_validate_array_invalid_instance_type():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    instance = {
        '_type': 'text',
        'text': 'test'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_array_invalid_item_type():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        }
    }
    instance = [
        {
            '_type': 'bool',
            'value': True
        }
    ]
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_array_min_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'minItems': 1
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    validate(instance, schema)


def test_validate_array_invalid_min_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'minItems': 2
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_array_max_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'maxItems': 1
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    validate(instance, schema)


def test_validate_array_invalid_max_items():
    schema = {
        'title': 'Example',
        'type': 'array',
        'items': {
            'title': 'Example Item',
            'type': 'text'
        },
        'maxItems': 0
    }
    instance = [
        {
            '_type': 'text',
            'text': 'test'
        }
    ]
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example Item',
                'type': 'text'
            }
        }
    }
    instance = {}
    validate(instance, schema)


def test_validate_object_multiple_errors():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example1': {
                'title': 'Example Item',
                'type': 'text'
            },
            'example2': {
                'title': 'Example Item',
                'type': 'text'
            }
        },
        'required': ['example1', 'example2']
    }
    instance = {
        'example2': {
            '_type': 'tect',
            'text': 'test'
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        validate(instance, schema)
    exception = exc_info.value
    assert len(exception.paths) == 2
    assert ['example1'] in exception.paths
    assert ['example2'] in exception.paths


def test_validate_object_invalid_instance_type():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example Item',
                'type': 'text'
            }
        }
    }
    instance = []
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_required():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example Item',
                'type': 'text'
            }
        },
        'required': ['example']
    }
    instance = {
        'example': {
            '_type': 'text',
            'text': 'test'
        }
    }
    validate(instance, schema)


def test_validate_object_required_missing():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        },
        'required': ['example']
    }
    instance = {}
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_unknown_property():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        }
    }
    instance = {
        'unknown': {
            '_type': 'text',
            'text': 'test'
        }
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_invalid_property():
    schema = {
        'title': 'Example',
        'type': 'object',
        'properties': {
            'example': {
                'title': 'Example',
                'type': 'text'
            }
        }
    }
    instance = {
        'example': {
            '_type': 'bool',
            'value': True
        }
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_sample():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'sample'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      'required': ['name']
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'sample',
        'object_id': object.id
    }
    validate(instance, schema)


def test_validate_sample_invalid_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'sample'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      'required': ['name']
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object_id = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = object_id
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_sample_unexpected_keys():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'sample'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      'required': ['name']
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object_id = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'sample',
        'object_id': object_id,
        'action_id': action.id
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_sample_missing_keys():
    schema = {
        'title': 'Example',
        'type': 'sample'
    }
    instance = {
        '_type': 'sample'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_sample_wrong_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'sample'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      "required": ["name"]
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object_id = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'object_reference',
        'object_id': object_id
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_sample_wrong_object_id_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'sample'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      "required": ["name"]
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'sample',
        'object_id': object
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_sample_invalid_object_id():
    schema = {
        'title': 'Example',
        'type': 'sample'
    }
    instance = {
        '_type': 'sample',
        'object_id': 42
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_measurement():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'measurement'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.MEASUREMENT, "Example Action", schema={
      "title": "Measurement Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Measurement Name",
          "type": "text"
        }
      },
      'required': ['name']
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'measurement',
        'object_id': object.id
    }
    validate(instance, schema)


def test_validate_measurement_invalid_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'measurement'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.MEASUREMENT, "Example Action", schema={
      "title": "Measurement Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Measurement Name",
          "type": "text"
        }
      },
      'required': ['name']
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object_id = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = object_id
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_measurement_unexpected_keys():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'measurement'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.MEASUREMENT, "Example Action", schema={
      "title": "Measurement Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Measurement Name",
          "type": "text"
        }
      },
      'required': ['name']
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object_id = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'measurement',
        'object_id': object_id,
        'action_id': action.id
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_measurement_missing_keys():
    schema = {
        'title': 'Example',
        'type': 'measurement'
    }
    instance = {
        '_type': 'measurement'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_measurement_wrong_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'measurement'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.MEASUREMENT, "Example Action", schema={
      "title": "Measurement Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Measurement Name",
          "type": "text"
        }
      },
      "required": ["name"]
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object_id = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'object_reference',
        'object_id': object_id
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_measurement_wrong_object_id_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'measurement'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.MEASUREMENT, "Example Action", schema={
      "title": "Measurement Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Measurement Name",
          "type": "text"
        }
      },
      "required": ["name"]
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'measurement',
        'object_id': object
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_measurement_invalid_object_id():
    schema = {
        'title': 'Example',
        'type': 'measurement'
    }
    instance = {
        '_type': 'measurement',
        'object_id': 42
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_reference():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'object_reference'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      'required': ['name']
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'object_reference',
        'object_id': object.id
    }
    validate(instance, schema)
    schema['action_type_id'] = None
    validate(instance, schema)
    schema['action_type_id'] = action.type_id
    validate(instance, schema)


def test_validate_object_reference_invalid_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'object_reference'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      'required': ['name']
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object_id = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = object_id
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_reference_unexpected_keys():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'object_reference'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      'required': ['name']
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object_id = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'object_reference',
        'object_id': object_id,
        'action_id': action.id
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_reference_missing_keys():
    schema = {
        'title': 'Example',
        'type': 'object_reference'
    }
    instance = {
        '_type': 'object_reference'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_reference_wrong_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'object_reference'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      "required": ["name"]
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object_id = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'sample',
        'object_id': object_id
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_reference_wrong_object_id_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'object_reference'
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      "required": ["name"]
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'object_reference',
        'object_id': object
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_reference_invalid_object_id():
    schema = {
        'title': 'Example',
        'type': 'sample'
    }
    instance = {
        '_type': 'sample',
        'object_id': 42
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_object_reference_wrong_action_type():
    from sampledb.models.users import User, UserType
    from sampledb.models.actions import Action
    schema = {
        'title': 'Example',
        'type': 'object_reference',
        'action_type_id': sampledb.models.ActionType.MEASUREMENT
    }
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    action = Action(sampledb.models.ActionType.SAMPLE_CREATION, "Example Action", schema={
      "title": "Sample Information",
      "type": "object",
      "properties": {
        "name": {
          "title": "Sample Name",
          "type": "text"
        }
      },
      "required": ["name"]
    })

    sampledb.db.session.add(user)
    sampledb.db.session.add(action)
    sampledb.db.session.commit()

    object = create_object(data={'name': {'_type': 'text', 'text': 'example'}}, user_id=user.id, action_id=action.id)
    instance = {
        '_type': 'object_reference',
        'object_id': object.id
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_tags():
    schema = {
        'title': 'Example',
        'type': 'tags'
    }
    instance = {
        '_type': 'tags',
        'tags': ['tag', 'other', 'keyword']
    }
    validate(instance, schema)


def test_validate_tags_empty():
    schema = {
        'title': 'Example',
        'type': 'tags'
    }
    instance = {
        '_type': 'tags',
        'tags': []
    }
    validate(instance, schema)


def test_validate_tags_invalid_content():
    schema = {
        'title': 'Example',
        'type': 'tags'
    }
    instance = {
        '_type': 'tags',
        'tags': 'tag,other,keyword'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_tags_invalid_tag():
    schema = {
        'title': 'Example',
        'type': 'tags'
    }
    instance = {
        '_type': 'tags',
        'tags': ['tag', 'other', 'üöäß']
    }
    validate(instance, schema)
    instance['tags'][-1] = 'tag?'
    with pytest.raises(ValidationError):
        validate(instance, schema)
    instance['tags'][-1] = 'tag '
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_tags_duplicate_tags():
    schema = {
        'title': 'Example',
        'type': 'tags'
    }
    instance = {
        '_type': 'tags',
        'tags': ['tag', 'other', 'tag']
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_hazards():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['hazards']
    }
    instance = {
        'hazards': {
            '_type': 'hazards',
            'hazards': [1, 3, 5]
        }
    }
    validate(instance, schema)


def test_validate_hazards_empty():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['hazards']
    }
    instance = {
        'hazards': {
            '_type': 'hazards',
            'hazards': []
        }
    }
    validate(instance, schema)


def test_validate_hazards_invalid_content():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['hazards']
    }
    instance = {
        'hazards': {
            '_type': 'hazards',
            'hazards': [0]
        }
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)

    instance = {
        'hazards': {
            '_type': 'hazards',
            'hazards': [10]
        }
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)

    instance = {
        'hazards': {
            '_type': 'hazards',
            'hazards': ["Explosive"]
        }
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_hazards_duplicate_hazards():
    schema = {
        'title': 'Object',
        'type': 'object',
        'properties': {
            'hazards': {
                'title': 'GHS hazards',
                'type': 'hazards'
            }
        },
        'required': ['hazards']
    }
    instance = {
        'hazards': {
            '_type': 'hazards',
            'hazards': [1, 5, 1]
        }
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_user():
    from sampledb.models.users import User, UserType
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    schema = {
        'title': 'Example User',
        'type': 'user'
    }

    instance = {
        '_type': 'user',
        'user_id': user.id
    }
    validate(instance, schema)


def test_validate_user_unexpected_keys():
    from sampledb.models.users import User, UserType
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    schema = {
        'title': 'Example User',
        'type': 'user'
    }
    instance = {
        '_type': 'user',
        'user_id': user.id,
        'user_role': 'example'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_user_missing_keys():
    schema = {
        'title': 'Example User',
        'type': 'user'
    }
    instance = {
        '_type': 'user'
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_user_wrong_type():
    from sampledb.models.users import User, UserType
    user = User("User", "example@fz-juelich.de", UserType.OTHER)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    schema = {
        'title': 'Example User',
        'type': 'user'
    }
    instance = {
        '_type': 'user_id',
        'user_id': user.id
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)


def test_validate_user_invalid_user_id():
    schema = {
        'title': 'Example User',
        'type': 'user'
    }
    instance = {
        '_type': 'user',
        'user_id': 42
    }
    with pytest.raises(ValidationError):
        validate(instance, schema)
