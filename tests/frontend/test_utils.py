import copy
import datetime
import glob
import json
import os.path
import re

import markupsafe
import pytest
import pytz

import sampledb
import sampledb.frontend.utils as utils


def test_custom_format_number():
    assert utils.custom_format_number(0) == "0"
    assert utils.custom_format_number(10) == "10"
    assert utils.custom_format_number(0.1) == "0.1"
    assert utils.custom_format_number(0.12) == "0.12"
    assert utils.custom_format_number(0.123) == "0.123"
    assert utils.custom_format_number(0.1234) == "0.1234"
    assert utils.custom_format_number(0.12345) == "0.12345"
    assert utils.custom_format_number(0.123456) == "0.123456"
    assert utils.custom_format_number(0.1234567) == "0.1234567"
    assert utils.custom_format_number(0.12345678) == "0.12345678"
    assert utils.custom_format_number(0.123456789) == "0.123456789"
    assert utils.custom_format_number(0.1234567890) == "0.123456789"
    assert utils.custom_format_number(0.12345678901) == "0.12345678901"
    assert utils.custom_format_number(0.123456789012) == "0.123456789012"
    assert utils.custom_format_number(0.1234567890123) == "0.1234567890123"
    assert utils.custom_format_number(0.12345678901234) == "0.12345678901234"
    assert utils.custom_format_number(0.123456789012345) == "0.123456789012345"
    assert utils.custom_format_number(0.01) == "0.01"
    assert utils.custom_format_number(0.001) == "0.001"
    assert utils.custom_format_number(0.0001) == "0.0001"
    assert utils.custom_format_number(0.00001) == "1E-5"
    assert utils.custom_format_number(0.000001) == "1E-6"
    assert utils.custom_format_number(0.000000123456789) == "1.23456789E-7"
    assert utils.custom_format_number(100) == "100"
    assert utils.custom_format_number(1000) == "1000"
    assert utils.custom_format_number(10000) == "10000"
    assert utils.custom_format_number(100000) == "100000"
    assert utils.custom_format_number(1000000) == "1E6"
    assert utils.custom_format_number(1234567) == "1.234567E6"
    assert utils.custom_format_number(0.123, 0) == "0"
    assert utils.custom_format_number(0.123, 2) == "0.12"
    assert utils.custom_format_number(0.123, 4) == "0.1230"
    assert utils.custom_format_number(0.126, 2) == "0.13"
    assert utils.custom_format_number(100, 0) == "100"
    assert utils.custom_format_number(100, 2) == "100.00"
    assert utils.custom_format_number(0.001, 2) == "0.00"
    assert utils.custom_format_number(0.001, 4) == "0.0010"
    assert utils.custom_format_number(0.000001, 5) == "0.00000"
    assert utils.custom_format_number(0.000001, 8) == "1.00E-6"
    assert utils.custom_format_number(123456789, 2) == "1.2345678900E8"
    assert utils.custom_format_number(1E27) == "1E27"
    assert utils.custom_format_number(1E14, 0) == "1.00000000000000E14"
    assert utils.custom_format_number(1E14, 1) == "1.000000000000000E14"
    assert utils.custom_format_number(1E15, 0) == "1.000000000000000E15"
    # 15 display digits is the maximum, independent of the exponent
    assert utils.custom_format_number(1E15, 1) == "1.000000000000000E15"
    assert utils.custom_format_number(1E27, 1) == "1.000000000000000E27"
    assert utils.custom_format_number(1E25, 5) == "1.000000000000000E25"
    assert utils.custom_format_number(1E-127, 154) == "1.000000000000000E-127"
    assert utils.custom_format_number(1E-127, 155) == "1.000000000000000E-127"

    assert utils.custom_format_number(0, None, 2) == "00"
    assert utils.custom_format_number(1, None, 2) == "01"
    assert utils.custom_format_number(123, None, 2) == "123"
    assert utils.custom_format_number(10, 2, 3) == "010.00"

    for integer_digits in range(5):
        number = 1/3 + (10**integer_digits - 1) / 3
        assert utils.custom_format_number(number, 0) == ("0" if integer_digits == 0 else "3" * integer_digits)
        for display_digits in range(1, 28):
            assert utils.custom_format_number(number, display_digits) == ("0" if integer_digits == 0 else "3" * integer_digits) + "." + "3" * max(0, min(15, display_digits + integer_digits) - integer_digits)


def test_custom_format_quantity():
    assert utils.custom_format_quantity(
        data={
            '_type': 'quantity',
            'units': 'km',
            'magnitude_in_base_units': 1234,
            'magnitude': 1.234,
            'dimensionality': '[length]'
        },
        schema={
            'type': 'quantity',
            'title': 'example',
            'units': 'km',
            'dimensionality': '[length]',
            'display_digits': 2
        }
    ) == '1.23\u202fkm'


def test_relative_url_for(app):
    app.config['SERVER_NAME'] = 'https://localhost'
    with app.app_context():
        assert utils.relative_url_for('frontend.object', object_id=1) == 'objects/1'
        assert utils.relative_url_for('frontend.object', object_id=1, _external=True) == 'objects/1'


def test_fingerprinted_static_uses(app):
    sampledb_path = os.path.dirname(sampledb.__file__)
    template_path = os.path.join(sampledb_path, 'frontend', 'templates')
    static_path = os.path.join(sampledb_path, 'static')
    template_files = glob.glob('**/*.html', recursive=True, root_dir=template_path)
    static_files = glob.glob('**/*.*', recursive=True, root_dir=static_path)

    # dynamic uses of sampledb/img/ghs*.png
    assert 'sampledb/img/ghs01.png' in static_files
    special_matches = [
        "'sampledb/img/ghs0%d.png' | format(hazard_index"
    ]

    # allow duplicate usage of image files
    duplicate_matches = [
        static_file_name
        for static_file_name in static_files
        if static_file_name.startswith('sampledb/img/')
    ]

    uses_by_template = {}
    template_parents = {}

    for template_file_name in template_files:
        template_file_path = os.path.join(template_path, template_file_name)
        with open(template_file_path, 'r') as template_file:
            template_file_content = template_file.read()
            matches = re.findall(r'{% extends (.*?) %}', template_file_content)
            if matches:
                assert len(matches) == 1
                match = matches[0]
                if match not in (
                        'get_view_property_template(schema, container_style)',
                        'get_form_property_template(schema, container_style)',
                        'get_inline_edit_property_template(schema, container_style)'
                ):
                    assert match[0] in '\'"'
                    parent_template_name = match[1:-1]
                    template_parents[template_file_name] = parent_template_name
            uses_by_template[template_file_name] = []
            matches = re.findall(r'fingerprinted_static\((.*?)\)', template_file_content)
            if matches:
                for match in matches:
                    if match in special_matches:
                        continue
                    assert match[0] == match[-1]
                    assert match[0] in '\'"'
                    static_file_name = match[1:-1]
                    assert static_file_name in static_files
                    if static_file_name in duplicate_matches:
                        continue
                    uses_by_template[template_file_name].append(static_file_name)
            matches = re.findall(r'url_for\((.*?)\)', template_file_content)
            if matches:
                for match in matches:
                    quoted_endpoint = match.split(',')[0].strip()
                    assert quoted_endpoint[0] == quoted_endpoint[-1]
                    assert quoted_endpoint[0] in '\'"'
                    endpoint = quoted_endpoint[1:-1]
                    assert endpoint != 'static'
                    assert not endpoint.endswith('.static')

    template_file_names_to_check = copy.deepcopy(template_files)
    while template_file_names_to_check:
        template_file_name = template_file_names_to_check.pop(0)
        if template_file_name in template_parents:
            parent_template_name = template_parents[template_file_name]
            if parent_template_name in template_file_names_to_check:
                template_file_names_to_check.append(template_file_name)
                continue
            uses_by_template[template_file_name].extend(uses_by_template[parent_template_name])
        assert len(uses_by_template[template_file_name]) == len(set(uses_by_template[template_file_name]))


def test_get_basic_group_name_prefixes():
    user = sampledb.logic.users.create_user(
        name="Test User",
        email="example@example.org",
        type=sampledb.models.UserType.PERSON
    )
    group = sampledb.logic.groups.create_group(
        name={'en': 'Example Group'},
        description={'en': ''},
        initial_user_id=user.id
    )
    assert utils.get_basic_group_name_prefixes(group.id) == []
    category_a = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Category A'},
        parent_category_id=None
    )
    sampledb.logic.group_categories.set_basic_group_categories(
        basic_group_id=group.id,
        category_ids=[category_a.id]
    )
    assert utils.get_basic_group_name_prefixes(group.id) == [
        f"Category A / "
    ]
    category_b = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Category B'},
        parent_category_id=category_a.id
    )
    sampledb.logic.group_categories.set_basic_group_categories(
        basic_group_id=group.id,
        category_ids=[category_a.id, category_b.id]
    )
    assert utils.get_basic_group_name_prefixes(group.id) == [
        f"Category A / ",
        f"Category A / Category B / ",
    ]


def test_get_project_group_name_prefixes():
    user = sampledb.logic.users.create_user(
        name="Test User",
        email="example@example.org",
        type=sampledb.models.UserType.PERSON
    )
    project_a = sampledb.logic.projects.create_project(
        name={'en': 'Project A'},
        description={'en': ''},
        initial_user_id=user.id
    )
    assert utils.get_project_group_name_prefixes(project_a.id) == []
    category_a = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Category A'},
        parent_category_id=None
    )
    sampledb.logic.group_categories.set_project_group_categories(
        project_group_id=project_a.id,
        category_ids=[category_a.id]
    )
    assert utils.get_project_group_name_prefixes(project_a.id) == [
        f"Category A / "
    ]
    category_b = sampledb.logic.group_categories.create_group_category(
        name={'en': 'Category B'},
        parent_category_id=category_a.id
    )
    sampledb.logic.group_categories.set_project_group_categories(
        project_group_id=project_a.id,
        category_ids=[category_a.id, category_b.id]
    )
    assert utils.get_project_group_name_prefixes(project_a.id) == [
        f"Category A / ",
        f"Category A / Category B / ",
    ]
    project_b = sampledb.logic.projects.create_project(
        name={'en': 'Project B'},
        description={'en': ''},
        initial_user_id=user.id
    )
    assert utils.get_project_group_name_prefixes(project_a.id) == [
        f"Category A / ",
        f"Category A / Category B / ",
    ]
    sampledb.logic.projects.create_subproject_relationship(project_b.id, project_a.id)
    assert utils.get_project_group_name_prefixes(project_a.id) == [
        f"Category A / ",
        f"Category A / Category B / ",
        f"Project B / ",
    ]
    sampledb.logic.group_categories.set_project_group_categories(
        project_group_id=project_b.id,
        category_ids=[category_a.id, category_b.id]
    )
    assert utils.get_project_group_name_prefixes(project_a.id) == [
        f"Category A / ",
        f"Category A / Category B / ",
        f"Category A / Category B / Project B / ",
        f"Category A / Project B / ",
    ]


def test_custom_format_quantity_time():
    schema = {
        'type': 'quantity',
        'title': 'example',
        'units': ['min', 'h'],
        'dimensionality': '[time]'
    }
    data = {
        '_type': 'quantity',
        'units': 'h',
        'magnitude_in_base_units': 0.0,
        'magnitude': 0.0,
        'dimensionality': '[time]'
    }
    assert utils.custom_format_quantity(data, schema) == '00:00:00\u202fh'

    data['units'] = 'min'
    assert utils.custom_format_quantity(data, schema) == '00:00\u202fmin'

    data['units'] = 'min'
    data['magnitude_in_base_units'] = 12.5 * 60 + 0.2
    data['magnitude'] = 12.5 + 0.2 / 60
    assert utils.custom_format_quantity(data, schema) == '12:30.2\u202fmin'

    data['units'] = 'h'
    data['magnitude_in_base_units'] = 5
    data['magnitude'] = 5 / 3600
    assert utils.custom_format_quantity(data, schema) == '00:00:05\u202fh'

    data['units'] = 'h'
    data['magnitude_in_base_units'] = ((30 * 60) + 15) * 60 + 30.1
    data['magnitude'] = 30 + 15 / 60 + 30.1 / 3600
    assert utils.custom_format_quantity(data, schema) == '30:15:30.1\u202fh'

    data['units'] = 'min'
    data['magnitude_in_base_units'] = 5
    data['magnitude'] = 5 / 60
    assert utils.custom_format_quantity(data, schema) == '00:05\u202fmin'

    data['units'] = 'h'
    data['magnitude_in_base_units'] = 5 * 60
    data['magnitude'] = 5 / 60
    assert utils.custom_format_quantity(data, schema) == '00:05:00\u202fh'

    data['units'] = 'min'
    data['magnitude_in_base_units'] = 5 * 60
    data['magnitude'] = 5
    assert utils.custom_format_quantity(data, schema) == '05:00\u202fmin'

    data['units'] = 'h'
    data['magnitude_in_base_units'] = 5 * 3600
    data['magnitude'] = 5
    assert utils.custom_format_quantity(data, schema) == '05:00:00\u202fh'

    data['units'] = 'h'
    data['magnitude_in_base_units'] = ((30 * 60) + 15) * 60 + 30.0000000001
    data['magnitude'] = 30 + 15 / 60 + 30.0000000001 / 3600
    assert utils.custom_format_quantity(data, schema) == '30:15:30.0000000001\u202fh'

    data['units'] = 'min'
    data['magnitude_in_base_units'] = 12.5 * 60 + 0.00123
    data['magnitude'] = 12.5 + 0.00123 / 60
    schema['display_digits'] = 4
    assert utils.custom_format_quantity(data, schema) == '12:30.0012\u202fmin'

    data['units'] = 'h'
    data['magnitude_in_base_units'] = 12.5 * 60 + 0.00123
    data['magnitude'] = 12.5 / 60 + 0.00123 / 3600
    schema['display_digits'] = 4
    assert utils.custom_format_quantity(data, schema) == '00:12:30.0012\u202fh'

    data['units'] = 'h'
    data['magnitude_in_base_units'] = ((30 * 60) + 15) * 60 + 30.1
    data['magnitude'] = 30 + 15 / 60 + 30.1 / 3600
    schema['display_digits'] = 5
    assert utils.custom_format_quantity(data, schema) == '30:15:30.10000\u202fh'


def test_get_search_paths():
    assert utils.get_search_paths([], []) == (
        {},
        {},
        {}
    )
    all_action_types = sampledb.logic.action_types.get_action_types()
    assert utils.get_search_paths([], all_action_types) == (
        {},
        {},
        {
            action_type.id: {}
            for action_type in all_action_types
        }
    )
    schema = {
        "type": "object",
        "title": "Object",
        "properties": {
            "name": {
                "type": "text",
                "title": "Text"
            }
        },
        "required": [
            "name"
        ]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    assert utils.get_search_paths([], all_action_types) == (
        {},
        {},
        {
            action_type.id: {}
            for action_type in all_action_types
        }
    )
    assert utils.get_search_paths([action], all_action_types) == (
        {
            "name": {
                "types": ["text"],
                "titles": ["Text"]
            }
        },
        {
            action.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                }
            }
        },
        {
            action_type.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                }
            } if action_type.id == sampledb.logic.action_types.ActionType.SAMPLE_CREATION else {}
            for action_type in all_action_types
        }
    )
    schema["properties"]["name"]["title"] = "Name"
    action2 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    assert utils.get_search_paths([action2], all_action_types) == (
        {
            "name": {
                "types": ["text"],
                "titles": ["Name"]
            }
        },
        {
            action2.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Name"]
                }
            }
        },
        {
            action_type.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Name"]
                }
            } if action_type.id == sampledb.logic.action_types.ActionType.SAMPLE_CREATION else {}
            for action_type in all_action_types
        }
    )
    assert utils.get_search_paths([action, action2], all_action_types) == (
        {
            "name": {
                "types": ["text"],
                "titles": ["Text", "Name"]
            }
        },
        {
            action.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                }
            },
            action2.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Name"]
                }
            }
        },
        {
            action_type.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text", "Name"]
                }
            } if action_type.id == sampledb.logic.action_types.ActionType.SAMPLE_CREATION else {}
            for action_type in all_action_types
        }
    )

    schema = {
        "type": "object",
        "title": "Object",
        "properties": {
            "name": {
                "type": "text",
                "title": "Text"
            },
            "other": {
                "type": "object_reference",
                "title": "Object Reference"
            }
        },
        "required": [
            "name"
        ]
    }
    action = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    assert utils.get_search_paths([action], all_action_types) == (
        {
            "name": {
                "types": ["text"],
                "titles": ["Text"]
            },
            "other": {
                "types": ["object_reference"],
                "titles": ["Object Reference"]
            }
        },
        {
            action.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                },
                "other": {
                    "types": ["object_reference"],
                    "titles": ["Object Reference"]
                }
            }
        },
        {
            action_type.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                },
                "other": {
                    "types": ["object_reference"],
                    "titles": ["Object Reference"]
                }
            } if action_type.id == sampledb.logic.action_types.ActionType.SAMPLE_CREATION else {}
            for action_type in all_action_types
        }
    )
    schema["properties"]["other"]["type"] = "text"
    action2 = sampledb.logic.actions.create_action(
        action_type_id=sampledb.logic.action_types.ActionType.SAMPLE_CREATION,
        schema=schema
    )
    assert utils.get_search_paths([action, action2], all_action_types, valid_property_types=("object_reference",)) == (
        {
            "other": {
                "types": ["object_reference"],
                "titles": ["Object Reference"]
            }
        },
        {
            action.id: {
                "other": {
                    "types": ["object_reference"],
                    "titles": ["Object Reference"]
                }
            },
            action2.id: {}
        },
        {
            action_type.id: {
                "other": {
                    "types": ["object_reference"],
                    "titles": ["Object Reference"]
                }
            } if action_type.id == sampledb.logic.action_types.ActionType.SAMPLE_CREATION else {}
            for action_type in all_action_types
        }
    )
    assert utils.get_search_paths([action, action2], all_action_types, valid_property_types=("object_reference",), include_file_name=True) == (
        {
            "other": {
                "types": ["object_reference"],
                "titles": ["Object Reference"]
            }
        },
        {
            action.id: {
                "other": {
                    "types": ["object_reference"],
                    "titles": ["Object Reference"]
                }
            },
            action2.id: {}
        },
        {
            action_type.id: {
                "other": {
                    "types": ["object_reference"],
                    "titles": ["Object Reference"]
                }
            } if action_type.id == sampledb.logic.action_types.ActionType.SAMPLE_CREATION else {}
            for action_type in all_action_types
        }
    )
    assert utils.get_search_paths([action, action2], all_action_types, valid_property_types=("text",), include_file_name=True) == (
        {
            "name": {
                "types": ["text"],
                "titles": ["Text"]
            },
            "other": {
                "types": ["text"],
                "titles": ["Object Reference"]
            },
            "file_name": {
                "types": ["text"],
                "titles": ["File Name"]
            }
        },
        {
            action.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                },
                "file_name": {
                    "types": ["text"],
                    "titles": ["File Name"]
                }
            },
            action2.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                },
                "other": {
                    "types": ["text"],
                    "titles": ["Object Reference"]
                },
                "file_name": {
                    "types": ["text"],
                    "titles": ["File Name"]
                }
            }
        },
        {
            action_type.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                },
                "other": {
                    "types": ["text"],
                    "titles": ["Object Reference"]
                },
                "file_name": {
                    "types": ["text"],
                    "titles": ["File Name"]
                }
            } if action_type.id == sampledb.logic.action_types.ActionType.SAMPLE_CREATION else {}
            for action_type in all_action_types
        }
    )
    assert utils.get_search_paths([action, action2], all_action_types, valid_property_types=("text",), include_file_name=False) == (
        {
            "name": {
                "types": ["text"],
                "titles": ["Text"]
            },
            "other": {
                "types": ["text"],
                "titles": ["Object Reference"]
            }
        },
        {
            action.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                }
            },
            action2.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                },
                "other": {
                    "types": ["text"],
                    "titles": ["Object Reference"]
                }
            }
        },
        {
            action_type.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                },
                "other": {
                    "types": ["text"],
                    "titles": ["Object Reference"]
                }
            } if action_type.id == sampledb.logic.action_types.ActionType.SAMPLE_CREATION else {}
            for action_type in all_action_types
        }
    )
    action_type = sampledb.logic.action_types.get_action_type(sampledb.logic.action_types.ActionType.SAMPLE_CREATION)
    sampledb.logic.action_types.update_action_type(
        action_type_id=action_type.id,
        admin_only=action_type.admin_only,
        show_on_frontpage=action_type.show_on_frontpage,
        show_in_navbar=action_type.show_in_navbar,
        show_in_object_filters=action_type.show_in_object_filters,
        enable_labels=action_type.enable_labels,
        enable_files=False,
        enable_locations=action_type.enable_locations,
        enable_publications=action_type.enable_publications,
        enable_comments=action_type.enable_comments,
        enable_activity_log=action_type.enable_activity_log,
        enable_related_objects=action_type.enable_related_objects,
        enable_project_link=action_type.enable_project_link,
        enable_instrument_link=action_type.enable_instrument_link,
        disable_create_objects=action_type.disable_create_objects,
        is_template=action_type.is_template,
        usable_in_action_type_ids=[other_action_type.id for other_action_type in action_type.usable_in_action_types],
        scicat_export_type=action_type.scicat_export_type,
    )
    all_action_types = sampledb.logic.action_types.get_action_types()
    # reload actions so they have the updated type
    action = sampledb.logic.actions.get_action(action.id)
    action2 = sampledb.logic.actions.get_action(action2.id)
    assert utils.get_search_paths([action, action2], all_action_types, valid_property_types=("text",), include_file_name=True) == (
        {
            "name": {
                "types": ["text"],
                "titles": ["Text"]
            },
            "other": {
                "types": ["text"],
                "titles": ["Object Reference"]
            }
        },
        {
            action.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                }
            },
            action2.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                },
                "other": {
                    "types": ["text"],
                    "titles": ["Object Reference"]
                }
            }
        },
        {
            action_type.id: {
                "name": {
                    "types": ["text"],
                    "titles": ["Text"]
                },
                "other": {
                    "types": ["text"],
                    "titles": ["Object Reference"]
                }
            } if action_type.id == sampledb.logic.action_types.ActionType.SAMPLE_CREATION else {}
            for action_type in all_action_types
        }
    )

def test_validate_orcid():
    for orcid in [
        '0000-0001-2345-6789',
        '0000-0001-2345-672X',
    ]:
        assert sampledb.frontend.utils.validate_orcid(orcid) == (True, orcid)
    for orcid in [
        '0000-0001-2345-6780',
        '0000-0000-0000-000',
        '0000-0000-0000-00000',
        '0000-0000-0000-00X0',
        '0000-0000-0000-000a',
    ]:
        assert sampledb.frontend.utils.validate_orcid(orcid) == (False, None)


@pytest.mark.parametrize(['timezone', 'lang_code', 'expected_date_str'], [
    ('UTC', 'en', 'Jan 2, 2024'),
    ('UTC', 'de', '02.01.2024'),
    ('America/Los_Angeles', 'en', 'Jan 1, 2024'),
    ('America/Los_Angeles', 'de', '01.01.2024')
])
def test_custom_format_date(timezone, lang_code, expected_date_str, mock_current_user):
    mock_current_user.settings['AUTO_TZ'] = False
    mock_current_user.settings['AUTO_LC'] = False
    mock_current_user.settings['TIMEZONE'] = timezone
    mock_current_user.timezone = timezone
    mock_current_user.set_language_by_lang_code(lang_code)
    example_datetime = datetime.datetime(2024, 1, 2, 3, 4, 5)
    assert utils.custom_format_date(example_datetime.strftime('%Y-%m-%d %H:%M:%S')) == expected_date_str
    assert utils.custom_format_date(example_datetime) == expected_date_str
    assert utils.custom_format_date(example_datetime.replace(tzinfo=datetime.timezone.utc)) == expected_date_str
    assert utils.custom_format_date(example_datetime.replace(tzinfo=datetime.timezone.utc).astimezone(pytz.timezone(timezone))) == expected_date_str

def test_plotly_base64_image_from_json():
    assert utils.plotly_base64_image_from_json({'invalid': 'ploty_json'}) is None
    with open(os.path.join(os.path.dirname(sampledb.__file__), 'scripts', 'demo_data', 'objects', 'plotly-example-data1.sampledb.json'), 'r') as f:
        plotly_json = json.load(f)
    assert utils.plotly_base64_image_from_json(plotly_json) is not None
