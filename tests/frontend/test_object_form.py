
import pytest
from selenium.webdriver.common.by import By

import sampledb
import sampledb.models
import sampledb.logic
from sampledb.frontend.objects.object_form import get_errors_by_title

from ..conftest import wait_for_page_load


@pytest.fixture
def user(flask_server):
    return sampledb.logic.users.create_user(name="Example User", email="example@example.com", type=sampledb.models.UserType.PERSON)


def test_get_errors_by_title_simple():
    assert get_errors_by_title({
        "object__name__text": "error message"
    }, {
        "type": "object",
        "title": "Object Information",
        "properties": {
            "name": {
                "type": "text",
                "title": "Object Name"
            }
        },
        "required": ["name"]
    }) == {
        "Object Name": {"error message"}
    }


def test_get_errors_by_title_translation():
    assert get_errors_by_title({
        "object__name__text": "error message"
    }, {
        "type": "object",
        "title": "Object Information",
        "properties": {
            "name": {
                "type": "text",
                "title": {"en": "Object Name", "de": "Objektname"}
            }
        },
        "required": ["name"]
    }) == {
        "Object Name": {"error message"}
    }


def test_get_errors_by_title_nested():
    assert get_errors_by_title({
        "object__nested_object__text__text": "error message"
    }, {
        "type": "object",
        "title": "Object Information",
        "properties": {
            "name": {
                "type": "text",
                "title": "Object Name"
            },
            "nested_object": {
                "type": "object",
                "title": "Nested Object",
                "properties": {
                    "text": {
                        "type": "text",
                        "title": "Nested Object Text"
                    }
                }
            }
        },
        "required": ["name"]
    }) == {
        "Nested Object ➜ Nested Object Text": {"error message"}
    }


def test_get_errors_by_title_nested_required():
    assert get_errors_by_title({
        "object__nested_object__text__text_languages": "The text must be at least 1 characters long.",
        "object__nested_object__text__text_en": "The text must be at least 1 characters long.",
        "object__nested_object__hidden": "missing required property \"text\" (at text)"
    }, {
        "type": "object",
        "title": "Object Information",
        "properties": {
            "name": {
                "type": "text",
                "title": "Object Name"
            },
            "nested_object": {
                "type": "object",
                "title": "Nested Object",
                "properties": {
                    "text": {
                        "type": "text",
                        "title": "Nested Object Text"
                    }
                },
                "required": ["text"]
            }
        },
        "required": ["name"]
    }) == {
        "Nested Object ➜ Nested Object Text": {"The text must be at least 1 characters long."}
    }


def test_get_errors_by_title_array():
    assert get_errors_by_title({
        "object__array__0__text": "error message"
    }, {
        "type": "object",
        "title": "Object Information",
        "properties": {
            "name": {
                "type": "text",
                "title": "Object Name"
            },
            "array": {
                "type": "array",
                "title": "Array",
                "items": {
                    "type": "text",
                    "title": "Array Entry Text"
                }
            }
        },
        "required": ["name"]
    }) == {
        "Array ➜ Array Entry Text #0": {"error message"}
    }


def test_get_errors_by_title_array_required():
    assert get_errors_by_title({
        "object__array__0__text__text": "error message",
        "object__array__0__hidden": 'missing required property "text" (at text)',
        "object__array__hidden": 'invalid type (at 0)',
        "object__hidden": 'missing required property "array" (at array)'
    }, {
        "type": "object",
        "title": "Object Information",
        "properties": {
            "name": {
                "type": "text",
                "title": "Object Name"
            },
            "array": {
                "type": "array",
                "title": "Array",
                "items": {
                    "type": "object",
                    "title": "Array Entry",
                    "properties": {
                        "text": {
                            "type": "text",
                            "title": "Array Entry Text"
                        }
                    }
                }
            }
        },
        "required": ["name"]
    }) == {
        "Array ➜ Array Entry #0 ➜ Array Entry Text": {"error message"}
    }


def test_get_errors_by_title_empty():
    assert get_errors_by_title({}, {
        "type": "object",
        "title": "Object Information",
        "properties": {
            "name": {
                "type": "text",
                "title": "Object Name"
            }
        },
        "required": ["name"]
    }) == {}


def test_get_errors_by_title_unknown():
    assert get_errors_by_title({
        "object__hidden": "error message"
    }, {
        "type": "object",
        "title": "Object Information",
        "properties": {
            "name": {
                "type": "text",
                "title": "Object Name"
            }
        },
        "required": ["name"]
    }) == {
        "Unknown (object__hidden)": {"error message"}
    }


def test_get_errors_by_title_duplicates():
    assert get_errors_by_title({
        "object__name__text_en": "error message",
        "object__name__text_languages": "error message"
    }, {
        "type": "object",
        "title": "Object Information",
        "properties": {
            "name": {
                "type": "text",
                "title": "Object Name"
            }
        },
        "required": ["name"]
    }) == {
        "Object Name": {"error message"}
    }


@pytest.mark.parametrize(
    [
        'existing_item',
        'default_item'
    ],
    [
        [
            [],
            [
                [
                    {
                        "_type": "text",
                        "text": "Test"
                    }
                ]
            ]
        ],
        [
            [
                [
                    {
                        "_type": "text",
                        "text": "Test"
                    }
                ]
            ],
            []
        ],
        [
            [
                [
                    {
                        "_type": "text",
                        "text": "Test"
                    }
                ]
            ],
            [
                [
                    {
                        "_type": "text",
                        "text": "A"
                    },
                    {
                        "_type": "text",
                        "text": "B"
                    },
                    {
                        "_type": "text",
                        "text": "C"
                    }
                ],
                [
                    {
                        "_type": "text",
                        "text": "D"
                    },
                    {
                        "_type": "text",
                        "text": "E"
                    },
                    {
                        "_type": "text",
                        "text": "F"
                    }
                ]
            ]
        ],
        [
            [
                [
                    {
                        "_type": "text",
                        "text": "A"
                    },
                    {
                        "_type": "text",
                        "text": "B"
                    },
                    {
                        "_type": "text",
                        "text": "C"
                    }
                ],
                [
                    {
                        "_type": "text",
                        "text": "D"
                    },
                    {
                        "_type": "text",
                        "text": "E"
                    },
                    {
                        "_type": "text",
                        "text": "F"
                    }
                ]
            ],
            [
                [
                    {
                        "_type": "text",
                        "text": "Test"
                    }
                ]
            ]
        ]
    ]
)
def test_copy_array_item_with_array_table(flask_server, driver, user, existing_item, default_item):
    schema = {
        "type": "object",
        "title": "Example Object",
        "properties": {
            "name": {
                "type": "text",
                "title": "Name"
            },
            "array": {
                "type": "array",
                "title": "Array",
                "items": {
                    "type": "array",
                    "title": "Array Table",
                    "style": "table",
                    "items": {
                        "type": "array",
                        "title": "Row",
                        "items": {
                            "type": "text",
                            "title": "Field"
                        }
                    },
                    "default": default_item
                },
                "default": [
                    existing_item
                ]
            }
        },
        "required": [
            "name"
        ]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        action_id=action.id,
        language_id=sampledb.models.Language.ENGLISH,
        name="Test Action"
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'objects/new?action_id={action.id}')
    with wait_for_page_load(driver):
        driver.find_element(By.ID, 'action_object__array__0__copy').click()
        driver.find_element(By.CSS_SELECTOR, '[name="action_submit"]').click()

    objects = sampledb.logic.objects.get_objects()
    assert len(objects) == 1
    assert objects[0].schema == action.schema
    assert objects[0].data == {
        'name': {
            '_type': 'text',
            'text': {'en': ''}
        },
        'array': [existing_item, existing_item]
    }


@pytest.mark.parametrize(
    [
        'existing_item',
        'default_item'
    ],
    [
        [
            [],
            [
                {
                    "a": {
                        "_type": "text",
                        "text": "Test"
                    }
                }
            ]
        ],
        [
            [
                {
                    "a": {
                        "_type": "text",
                        "text": "Test"
                    }
                }
            ],
            []
        ]
    ]
)
def test_copy_array_item_with_object_table(flask_server, driver, user, existing_item, default_item):
    schema = {
        "type": "object",
        "title": "Example Object",
        "properties": {
            "name": {
                "type": "text",
                "title": "Name"
            },
            "array": {
                "type": "array",
                "title": "Array",
                "items": {
                    "type": "array",
                    "title": "Table",
                    "style": "table",
                    "items": {
                        "type": "object",
                        "title": "Row",
                        "properties": {
                            "a": {
                                "type": "text",
                                "title": "A"
                            }
                        }
                    },
                    "default": default_item
                },
                "default": [
                    existing_item
                ]
            }
        },
        "required": [
            "name"
        ]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        action_id=action.id,
        language_id=sampledb.models.Language.ENGLISH,
        name="Test Action"
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'objects/new?action_id={action.id}')
    with wait_for_page_load(driver):
        driver.find_element(By.ID, 'action_object__array__0__copy').click()
        driver.find_element(By.CSS_SELECTOR, '[name="action_submit"]').click()

    objects = sampledb.logic.objects.get_objects()
    assert len(objects) == 1
    assert objects[0].schema == action.schema
    assert objects[0].data == {
        'name': {
            '_type': 'text',
            'text': {'en': ''}
        },
        'array': [existing_item, existing_item]
    }


@pytest.mark.parametrize(
    [
        'existing_item',
        'default_item'
    ],
    [
        [
            [
                {
                    "_type": "text",
                    "text": {"en": "Test"}
                }
            ],
            []
        ],
        [
            [],
            [
                {
                    "_type": "text",
                    "text": {"en": "Test"}
                }
            ]
        ]
    ]
)
def test_copy_array_item_with_array(flask_server, driver, user, existing_item, default_item):
    schema = {
        "type": "object",
        "title": "Example Object",
        "properties": {
            "name": {
                "type": "text",
                "title": "Name"
            },
            "array": {
                "type": "array",
                "title": "Array",
                "items": {
                    "type": "array",
                    "title": "Inner Array",
                    "items": {
                        "type": "text",
                        "title": "Item"
                    },
                    "default": default_item
                },
                "default": [
                    existing_item
                ]
            }
        },
        "required": [
            "name"
        ]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        action_id=action.id,
        language_id=sampledb.models.Language.ENGLISH,
        name="Test Action"
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'objects/new?action_id={action.id}')
    with wait_for_page_load(driver):
        driver.find_element(By.ID, 'action_object__array__0__copy').click()
        driver.find_element(By.CSS_SELECTOR, '[name="action_submit"]').click()

    objects = sampledb.logic.objects.get_objects()
    assert len(objects) == 1
    assert objects[0].schema == action.schema
    assert objects[0].data == {
        'name': {
            '_type': 'text',
            'text': {'en': ''}
        },
        'array': [existing_item, existing_item]
    }


@pytest.mark.parametrize(
    [
        'existing_item',
        'default_item'
    ],
    [
        [
            [
                {
                    "_type": "text",
                    "text": "Test"
                }
            ],
            []
        ],
        [
            [],
            [
                {
                    "_type": "text",
                    "text": "Test"
                }
            ]
        ]
    ]
)
def test_copy_array_item_with_list(flask_server, driver, user, existing_item, default_item):
    schema = {
        "type": "object",
        "title": "Example Object",
        "properties": {
            "name": {
                "type": "text",
                "title": "Name"
            },
            "array": {
                "type": "array",
                "title": "Array",
                "items": {
                    "type": "array",
                    "title": "Inner Array",
                    "style": "list",
                    "items": {
                        "type": "text",
                        "title": "Item"
                    },
                    "default": default_item
                },
                "default": [
                    existing_item
                ]
            }
        },
        "required": [
            "name"
        ]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    sampledb.logic.action_translations.set_action_translation(
        action_id=action.id,
        language_id=sampledb.models.Language.ENGLISH,
        name="Test Action"
    )
    sampledb.logic.action_permissions.set_action_permissions_for_all_users(action.id, sampledb.models.Permissions.READ)

    driver.get(flask_server.base_url + f'users/{user.id}/autologin')
    driver.get(flask_server.base_url + f'objects/new?action_id={action.id}')
    with wait_for_page_load(driver):
        driver.find_element(By.ID, 'action_object__array__0__copy').click()
        driver.find_element(By.CSS_SELECTOR, '[name="action_submit"]').click()

    objects = sampledb.logic.objects.get_objects()
    assert len(objects) == 1
    assert objects[0].schema == action.schema
    assert objects[0].data == {
        'name': {
            '_type': 'text',
            'text': {'en': ''}
        },
        'array': [existing_item, existing_item]
    }