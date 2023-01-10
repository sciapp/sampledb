import copy
import glob
import os.path
import re

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
    assert utils.custom_format_number(1E27, 0) == "1.000000000000000000000000000E27"
    # 27 display digits is the maximum, independent of the exponent
    assert utils.custom_format_number(1E27, 1) == "1.000000000000000000000000000E27"
    assert utils.custom_format_number(1E25, 5) == "1.000000000000000000000000000E25"
    assert utils.custom_format_number(1E-127, 154) == "1.000000000000000000000000000E-127"
    assert utils.custom_format_number(1E-127, 155) == "1.000000000000000000000000000E-127"

    assert utils.custom_format_number(0, None, 2) == "00"
    assert utils.custom_format_number(1, None, 2) == "01"
    assert utils.custom_format_number(123, None, 2) == "123"
    assert utils.custom_format_number(10, 2, 3) == "010.00"


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