# coding: utf-8
"""

"""

from sampledb.logic.schemas.utils import get_property_paths_for_schema


def test_get_property_paths_for_schema():
    assert get_property_paths_for_schema({}) == {}
    assert get_property_paths_for_schema({
        'type': 'object',
        'properties': {
            'name': {
                'title': 'name',
                'type': 'text'
            }
        }
    }) == {
        (): 'object',
        ('name',): 'text'
    }
    assert get_property_paths_for_schema({
        'type': 'object',
        'properties': {
            'name': {
                'title': 'name',
                'type': 'text'
            },
            'list': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'title': 'name',
                            'type': 'text'
                        },
                        'value': {
                            'title': 'value',
                            'type': 'quantity'
                        }
                    }
                }
            }
        }
    }) == {
        (): 'object',
        ('name',): 'text',
        ('list',): 'array',
        ('list', None): 'object',
        ('list', None, 'name'): 'text',
        ('list', None, 'value'): 'quantity',
    }
    assert get_property_paths_for_schema(
        {
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'name',
                    'type': 'text'
                },
                'list': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {
                                'title': 'name',
                                'type': 'text'
                            },
                            'value': {
                                'title': 'value',
                                'type': 'quantity'
                            }
                        }
                    }
                }
            }
        },
        valid_property_types={'text'}
    ) == {
        ('name',): 'text',
        ('list', None, 'name'): 'text',
    }
