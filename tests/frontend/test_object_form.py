from sampledb.frontend.objects.object_form import get_errors_by_title


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
