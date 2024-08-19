# coding: utf-8
"""

"""
import dataclasses
import datetime
import inspect
import typing

import pytz
import sqlalchemy
import pytest

from sampledb import db
import sampledb.logic
import sampledb.models


@pytest.fixture
def user():
    user = sampledb.models.User(
        name="User",
        email="example@example.com",
        type=sampledb.models.UserType.PERSON)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def action():
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'tags': {
                    'title': 'Tags',
                    'type': 'tags'
                },
                'text_attr': {
                    'title': 'Text Attribute 1',
                    'type': 'text'
                },
                'bool_attr': {
                    'title': 'Boolean Attribute 1',
                    'type': 'bool'
                },
                'bool_attr2': {
                    'title': 'Boolean Attribute 2',
                    'type': 'bool'
                },
                'bool_attr3': {
                    'title': 'Boolean Attribute 3',
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
                'object_reference_attr': {
                    'title': 'Object Reference',
                    'type': 'object_reference'
                },
                'user_reference_attr': {
                    'title': 'User Reference',
                    'type': 'user'
                },
                'Attribute': {
                    'title': 'Mixed Case Attribute Name',
                    'type': 'text'
                },
                'array_attr': {
                    'title': 'Array Attribute',
                    'type': 'array',
                    'items': {
                        'title': 'Array Attribute Item',
                        'type': 'object',
                        'properties': {
                            'text_attr': {
                                'title': 'Array Attribute Item Text Attribute',
                                'type': 'text'
                            },
                            'bool_attr': {
                                'title': 'Array Attribute Item Boolean Attribute',
                                'type': 'bool'
                            }
                        }
                    }
                }
            },
            'required': ['name']
        }
    )
    return action


def test_find_by_empty_string(user, action) -> None:
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

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 2
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('', use_advanced_search=False)
    assert not use_advanced_search
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 2
    assert len(search_notes) == 0


def test_find_by_simple_text(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'text_attr': {
            '_type': 'text',
            'text': "This is a test."
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'text_attr': {
            '_type': 'text',
            'text': "This is an example."
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('test', use_advanced_search=False)
    assert not use_advanced_search
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert 'test' in object.data['text_attr']['text']


@pytest.mark.parametrize('special_character', ['ä', '%', '_', '.', ':', '{', '[', '(', "'", '"',])
def test_find_by_special_characters(user, special_character) -> None:
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Example Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    data = {
        'name': {
            '_type': 'text',
            'text': "This is a test without any special characters"
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': f"This contains {special_character}"
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(data['name']['text'], use_advanced_search=False)
    assert not use_advanced_search
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert data['name']['text'] in object.data['name']['text']

def test_find_by_tag(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'tags': {
            '_type': 'tags',
            'tags': ['tag1', 'tag2', 'tag3']
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'tags': {
            '_type': 'tags',
            'tags': ['tag2', 'tag3']
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('#tag1', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert 'tag1' in object.data['tags']['tags']


def test_find_by_unknown_tag(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'tags': {
            '_type': 'tags',
            'tags': ['tag1', 'tag2', 'tag3']
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'tags': {
            '_type': 'tags',
            'tags': ['tag2', 'tag3']
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('#tag4', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_attribute(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']


def test_find_by_boolean_attribute_equal(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr == True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr == False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert not object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True == bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False == bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert not object.data['bool_attr']['value']


def test_find_by_boolean_attribute_not_equal(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr != True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert not object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr != False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True != bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert not object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False != bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']


def test_find_by_equal_values(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True == True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True == False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 == 2018-10-05', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 == 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"Example" == "Example"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"Example" == "Exomple"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm == 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm == 20km', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_unequal_values(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True != True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True != False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 != 2018-10-05', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 != 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"Example" != "Example"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"Example" != "Exomple"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm != 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm != 20km', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0


def test_find_by_boolean_attribute_or(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        },
        'bool_attr2': {
            '_type': 'bool',
            'value': True
        },
        'bool_attr3': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': False
        },
        'bool_attr2': {
            '_type': 'bool',
            'value': True
        },
        'bool_attr3': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr or True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 2
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr or False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True or bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 2
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False or bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr or bool_attr2', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 2
    assert len(search_notes) == 0
    for object in objects:
        assert ('bool_attr' in object.data and object.data['bool_attr']['value']) or ('bool_attr2' in object.data and object.data['bool_attr2']['value'])

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr or bool_attr3', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert ('bool_attr' in object.data and object.data['bool_attr']['value']) or ('bool_attr3' in object.data and object.data['bool_attr3']['value'])


def test_find_by_boolean_attribute_and(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        },
        'bool_attr2': {
            '_type': 'bool',
            'value': True
        },
        'bool_attr3': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': False
        },
        'bool_attr2': {
            '_type': 'bool',
            'value': True
        },
        'bool_attr3': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr and True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr and False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True and bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False and bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr and bool_attr2', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert ('bool_attr' in object.data and object.data['bool_attr']['value']) and ('bool_attr2' in object.data and object.data['bool_attr2']['value'])

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr and bool_attr3', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_boolean_boolean_and(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True and True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True and False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False and True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False and False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_boolean_boolean_or(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True or True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True or False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False or True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False or False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_boolean_expression_and(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True and (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True and (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False and (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False and (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) and True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) and False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and True) and (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and True) and (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) and (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) and (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_boolean_expression_or(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True or (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True or (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False or (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False or (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) or True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) or False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and True) or (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and True) or (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) or (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) or (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_attribute_expression_and(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr and (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr and (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and True) and bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) and bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_attribute_expression_or(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr or (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 2
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr or (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and True) or bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 2
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) or bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0


def test_find_by_datetime_attribute_equal(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2018-10-05 12:00:00'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr == 2018-10-05', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr == 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 == datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-06 == datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

def test_find_by_datetime_attribute_equal_with_timezones(user, action) -> None:
    for day in (3, 4, 5):
        for hour in range(24):
            data = {
                'name': {
                    '_type': 'text',
                    'text': 'Name'
                },
                'datetime_attr': {
                    '_type': 'datetime',
                    'utc_datetime': datetime.datetime(2024, 6, day, hour, 0, 0, 0, tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    @dataclasses.dataclass
    class MockUser:
        timezone: typing.Optional[str]

    # mock current user to avoid being dependent on the request context
    where_filters_module = inspect.getmodule(sampledb.logic.where_filters)
    previous_current_user = where_filters_module.current_user

    try:
        for timezone_name in pytz.common_timezones:
            timezone = pytz.timezone(timezone_name)
            where_filters_module.current_user = MockUser(timezone=timezone_name)
            filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr == 2024-06-04', use_advanced_search=True)
            filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
            objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
            assert len(objects) == 24
            assert len(search_notes) == 0
            for object in objects:
                utc_datetime = datetime.datetime.strptime(object.data['datetime_attr']['utc_datetime'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc)
                local_datetime = utc_datetime.astimezone(timezone)
                local_date = local_datetime.date()
                assert (local_date.year, local_date.month, local_date.day) == (2024, 6, 4)
    finally:
        where_filters_module.current_user = previous_current_user

def test_find_by_datetime_on(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2018-10-05 12:00:00'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr on 2018-10-05', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr on 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 on datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-06 on datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 on 2018-10-05', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-06 on 2018-10-05', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_datetime_less_than(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2018-10-05 12:00:00'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr < 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 < 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 < 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr < 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-04 < datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-06 < datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_datetime_before(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2018-10-05 12:00:00'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr before 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 before 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 before 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr before 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-04 before datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-06 before datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_datetime_greater_than(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2018-10-05 12:00:00'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr > 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 > 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 > 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr > 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 > datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-04 > datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_datetime_after(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2018-10-05 12:00:00'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr after 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 after 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 after 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr after 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 after datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-04 after datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_datetime_less_than_or_equal(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2018-10-05 12:00:00'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr <= 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 <= 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 <= 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 <= 2018-10-05', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr <= 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-04 <= datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-06 <= datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_datetime_greater_than_or_equal(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'datetime_attr': {
            '_type': 'datetime',
            'utc_datetime': '2018-10-05 12:00:00'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr >= 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 >= 2018-10-06', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 >= 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 >= 2018-10-05', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('datetime_attr >= 2018-10-04', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-05 >= datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['datetime_attr']['utc_datetime'] == '2018-10-05 12:00:00'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-04 >= datetime_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_quantity_attribute_equal(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'quantity_attr': {
            '_type': 'quantity',
            'units': 'cm',
            'dimensionality': '[length]',
            'magnitude_in_base_units': 0.01
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr == 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr == 0.00001km', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr == 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm == quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2cm == quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_quantity_attribute_not_equal(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'quantity_attr': {
            '_type': 'quantity',
            'units': 'cm',
            'dimensionality': '[length]',
            'magnitude_in_base_units': 0.01
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr != 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr != 0.00001km', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr != 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm != quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2cm != quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2kg != quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0


def test_find_by_quantity_less_than(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'quantity_attr': {
            '_type': 'quantity',
            'units': 'cm',
            'dimensionality': '[length]',
            'magnitude_in_base_units': 0.01
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr < 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2cm < 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm < 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr < 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('0.5cm < quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm < quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr < 1e-4km', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0


def test_find_by_quantity_greater_than(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'quantity_attr': {
            '_type': 'quantity',
            'units': 'cm',
            'dimensionality': '[length]',
            'magnitude_in_base_units': 0.01
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr > 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm > 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2cm > 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr > 0.5cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2cm > quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm > quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_quantity_less_than_equals(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'quantity_attr': {
            '_type': 'quantity',
            'units': 'cm',
            'dimensionality': '[length]',
            'magnitude_in_base_units': 0.01
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr <= 0.5cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr <= 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2cm <= 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm <= 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr <= 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('0.5cm <= quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2cm <= quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm <= quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1 <= quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_quantity_greater_than_equals(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'quantity_attr': {
            '_type': 'quantity',
            'units': 'cm',
            'dimensionality': '[length]',
            'magnitude_in_base_units': 0.01
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr >= 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr >= 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm >= 2cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2cm >= 1cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr >= 0.5cm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2cm >= quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('1cm >= quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('0.5cm >= quantity_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_text_contains(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'text_attr': {
            '_type': 'text',
            'text': 'This is an example.'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"ample" in "example"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"ampel" in "example"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"ample" in text_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"ampel" in text_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_text_attribute_equal(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'text_attr': {
            '_type': 'text',
            'text': 'This is an example.'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"This is an example." == text_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"This is an example!" == text_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('text_attr == "This is an example."', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('text_attr == "This is an example!"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_attribute_equal(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        },
        'bool_attr2': {
            '_type': 'bool',
            'value': True
        },
        'bool_attr3': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr == bool_attr2', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr2 == bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr == bool_attr3', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr3 == bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_expression_equal(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and True) == (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) == (True and False)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(True and False) == (True and True)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_find_by_boolean_not(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert search_notes == [('warning', 'This expression will always be true', 0, 9)]

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('warning', 'This expression will always be false', 0, 8)]


def test_find_by_attribute_not(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': True
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'bool_attr': {
            '_type': 'bool',
            'value': False
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert not object.data['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('!(not bool_attr)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['bool_attr']['value']


def test_find_by_array_item(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'array_attr': [
            {
                'text_attr': {
                    '_type': 'text',
                    'text': 'Example'
                },
                'bool_attr': {
                    '_type': 'bool',
                    'value': True
                }
            },
            {
                'text_attr': {
                    '_type': 'text',
                    'text': 'Test'
                },
                'bool_attr': {
                    '_type': 'bool',
                    'value': False
                }
            }
        ]
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'array_attr': [
            {
                'text_attr': {
                    '_type': 'text',
                    'text': 'Example'
                },
                'bool_attr': {
                    '_type': 'bool',
                    'value': True
                }
            }
        ]
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"est" in array_attr.?.text_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert "est" in object.data['array_attr'][1]['text_attr']['text']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('array_attr.?.text_attr = "Test"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert object.data['array_attr'][1]['text_attr']['text'] == 'Test'

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not array_attr.?.bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0
    for object in objects:
        assert not object.data['array_attr'][1]['bool_attr']['value']

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('array_attr.?.bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 2
    assert len(search_notes) == 0
    for object in objects:
        assert any(o['bool_attr']['value'] for o in object.data['array_attr'])


def test_find_by_unknown_binary_operation(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False and 2018-10-11', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unknown binary operation", 0, len('False and 2018-10-11'))


def test_find_by_unknown_unary_operation(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not 2018-10-11', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unknown unary operation", 0, len('not 2018-10-11'))

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not 1mm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unknown unary operation", 0, len('not 1mm'))

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not "Test"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unknown unary operation", 0, len('not "Test"'))


def test_find_by_mutliple_array_placeholders(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('array_attr.?.bool_attr and array_attr.?.bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Multiple array placeholders", 0, len('array_attr.?.bool_attr and array_attr.?.bool_attr'))


def test_find_by_invalid_array_placeholder(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('array_attr.?.?.bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Multiple array placeholders", 0, len('array_attr.?.?.bool_attr'))

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('array_attr.??.bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Invalid array placeholder", 0, len('array_attr.??.bool_attr'))


def test_find_by_invalid_literal(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('åttr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unable to parse literal", 0, len('åttr'))


def test_find_by_invalid_attribute_name(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('a..ttr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Invalid attribute name", 0, len('a..ttr'))


def test_find_by_invalid_units(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('quantity_attr > 1 Banana', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unable to parse units", len('quantity_attr > 1'), len('quantity_attr > 1 Banana'))


def test_find_by_invalid_tag(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('#tåg', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Invalid tag", 1, len('#tåg'))


def test_find_by_unfinished_text(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('text_attr == "', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unfinished text", len('text_attr == '), len('text_attr == "'))


def test_find_by_unbalanced_parentheses(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(bool_attr', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unmatched opening parenthesis", 0, 1)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('bool_attr)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unmatched closing parenthesis", len('bool_attr'), len('bool_attr)'))


def test_find_by_invalid_operands(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('and True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Binary operator without left operand", 0, len('and'))

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True and', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Binary operator without right operand", len('True '), len('True and'))

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Unary operator without operand", 0, len('not'))

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not and', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 1
    assert search_notes[0] == ('error', "Invalid right operand", 0, len('not and'))


def test_find_by_different_dimensionalities(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm == 20l', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None)]

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm != 20l', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert search_notes == [('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None)]

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm > 20l', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None)]

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm < 20l', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None)]

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm >= 20l', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None)]

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm <= 20l', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('warning', 'Invalid comparison between quantities of different dimensionalities', 0, None)]


def test_find_by_boolean_literal(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('True', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert search_notes == [('warning', 'This search will always return all objects', 0, len('True'))]

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('warning', 'This search will never return any objects', 0, len('False'))]


def test_find_by_other_literal(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('2018-10-12', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('error', 'Unable to use literal as search query', 0, len('2018-10-12'))]

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('20mm', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('error', 'Unable to use literal as search query', 0, len('20mm'))]


def test_find_by_text_operators(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('not not False', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('warning', 'This expression will always be true', len('not '), len('not not False'))]


def test_find_by_negative_quantity(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('-2kg < 0kg', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert search_notes == []


def test_find_by_parentheses_only(user, action) -> None:
    sampledb.logic.objects.create_object(action_id=action.id, data={
        'name': {
            '_type': 'text',
            'text': 'Name'
        }
    }, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('()', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('error', 'Empty search', 0, 2)]

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(()())', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert search_notes == [('error', 'Invalid search query (missing operator)', 0, None)]


def test_find_by_automatic_advanced_search(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'text_attr': {
            '_type': 'text',
            'text': 'This is an example.'
        }
    }
    sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('text_attr = "This is an example."', use_advanced_search=False)
    assert use_advanced_search
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('"text_attr = "This is an example.""', use_advanced_search=False)
    assert not use_advanced_search
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 0
    assert len(search_notes) == 0


def test_with_name_collision(user) -> None:
    schema1 = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'vs': {
                'title': 'vs',
                'type': 'text'
            }
        },
        'required': ['name']
    }
    schema2 = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'vs': {
                'title': 'vs',
                'type': 'array',
                'items': {
                    'type': 'object',
                    'title': 'v',
                    'properties': {
                        'v': {
                            'title': 'v',
                            'type': 'text'
                        }
                    }
                }
            }
        },
        'required': ['name']
    }
    action1 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema1
    )
    action2 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema2
    )

    data1 = {
        'name': {
            '_type': 'text',
            'text': 'o1'
        },
        'vs': {
            '_type': 'text',
            'text': 'v1'
        }
    }
    data2 = {
        'name': {
            '_type': 'text',
            'text': 'o1'
        },
        'vs': [
            {
                'v': {
                    '_type': 'text',
                    'text': 'v1'
                }
            }
        ]
    }
    sampledb.logic.objects.create_object(action1.id, data1, user.id)
    sampledb.logic.objects.create_object(action2.id, data2, user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('vs == "v1"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert objects[0].data == data1
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('vs.?.v == "v1"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1
    assert objects[0].data == data2
    assert len(search_notes) == 0


def test_find_by_reference(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name 1'
        },
        'user_reference_attr': {
            '_type': 'user',
            'user_id': user.id
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name 2'
        },
        'object_reference_attr': {
            '_type': 'object_reference',
            'object_id': object1.id
        }
    }
    object2 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name 3'
        },
        'object_reference_attr': {
            '_type': 'object_reference',
            'object_id': object2.id
        }
    }
    object3 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'object_reference_attr == #{object1.id}', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1 and objects[0].id == object2.id
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('object_reference_attr != #0', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 2 and {object.id for object in objects} == {object2.id, object3.id}
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'user_reference_attr == #{user.id}', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1 and objects[0].id == object1.id
    assert len(search_notes) == 0


def test_find_by_case_insensitive_attribute(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name 1'
        },
        'Attribute': {
            '_type': 'text',
            'text': 'example'
        }
    }
    object = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'Attribute == "example"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1 and objects[0].id == object.id
    assert len(search_notes) == 0


def test_find_text_mixed_internationalisation(user, action) -> None:
    object1 = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': 'Name 1'
            }
        },
        user_id=user.id
    )

    object2 = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': {
                    'en': 'Name 1'
                }
            }
        },
        user_id=user.id
    )

    object3 = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': 'Name 2'
            }
        },
        user_id=user.id
    )

    object4 = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': {
                    'en': 'Name 2'
                }
            }
        },
        user_id=user.id
    )

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'name == "Name 1"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    found_objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    found_object_ids = {
        object.object_id
        for object in found_objects
    }
    assert found_object_ids == {object1.id, object2.id}

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'!(name == "Name 1")', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    found_objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    found_object_ids = {
        object.object_id
        for object in found_objects
    }
    assert found_object_ids == {object3.id, object4.id}

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'"1" in name', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    found_objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    found_object_ids = {
        object.object_id
        for object in found_objects
    }
    assert found_object_ids == {object1.id, object2.id}

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'!("1" in name)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    found_objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    found_object_ids = {
        object.object_id
        for object in found_objects
    }
    assert found_object_ids == {object3.id, object4.id}


def test_find_missing_attribute(user, action) -> None:
    object1 = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': {
                    'en': 'Name 1'
                }
            },
            'Attribute': {
                '_type': 'text',
                'text': {
                    'en': 'example'
                }
            }
        },
        user_id=user.id
    )

    object2 = sampledb.logic.objects.create_object(
        action_id=action.id,
        data={
            'name': {
                '_type': 'text',
                'text': {
                    'en': 'Name 2'
                }
            }
        },
        user_id=user.id
    )

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'Attribute == "example"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    found_objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    found_object_ids = {
        object.object_id
        for object in found_objects
    }
    assert found_object_ids == {object1.id,}

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'!(Attribute == "example")', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    found_objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    found_object_ids = {
        object.object_id
        for object in found_objects
    }
    assert found_object_ids == {object2.id,}

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'"ex" in Attribute', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    found_objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    found_object_ids = {
        object.object_id
        for object in found_objects
    }
    assert found_object_ids == {object1.id,}

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'!("ex" in Attribute)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    found_objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    found_object_ids = {
        object.object_id
        for object in found_objects
    }
    assert found_object_ids == {object2.id,}


def test_find_by_missing_attribute(user, action) -> None:
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name 1'
        },
        'Attribute': {
            '_type': 'text',
            'text': 'example'
        }
    }
    object1 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)
    data = {
        'name': {
            '_type': 'text',
            'text': 'Name 2'
        }
    }
    object2 = sampledb.logic.objects.create_object(action_id=action.id, data=data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'Attribute == null', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1 and objects[0].id == object2.id
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(f'!(Attribute == null)', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1 and objects[0].id == object1.id
    assert len(search_notes) == 0

def test_find_by_referenced_object(user):
    referenced_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Referenced Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    referenced_data = {
        'name': {
            '_type': 'text',
            'text': 'Name 1'
        }
    }
    referenced_object = sampledb.logic.objects.create_object(action_id=referenced_action.id, data=referenced_data, user_id=user.id)
    referencing_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Referencing Object',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'object_reference': {
                    'title': 'Object',
                    'type': 'object_reference'
                }
            },
            'required': ['name']
        }
    )
    referencing_data = {
        'name': {
            '_type': 'text',
            'text': 'Name 2'
        },
        'object_reference': {
            '_type': 'object_reference',
            'object_id': referenced_object.object_id
        }
    }
    referencing_object = sampledb.logic.objects.create_object(action_id=referencing_action.id, data=referencing_data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('*object_reference.name == "Name 1"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1 and objects[0].id == referencing_object.id
    assert len(search_notes) == 0

    referencing_data['object_reference']['object_id'] = referencing_object.id
    other_object = sampledb.logic.objects.create_object(action_id=referencing_action.id, data=referencing_data, user_id=user.id)

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('*object_reference.name == "Name 1"', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(objects) == 1 and objects[0].id == referencing_object.id
    assert len(search_notes) == 0

    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func('(*object_reference.name == "Name 1") || (*object_reference.name == "Name 2")', use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(search_notes) == 0
    assert len(objects) == 2 and {object.id for object in objects} == {referencing_object.id, other_object.id}

@pytest.mark.parametrize('query_string', [
    '*object_reference.*other_reference.name == "Name 1"',
    'array.?.*other_reference.name == "Name 1"',
    'object_reference*.name == "Name 1"',
    'array.*.name == "Name 1"'
])
def test_invalid_referencing_query(query_string):
    filter_func, search_tree, use_advanced_search = sampledb.logic.object_search.generate_filter_func(query_string, use_advanced_search=True)
    filter_func, search_notes = sampledb.logic.object_search.wrap_filter_func(filter_func)
    objects = sampledb.logic.objects.get_objects(filter_func=filter_func)
    assert len(search_notes) == 1
    assert len(objects) == 0
