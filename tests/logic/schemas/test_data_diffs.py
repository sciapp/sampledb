import json

import pytest

import sampledb
from sampledb.logic.schemas.data_diffs import calculate_diff, apply_diff, VALUE_NOT_SET
from sampledb.logic.errors import DiffMismatchError


def test_data_diffs():
    german_language = sampledb.logic.languages.get_language_by_lang_code('de')
    sampledb.logic.languages.update_language(
        german_language.id,
        names=german_language.names,
        lang_code=german_language.lang_code,
        datetime_format_datetime=german_language.datetime_format_datetime,
        datetime_format_moment=german_language.datetime_format_moment,
        datetime_format_moment_output=german_language.datetime_format_moment_output,
        enabled_for_input=True,
        enabled_for_user_interface=german_language.enabled_for_user_interface
    )
    schema_before_1 = {
        'title': 'Example Schema 1',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text',
                'languages': ['en', 'de']
            },
            'array': {
                'title': 'Array',
                'type': 'array',
                'items': {
                    'title': 'Text',
                    'type': 'text'
                }
            }
        },
        'required': ['name']
    }
    schema_before_2 = {
        'title': 'Example Schema 1',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text',
                'languages': ['en', 'de']
            },
            'array': {
                'title': 'Array',
                'type': 'array',
                'items': {
                    'title': 'Array',
                    'type': 'array',
                    'items': {
                        'title': 'Text',
                        'type': 'text'
                    }
                }
            }
        },
        'required': ['name']
    }
    schema_before_3 = {
        'title': 'Example Schema 1',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text',
                'languages': ['en', 'de']
            },
            'array': {
                'title': 'Array',
                'type': 'array',
                'items': {
                    'title': 'Object',
                    'type': 'object',
                    'properties': {
                        'text1': {
                            'title': 'Text',
                            'type': 'text'
                        },
                        'text2': {
                            'title': 'Text',
                            'type': 'text'
                        }
                    }
                }
            }
        },
        'required': ['name']
    }
    test_data = [
        (
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                }
            },
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                }
            },
            schema_before_1
        ),
        (
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                }
            },
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name 2',
                        'de': 'Objektname 2'
                    }
                }
            },
            schema_before_1
        ),
        (
            {
                'name': {
                    '_type': 'text',
                    'text': 'Objektname'
                }
            },
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                }
            },
            schema_before_1
        ),
        (
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                },
                'array': [
                    {
                        '_type': 'text',
                        'text': 'Array Item 1'
                    },
                    {
                        '_type': 'text',
                        'text': 'Array Item 2'
                    }
                ]
            },
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                },
                'array': [
                    {
                        '_type': 'text',
                        'text': 'Array Item 1'
                    },
                    {
                        '_type': 'text',
                        'text': 'Array Item 2b'
                    },
                    {
                        '_type': 'text',
                        'text': 'Array Item 3'
                    }
                ]
            },
            schema_before_1
        ),
        (
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                },
                'array': [
                    {
                        '_type': 'text',
                        'text': 'Array Item 1'
                    },
                    {
                        '_type': 'text',
                        'text': 'Array Item 2'
                    },
                    {
                        '_type': 'text',
                        'text': 'Array Item 3'
                    }
                ]
            },
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                },
                'array': [
                    {
                        '_type': 'text',
                        'text': 'Array Item 1b'
                    },
                    {
                        '_type': 'text',
                        'text': 'Array Item 2'
                    }
                ]
            },
            schema_before_1
        ),
        (
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                },
                'array': [
                    [
                        {
                            '_type': 'text',
                            'text': 'Array Item 1'
                        },
                        {
                            '_type': 'text',
                            'text': 'Array Item 2'
                        }
                    ],
                    [
                        {
                            '_type': 'text',
                            'text': 'Array Item 3'
                        }
                    ]
                ]
            },
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                },
                'array': [
                    [
                        {
                            '_type': 'text',
                            'text': 'Array Item 1b'
                        },
                        {
                            '_type': 'text',
                            'text': 'Array Item 2'
                        }
                    ]
                ]
            },
            schema_before_2
        ),
        (
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                },
                'array': [
                    {
                        'text1': {
                            '_type': 'text',
                            'text': 'Array Item 1'
                        },
                        'text2': {
                            '_type': 'text',
                            'text': 'Array Item 2'
                        }
                    },
                    {
                        'text1': {
                            '_type': 'text',
                            'text': 'Array Item 3'
                        }
                    }
                ]
            },
            {
                'name': {
                    '_type': 'text',
                    'text': {
                        'en': 'Object Name',
                        'de': 'Objektname'
                    }
                },
                'array': [
                    {
                        'text1': {
                            '_type': 'text',
                            'text': 'Array Item 1b'
                        },
                        'text2': {
                            '_type': 'text',
                            'text': 'Array Item 2'
                        }
                    }
                ]
            },
            schema_before_3
        )
    ]
    for data_before, data_after, schema_before in test_data:
        data_diff = calculate_diff(data_before, data_after)
        assert data_after == apply_diff(data_before, data_diff, schema_before)
        # make sure the diff is JSON-serializable
        data_diff_after_serializing = json.loads(json.dumps(data_diff))
        assert data_diff == data_diff_after_serializing

    schema_before = {
        'title': 'Quantity',
        'type': 'quantity',
        'units': ['g']
    }
    data_before = sampledb.logic.datatypes.Quantity(magnitude=10, units='g').to_json()
    data_before['_type'] = 'quantity'
    data_diff = {
        '_before': {
            '_type': 'quantity',
            'units': 'g',
            'magnitude': 10
        }
    }
    assert VALUE_NOT_SET == apply_diff(data_before, data_diff, schema_before)

    data_diff = {
        '_before': {
            '_type': 'quantity',
            'units': 'g',
            'magnitude_in_base_units': 0.01
        }
    }
    assert VALUE_NOT_SET == apply_diff(data_before, data_diff, schema_before)

    data_diff = {
        '_before': {
            '_type': 'quantity',
            'units': 'g',
        }
    }
    with pytest.raises(DiffMismatchError):
        assert VALUE_NOT_SET == apply_diff(data_before, data_diff, schema_before)