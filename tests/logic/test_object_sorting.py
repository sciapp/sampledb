# coding: utf-8
"""

"""

import pytest

from sampledb import db
import sampledb.logic
from sampledb.logic import object_sorting
import sampledb.models
from sampledb.models import Action, User


@pytest.fixture
def user() -> User:
    user = sampledb.models.User(
        name="User",
        email="example@fz-juelich.de",
        type=sampledb.models.UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def action() -> Action:
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        name="",
        description="",
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'text_attr': {
                    'title': 'Text Attribute 1',
                    'type': 'text'
                },
                'bool_attr': {
                    'title': 'Boolean Attribute 1',
                    'type': 'bool'
                },
                'datetime_attr': {
                    'title': 'Datetime Attribute',
                    'type': 'datetime'
                },
                'quantity_attr': {
                    'title': 'Quantity Attribute',
                    'type': 'quantity',
                    'units': 'm'
                },
                'sample_attr': {
                    'title': 'Sample Attribute',
                    'type': 'sample'
                }
            },
            'required': ['name']
        }
    )
    return action


def test_order_by_default(user: User, action: Action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True)
    assert objects[0].id > objects[1].id


def test_order_by_object_id(user: User, action: Action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.object_id()))
    assert objects[0].id <= objects[1].id

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.object_id()))
    assert objects[0].id >= objects[1].id


def test_order_by_creation_date(user: User, action: Action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.creation_date()))
    assert objects[0].utc_datetime <= objects[1].utc_datetime

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.creation_date()))
    assert objects[0].utc_datetime >= objects[1].utc_datetime

    sampledb.logic.objects.update_object(objects[1].object_id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.creation_date()))
    assert objects[0].utc_datetime >= objects[1].utc_datetime

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.creation_date()))
    assert objects[0].utc_datetime <= objects[1].utc_datetime


def test_order_by_last_modification_date(user: User, action: Action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.last_modification_date()))
    assert objects[0].utc_datetime <= objects[1].utc_datetime

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.last_modification_date()))
    assert objects[0].utc_datetime >= objects[1].utc_datetime

    sampledb.logic.objects.update_object(objects[1].object_id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.last_modification_date()))
    assert objects[0].utc_datetime <= objects[1].utc_datetime

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.last_modification_date()))
    assert objects[0].utc_datetime >= objects[1].utc_datetime


def test_order_by_text_property(user: User, action: Action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'ABC'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.property_value("name")))
    assert objects[0].data['name']['text'] <= objects[1].data['name']['text']

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.property_value("name")))
    assert objects[0].data['name']['text'] >= objects[1].data['name']['text']


def test_order_by_quantity_property(user: User, action: Action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'quantity_attr': {
            '_type': 'quantity',
            'dimensionality': '[length]',
            'magnitude_in_base_units': 42,
            'units': 'm'
        }
    }, user_id=user.id)
    object = sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'quantity_attr': {
            '_type': 'quantity',
            'dimensionality': '[length]',
            'magnitude_in_base_units': 17,
            'units': 'm'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.property_value("quantity_attr")))
    assert objects[0].data['quantity_attr']['magnitude_in_base_units'] <= objects[1].data['quantity_attr']['magnitude_in_base_units']

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.property_value("quantity_attr")))
    assert objects[0].data['quantity_attr']['magnitude_in_base_units'] >= objects[1].data['quantity_attr']['magnitude_in_base_units']

    sampledb.logic.objects.update_object(object_id=object.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.property_value("quantity_attr")))
    assert 'quantity_attr' in objects[0].data and 'quantity_attr' not in objects[1].data

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.property_value("quantity_attr")))
    assert 'quantity_attr' in objects[1].data and 'quantity_attr' not in objects[0].data


def test_order_by_boolean_property(user: User, action: Action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        }
    }, user_id=user.id)
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': False
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.property_value("bool_attr")))
    assert objects[0].data['bool_attr']['value'] <= objects[1].data['bool_attr']['value']

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.property_value("bool_attr")))
    assert objects[0].data['bool_attr']['value'] >= objects[1].data['bool_attr']['value']


def test_order_by_datetime_property(user: User, action: Action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2019-01-28 16:00:00'
        }
    }, user_id=user.id)
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2019-01-29 16:00:00'
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.property_value("datetime_attr")))
    assert objects[0].data['datetime_attr']['utc_datetime'] <= objects[1].data['datetime_attr']['utc_datetime']

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.property_value("datetime_attr")))
    assert objects[0].data['datetime_attr']['utc_datetime'] >= objects[1].data['datetime_attr']['utc_datetime']


def test_order_by_sample_property(user: User, action: Action) -> None:
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)
    object2 = sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'sample_attr': {
            '_type': 'sample',
            'object_id': object1.id
        }
    }, user_id=user.id)
    sampledb.logic.objects.update_object(object_id=object1.object_id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'sample_attr': {
            '_type': 'sample',
            'object_id': object2.id
        }
    }, user_id=user.id)

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.ascending(object_sorting.property_value("sample_attr")))
    assert objects[0].data['sample_attr']['object_id'] <= objects[1].data['sample_attr']['object_id']

    objects = sampledb.logic.objects.get_objects(filter_func=lambda data: True, sorting_func=object_sorting.descending(object_sorting.property_value("sample_attr")))
    assert objects[0].data['sample_attr']['object_id'] >= objects[1].data['sample_attr']['object_id']
