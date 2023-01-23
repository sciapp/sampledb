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
        (): {'type': 'object', 'title': None},
        ('name',): {'type': 'text', 'title': 'name'}
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
        (): {'type': 'object', 'title': None},
        ('name',): {'type': 'text', 'title': 'name'},
        ('list',): {'type': 'array', 'title': None},
        ('list', None): {'type': 'object', 'title': None},
        ('list', None, 'name'): {'type': 'text', 'title': 'name'},
        ('list', None, 'value'): {'type': 'quantity', 'title': 'value'},
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
                                'title': 'name2',
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
        ('name',): {'type': 'text', 'title': 'name'},
        ('list', None, 'name'): {'type': 'text', 'title': 'name2'}
    }
