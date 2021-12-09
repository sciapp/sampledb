# coding: utf-8
"""

"""

from sampledb.logic.schemas.copy_data import copy_data
from sampledb.logic.schemas.validate_schema import validate_schema
from sampledb.logic.schemas.validate import validate


def test_copy_data():
    schema = {
        'title': 'Example Object',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'steps': {
                'title': 'Steps',
                'type': 'array',
                'items': {
                    'title': 'Step',
                    'type': 'object',
                    'properties': {
                        'description': {
                            'title': 'Description',
                            'type': 'text'
                        }
                    }
                }
            }
        },
        'required': ['name']
    }
    instance = {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'steps': [
            {
                'description': {
                    '_type': 'text',
                    'text': 'Step 1'
                }
            },
            {
                'description': {
                    '_type': 'text',
                    'text': 'Step 2'
                }
            }
        ]
    }
    validate_schema(schema)
    validate(instance, schema)
    assert copy_data(instance, schema) == {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'steps': [
            {
                'description': {
                    '_type': 'text',
                    'text': 'Step 1'
                }
            },
            {
                'description': {
                    '_type': 'text',
                    'text': 'Step 2'
                }
            }
        ]
    }

    schema['properties']['steps']['items']['properties']['description']['may_copy'] = False
    validate_schema(schema)
    validate(instance, schema)
    assert copy_data(instance, schema) == {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'steps': [
            {
                'description': None
            },
            {
                'description': None
            }
        ]
    }

    del instance['steps'][0]['description']
    validate_schema(schema)
    validate(instance, schema)
    assert copy_data(instance, schema) == {
        'name': {
            '_type': 'text',
            'text': 'Name'
        },
        'steps': [
            {
                'description': None
            },
            {
                'description': None
            }
        ]
    }
