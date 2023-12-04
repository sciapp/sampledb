# coding: utf-8
"""

"""

from sampledb.logic.schemas.utils import get_property_paths_for_schema, schema_iter, data_iter


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


def test_schema_iter():
    schema = {
        'type': 'object',
        'title': 'Object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text',
                'minLength': 1
            },
            'array': {
                'type': 'array',
                'title': 'Array',
                'items': {
                    'type': 'object',
                    'title': 'Nested Object',
                    'properties': {
                        'text': {
                            'title': 'Text',
                            'type': 'text'
                        },
                        'quantity': {
                            'title': 'Quantity',
                            'type': 'quantity'
                        }
                    }
                }
            }
        },
        'required': ['name']
    }
    assert dict(schema_iter(schema)) == {
        (): schema,
        ('name',): schema['properties']['name'],
        ('array',): schema['properties']['array'],
        ('array', None): schema['properties']['array']['items'],
        ('array', None, 'text'): schema['properties']['array']['items']['properties']['text'],
        ('array', None, 'quantity'): schema['properties']['array']['items']['properties']['quantity']
    }
    assert dict(schema_iter(schema, filter_property_types={'text'})) == {
        ('name',): schema['properties']['name'],
        ('array', None, 'text'): schema['properties']['array']['items']['properties']['text'],
    }
    assert dict(schema_iter(schema, filter_property_types={'object'})) == {
        (): schema,
        ('array', None): schema['properties']['array']['items'],
    }
    assert dict(schema_iter(schema, filter_path_depth_limit=-1)) == {}
    assert dict(schema_iter(schema, filter_path_depth_limit=1)) == {
        (): schema,
        ('name',): schema['properties']['name'],
        ('array',): schema['properties']['array'],
    }
    assert dict(schema_iter(schema, path=('test',), filter_path_depth_limit=1)) == {
        ('test',): schema
    }
    assert dict(schema_iter(schema, filter_property_path=())) == {
        (): schema,
        ('name',): schema['properties']['name'],
        ('array',): schema['properties']['array'],
        ('array', None): schema['properties']['array']['items'],
        ('array', None, 'text'): schema['properties']['array']['items']['properties']['text'],
        ('array', None, 'quantity'): schema['properties']['array']['items']['properties']['quantity']
    }
    assert dict(schema_iter(schema, filter_property_path=('array',))) == {
        ('array',): schema['properties']['array'],
        ('array', None): schema['properties']['array']['items'],
        ('array', None, 'text'): schema['properties']['array']['items']['properties']['text'],
        ('array', None, 'quantity'): schema['properties']['array']['items']['properties']['quantity']
    }
    assert dict(schema_iter(schema, filter_property_path=('array', None, 'text'))) == {
        ('array', None, 'text'): schema['properties']['array']['items']['properties']['text'],
    }


def test_data_iter():
    data = {
        'name': {
            '_type': 'text',
            'text': {
                'en': 'Name'
            }
        },
        'array': [
            {
                'text': {
                    '_type': 'text',
                    'multiline': 'true',
                    'text': {
                        'en': 'Test:\n1m'
                    }
                },
                'quantity': {
                    '_type': 'quantity',
                    'magnitude_in_base_units': 1,
                    'magnitude': 1,
                    'units': 'm'
                }
            }
        ]
    }
    assert dict(data_iter(data)) == {
        (): data,
        ('name',): data['name'],
        ('array',): data['array'],
        ('array', 0): data['array'][0],
        ('array', 0, 'text'): data['array'][0]['text'],
        ('array', 0, 'quantity'): data['array'][0]['quantity']
    }
    assert dict(data_iter(data, filter_property_types={'text'})) == {
        ('name',): data['name'],
        ('array', 0, 'text'): data['array'][0]['text'],
    }
    assert dict(data_iter(data, filter_property_types={'object'})) == {
        (): data,
        ('array', 0): data['array'][0],
    }
