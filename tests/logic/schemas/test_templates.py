import pytest

import sampledb.logic


def test_update_template_action():
    template_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.TEMPLATE,
        schema={
            'title': 'Test Template',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'value': {
                    'title': 'Value',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    including_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema={
            'title': 'Test Action',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'template': {
                    'title': 'Template',
                    'type': 'object',
                    'template': template_action.id
                }
            },
            'required': ['name']
        }
    )
    assert including_action.schema == {
        'title': 'Test Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'template': {
                'title': 'Template',
                'type': 'object',
                'template': template_action.id,
                'properties': {
                    'value': {
                        'title': 'Value',
                        'type': 'text'
                    }
                },
                'required': []
            }
        },
        'required': ['name']
    }
    sampledb.logic.actions.update_action(
        action_id=template_action.id,
        schema={
            'title': 'Test Template',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'value': {
                    'title': 'Value',
                    'type': 'object_reference'
                }
            },
            'required': ['name', 'value']
        }
    )
    including_action = sampledb.logic.actions.get_action(including_action.id)
    assert including_action.schema == {
        'title': 'Test Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'template': {
                'title': 'Template',
                'type': 'object',
                'template': template_action.id,
                'properties': {
                    'value': {
                        'title': 'Value',
                        'type': 'object_reference'
                    }
                },
                'required': ['value']
            }
        },
        'required': ['name']
    }


def test_update_template_action_recursion():
    template_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.TEMPLATE,
        schema={
            'title': 'Test Template',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'value': {
                    'title': 'Value',
                    'type': 'text'
                }
            },
            'required': ['name']
        }
    )
    including_template_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.TEMPLATE,
        schema={
            'title': 'Including Template Action',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'template1': {
                    'title': 'Template',
                    'type': 'object',
                    'template': template_action.id
                }
            },
            'required': ['name']
        }
    )
    assert including_template_action.schema == {
        'title': 'Including Template Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'template1': {
                'title': 'Template',
                'type': 'object',
                'template': template_action.id,
                'properties': {
                    'value': {
                        'title': 'Value',
                        'type': 'text'
                    }
                },
                'required': []
            }
        },
        'required': ['name']
    }
    including_action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.TEMPLATE,
        schema={
            'title': 'Including Action',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'template': {
                    'title': 'Template',
                    'type': 'object',
                    'template': including_template_action.id
                }
            },
            'required': ['name']
        }
    )
    assert including_action.schema == {
        'title': 'Including Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'template': {
                'title': 'Template',
                'type': 'object',
                'template': including_template_action.id,
                'properties': {
                    'template1': {
                        'title': 'Template',
                        'type': 'object',
                        'template': template_action.id,
                        'properties': {
                            'value': {
                                'title': 'Value',
                                'type': 'text'
                            }
                        },
                        'required': []
                    }
                },
                'required': []
            }
        },
        'required': ['name']
    }

    # updating template_action should trigger an update in including_template_action and including_action
    sampledb.logic.actions.update_action(
        action_id=template_action.id,
        schema={
            'title': 'Test Template',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'value': {
                    'title': 'Value',
                    'type': 'object_reference'
                }
            },
            'required': ['name', 'value']
        }
    )
    including_action = sampledb.logic.actions.get_action(including_action.id)
    assert including_action.schema == {
        'title': 'Including Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'template': {
                'title': 'Template',
                'type': 'object',
                'template': including_template_action.id,
                'properties': {
                    'template1': {
                        'title': 'Template',
                        'type': 'object',
                        'template': template_action.id,
                        'properties': {
                            'value': {
                                'title': 'Value',
                                'type': 'object_reference'
                            }
                        },
                        'required': ['value']
                    }
                },
                'required': []
            }
        },
        'required': ['name']
    }
    including_template_action = sampledb.logic.actions.get_action(including_template_action.id)
    assert including_template_action.schema == {
        'title': 'Including Template Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'template1': {
                'title': 'Template',
                'type': 'object',
                'template': template_action.id,
                'properties': {
                    'value': {
                        'title': 'Value',
                        'type': 'object_reference'
                    }
                },
                'required': ['value']
            }
        },
        'required': ['name']
    }

    # updating including_template_action should trigger an update in including_action
    sampledb.logic.actions.update_action(
        action_id=including_template_action.id,
        schema={
            'title': 'Including Template Action',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                },
                'template1': {
                    'title': 'Template',
                    'type': 'object',
                    'template': template_action.id,
                    'properties': {},
                    'required': []
                },
                'template2': {
                    'title': 'Template',
                    'type': 'object',
                    'template': template_action.id,
                    'properties': {},
                    'required': []
                }
            },
            'required': ['name']
        }
    )
    including_action = sampledb.logic.actions.get_action(including_action.id)
    assert including_action.schema == {
        'title': 'Including Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'template': {
                'title': 'Template',
                'type': 'object',
                'template': including_template_action.id,
                'properties': {
                    'template1': {
                        'title': 'Template',
                        'type': 'object',
                        'template': template_action.id,
                        'properties': {
                            'value': {
                                'title': 'Value',
                                'type': 'object_reference'
                            }
                        },
                        'required': ['value']
                    },
                    'template2': {
                        'title': 'Template',
                        'type': 'object',
                        'template': template_action.id,
                        'properties': {
                            'value': {
                                'title': 'Value',
                                'type': 'object_reference'
                            }
                        },
                        'required': ['value']
                    }
                },
                'required': []
            }
        },
        'required': ['name']
    }
    including_template_action = sampledb.logic.actions.get_action(including_template_action.id)
    assert including_template_action.schema == {
        'title': 'Including Template Action',
        'type': 'object',
        'properties': {
            'name': {
                'title': 'Name',
                'type': 'text'
            },
            'template1': {
                'title': 'Template',
                'type': 'object',
                'template': template_action.id,
                'properties': {
                    'value': {
                        'title': 'Value',
                        'type': 'object_reference'
                    }
                },
                'required': ['value']
            },
            'template2': {
                'title': 'Template',
                'type': 'object',
                'template': template_action.id,
                'properties': {
                    'value': {
                        'title': 'Value',
                        'type': 'object_reference'
                    }
                },
                'required': ['value']
            }
        },
        'required': ['name']
    }


def test_enforce_permissions():
    user = sampledb.logic.users.create_user('Test User', 'example@example.com', sampledb.logic.users.UserType.PERSON)
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.TEMPLATE,
        schema={
            "title": "Schema",
            "type": "object",
            "properties": {
                "name": {
                    "title": "Name",
                    "type": "text"
                }
            },
            "required": ["name"]
        }
    )
    assert sampledb.logic.schemas.templates.find_invalid_template_paths(action.schema, user.id) == []
    schema = {
        "title": "Schema",
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "type": "text"
            },
            "array": {
                "type": "array",
                "title": "Array",
                "items": {
                    "type": "object",
                    "title": "Nested Object",
                    "template": action.id
                }
            }
        },
        "required": ["name"]
    }
    assert sampledb.logic.schemas.templates.find_invalid_template_paths(schema, user.id) == [
        ['array', '[?]']
    ]
    sampledb.logic.action_permissions.set_user_action_permissions(action.id, user.id, sampledb.models.permissions.Permissions.READ)
    assert sampledb.logic.schemas.templates.find_invalid_template_paths(schema, user.id) == []

def test_find_used_template_ids():
    assert sampledb.logic.schemas.templates.find_used_template_ids({
        "type": "object",
        "title": "Object",
        "properties": {
            "name": {
                "type": "text",
                "title": "Name"
            }
        },
        "required": ["name"]
    }) == set()
    assert sampledb.logic.schemas.templates.find_used_template_ids({
        "type": "object",
        "title": "Object",
        "properties": {
            "name": {
                "type": "text",
                "title": "Name"
            },
            "included_template": {
                "type": "object",
                "title": "Name",
                "template": 1,
                "properties": {}
            }
        },
        "required": ["name"]
    }) == {1}
    assert sampledb.logic.schemas.templates.find_used_template_ids({
        "type": "object",
        "title": "Object",
        "properties": {
            "name": {
                "type": "text",
                "title": "Name"
            },
            "included_template": {
                "type": "object",
                "title": "Name",
                "template": 1,
                "properties": {
                    "nested_template": {
                        "type": "object",
                        "title": "Name",
                        "template": 2,
                        "properties": {}
                    }
                }
            }
        },
        "required": ["name"]
    }) == {1, 2}
