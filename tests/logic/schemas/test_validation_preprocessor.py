import pytest
import copy

import sampledb
from sampledb.logic.schemas.templates import reverse_substitute_templates
from sampledb.logic import errors
from sampledb.logic import actions

SCHEMA = {
        "title": "Example Action",
        "type": "object",
        "properties": {
            "name": {
                "title": "Example Attribute",
                "type": "text"
            }
        },
        "propertyOrder": [],
        "required": ["name"]
    }


@pytest.fixture
def template_action():
    action_schema = copy.deepcopy(SCHEMA)
    action_schema["properties"]["value"] = {
        "title": "Value",
        "type": "text"
    }
    return actions.create_action(action_type_id=sampledb.models.ActionType.TEMPLATE, schema=action_schema)


def test_substitute_templates_substitution_passes(template_action):
    base_action_schema = copy.deepcopy(SCHEMA)
    template_include_schema = {
            "type": "object",
            "title": "Template Include",
            "template": template_action.id
        }
    base_action_schema["properties"]["template_include"] = template_include_schema
    asserted_action_schema = {
        "title": "Example Action",
        "type": "object",
        "properties": {
            "name": {
                "title": "Example Attribute",
                "type": "text"
            },
            "template_include": {
                "type": "object",
                "title": "Template Include",
                "template": template_action.id,
                "properties": {
                    "value": {
                        "title": "Value",
                        "type": "text"
                    }
                },
                "propertyOrder": [],
                "required": []
            }
        },
        "propertyOrder": [],
        "required": ["name"]
    }
    stored_action = actions.create_action(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION, schema=base_action_schema)
    assert asserted_action_schema == stored_action.schema


def test_substitute_template_template_does_not_exist():
    action_schema = copy.deepcopy(SCHEMA)
    template_include_schema = {
        "title": "Template Include",
        "type": "object",
        "template": "200"
    }
    action_schema["properties"]["template_include"] = template_include_schema
    with pytest.raises(errors.ValidationError):
        actions.create_action(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION, schema=action_schema)


def test_substitute_template_template_properties_not_empty(template_action):
    action_schema = copy.deepcopy(SCHEMA)
    template_include_schema = {
        "title": "Template Include",
        "type": "object",
        "template": template_action.id,
        "properties": {
            "val": {
                "title": "Value",
                "type": "text"
            }
        }
    }
    action_schema["properties"]["template_include"] = template_include_schema
    stored_action = actions.create_action(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION, schema=action_schema)
    assert stored_action.schema == action_schema


def test_reverse_substitute_passes(template_action):
    action_schema = {
        "title": "Example Action",
        "type": "object",
        "properties": {
            "name": {
                "title": "Example Attribute",
                "type": "text"
            },
            "template_include": {
                "type": "object",
                "title": "Template Include",
                "template": f"{template_action.id}",
                "properties": {
                    "value": {
                        "title": "Value",
                        "type": "text"
                    }
                },
                "propertyOrder": [],
                "required": []
            }
        },
        "propertyOrder": [],
        "required": ["name"]
    }
    asserted_dict = {
            "title": "Example Action",
            "type": "object",
            "properties": {
                "name": {
                    "title": "Example Attribute",
                    "type": "text"
                },
                "template_include": {
                    "type": "object",
                    "title": "Template Include",
                    "template": f"{template_action.id}",
                    "properties": {},
                    "propertyOrder": [],
                    "required": []
                }
            },
            "propertyOrder": [],
            "required": ["name"]
        }
    reverse_substitute_templates(action_schema)
    assert asserted_dict == action_schema


def test_template_with_conditions(template_action):
    action_schema = {
        "title": "Example Action",
        "type": "object",
        "properties": {
            "name": {
                "title": "Example Attribute",
                "type": "text"
            },
            "checkbox": {
                "title": "Checkbox",
                "type": "bool"
            },
            "template_include": {
                "type": "object",
                "title": "Template Include",
                "template": template_action.id,
                "properties": {
                    "value": {
                        "title": "Value",
                        "type": "text"
                    }
                },
                "propertyOrder": [],
                "required": [],
                "conditions": [
                    {
                        "type": "bool_equals",
                        "property_name": "checkbox",
                        "value": True
                    }
                ]
            }
        },
        "propertyOrder": [],
        "required": ["name"]
    }
    asserted_dict = {
            "title": "Example Action",
            "type": "object",
            "properties": {
                "name": {
                    "title": "Example Attribute",
                    "type": "text"
                },
                "checkbox": {
                    "title": "Checkbox",
                    "type": "bool"
                },
                "template_include": {
                    "type": "object",
                    "title": "Template Include",
                    "template": template_action.id,
                    "properties": {},
                    "propertyOrder": [],
                    "required": [],
                    "conditions": [
                        {
                            "type": "bool_equals",
                            "property_name": "checkbox",
                            "value": True
                        }
                    ]
                }
            },
            "propertyOrder": [],
            "required": ["name"]
        }
    stored_action = actions.create_action(action_type_id=sampledb.models.ActionType.SAMPLE_CREATION, schema=action_schema)
    assert stored_action.schema == action_schema
    reverse_substitute_templates(action_schema)
    assert asserted_dict == action_schema
