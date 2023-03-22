import json

from sampledb.logic.schemas.data_diffs import calculate_diff, apply_diff


def test_data_diffs():
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
            }
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
            }
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
            }
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
            }
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
            }
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
            }
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
            }
        )
    ]
    for data_before, data_after in test_data:
        data_diff = calculate_diff(data_before, data_after)
        assert data_after == apply_diff(data_before, data_diff)
        # make sure the diff is JSON-serializable
        data_diff_after_serializing = json.loads(json.dumps(data_diff))
        assert data_diff == data_diff_after_serializing
