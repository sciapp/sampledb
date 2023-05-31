# coding: utf-8
"""

"""
import pytest

from sampledb.frontend.objects import object_form_parser


def test_parse_time_input(mock_current_user):
    schema = {
        'type': 'quantity',
        'title': 'Duration',
        'units': ['s', 'min', 'h']
    }
    form_data = {
        'object__duration__magnitude': ['12:20'],
        'object__duration__units': ['min']
    }
    id_prefix = 'object__duration'
    errors = {}

    # minutes, ":"-notation
    form_data['object__duration__magnitude'][0] = '12:30.20'
    form_data['object__duration__units'][0] = 'min'
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert abs(data['magnitude'] - (12.5 + 0.2 / 60)) <= 1e-12
    assert abs(data['magnitude_in_base_units'] - (12.5 * 60 + 0.2)) <= 1e-12
    assert data['units'] == 'min'
    assert data['dimensionality'] == '[time]'

    # minutes, ":"-notation, leading 0s
    form_data['object__duration__magnitude'][0] = '02:06.20'
    form_data['object__duration__units'][0] = 'min'
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert abs(data['magnitude'] - (2.1 + 0.2 / 60)) <= 1e-12
    assert abs(data['magnitude_in_base_units'] - (2.1 * 60 + 0.2)) <= 1e-12
    assert data['units'] == 'min'
    assert data['dimensionality'] == '[time]'

    # hours, ":"-notation
    form_data['object__duration__magnitude'][0] = '30:15:30.10'
    form_data['object__duration__units'][0] = 'h'
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert abs(data['magnitude'] - (30 + 15 / 60 + 30.1 / 3600)) <= 1e-12
    assert abs(data['magnitude_in_base_units'] - (((30 * 60) + 15) * 60 + 30.1)) <= 1e-12
    assert data['units'] == 'h'
    assert data['dimensionality'] == '[time]'

    form_data['object__duration__magnitude'][0] = '30:15'  # == '30:15:00'
    form_data['object__duration__units'][0] = 'h'
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert abs(data['magnitude'] - (30 + 15 / 60)) <= 1e-12
    assert abs(data['magnitude_in_base_units'] - (((30 * 60) + 15) * 60)) <= 1e-12
    assert data['units'] == 'h'
    assert data['dimensionality'] == '[time]'

    # seconds, ","-notation
    form_data['object__duration__magnitude'][0] = '12.20'
    form_data['object__duration__units'][0] = 's'
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert data['magnitude'] == 12.2
    assert data['magnitude_in_base_units'] == 12.2
    assert data['units'] == 's'
    assert data['dimensionality'] == '[time]'

    # minutes, ","-notation
    form_data['object__duration__magnitude'][0] = '12.5'
    form_data['object__duration__units'][0] = 'min'
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert data['magnitude'] == 12.5
    assert data['magnitude_in_base_units'] == 12.5 * 60
    assert data['units'] == 'min'
    assert data['dimensionality'] == '[time]'

    # hours, ","-notation
    form_data['object__duration__magnitude'][0] = '1.75'
    form_data['object__duration__units'][0] = 'h'
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert data['magnitude'] == 1.75
    assert data['magnitude_in_base_units'] == 1.75 * 3600
    assert data['units'] == 'h'
    assert data['dimensionality'] == '[time]'

    form_data['object__duration__magnitude'][0] = '10:05:17,321'  # locale en_US expects . as decimal point
    form_data['object__duration__units'][0] = 'h'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = '10:-5:00'
    form_data['object__duration__units'][0] = 'h'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2     # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = '1:10:20'
    form_data['object__duration__units'][0] = 'min'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = '10:5:17.3'
    form_data['object__duration__units'][0] = 's'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = 'three:five'
    form_data['object__duration__units'][0] = 'h'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = '1:20:'
    form_data['object__duration__units'][0] = 'h'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = ':20:'
    form_data['object__duration__units'][0] = 'h'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = ':20'
    form_data['object__duration__units'][0] = 'min'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = '1:3:00'
    form_data['object__duration__units'][0] = 'h'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = '1:3.5'
    form_data['object__duration__units'][0] = 'h'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units

    mock_current_user.set_language_by_lang_code('de')

    form_data['object__duration__magnitude'][0] = '10:05:17.321'  # locale de_DE expects , as decimal point
    form_data['object__duration__units'][0] = 'h'
    assert object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={}) is None
    assert len(errors) == 2  # two errors, for magnitude and units
    form_data['object__duration__magnitude'][0] = '30:15:30,10'
    form_data['object__duration__units'][0] = 'h'
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert abs(data['magnitude'] - (30 + 15 / 60 + 30.1 / 3600)) <= 1e-12
    assert abs(data['magnitude_in_base_units'] - (((30 * 60) + 15) * 60 + 30.1)) <= 1e-12
    assert data['units'] == 'h'
    assert data['dimensionality'] == '[time]'


@pytest.mark.parametrize("lang_code,decimal_separator,group_separator", [('en', '.', ','), ('de', ',', '.')])
def test_parse_quantity_input(mock_current_user, lang_code, decimal_separator, group_separator):
    id_prefix = 'object__quantity'
    schema = {
        'type': 'quantity',
        'title': 'Quantity',
        'units': ['m', 'ft']
    }
    form_data = {
        id_prefix + '__units': ['m']
    }

    mock_current_user.set_language_by_lang_code(lang_code)

    # valid input using decimal separator
    errors = {}
    form_data[id_prefix + '__magnitude'] = [f'1{decimal_separator}1']
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert not errors
    assert data['magnitude'] == 1.1
    assert data['magnitude_in_base_units'] == 1.1

    # invalid input using group separator
    errors = {}
    form_data[id_prefix + '__magnitude'] = [f'1{group_separator}1']
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert errors
    assert data is None

    # invalid input using group separator and very large numbers
    # (causes InvalidOperation error during parsing instead of ValueError)
    errors = {}
    form_data[id_prefix + '__magnitude'] = [f'100000000000000000000000000000000000000000000000{group_separator}1']
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert errors
    assert data is None

    # valid converted input
    form_data = {
        id_prefix + '__units': ['ft']
    }
    errors = {}
    form_data[id_prefix + '__magnitude'] = [f'1{decimal_separator}1']
    data = object_form_parser.parse_quantity_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert not errors
    assert data['magnitude'] == 1.1
    assert data['magnitude_in_base_units'] == 0.33528


def test_parse_timeseries_form_data(mock_current_user):
    id_prefix = 'object__timeseries'
    schema = {
        'type': 'timeseries',
        'title': 'Time Series',
        'units': ['g', 'kg']
    }
    form_data = {
        id_prefix + '__units': ['g'],
        id_prefix + '__data': ['']
    }

    form_data[id_prefix + '__data'][0] = '''"2023-01-02 03:04:05.678900",1.0
"2023-01-02 03:04:06.678900",2.0
'''
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert not errors
    assert data['data'] == [
        ["2023-01-02 03:04:05.678900", 1.0, 0.001],
        ["2023-01-02 03:04:06.678900", 2.0, 0.002]
    ]

    form_data[id_prefix + '__data'][0] = '''"2023-01-02 03:04:05.678900",3.0,0.003
"2023-01-02 03:04:06.678900",4.0,0.004
'''
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert not errors
    assert data['data'] == [
        ["2023-01-02 03:04:05.678900", 3.0, 0.003],
        ["2023-01-02 03:04:06.678900", 4.0, 0.004]
    ]

    form_data[id_prefix + '__data'][0] = '''"utc_datetime","magnitude","magnitude_in_base_units"
"2023-01-02 03:04:05.678900",5.0,0.005
"2023-01-02 03:04:06.678900",6.0,0.006
'''
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert not errors
    assert data['data'] == [
        ["2023-01-02 03:04:05.678900", 5.0, 0.005],
        ["2023-01-02 03:04:06.678900", 6.0, 0.006]
    ]

    form_data[id_prefix + '__data'][0] = '''"2023-01-02 03:04:05.678900",1.0
"2023-01-02 03:04:06.678900",2.0
'''
    form_data[id_prefix + '__units'][0] = "invalid units"
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert errors
    assert data is None

    form_data[id_prefix + '__data'][0] = '''"2023-01-02 03:04:05.678900",1.0,0.001
"2023-01-02 03:04:06.678900",2.0,0.003
'''
    form_data[id_prefix + '__units'][0] = "g"
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert errors
    assert data is None

    form_data[id_prefix + '__data'][0] = ""
    form_data[id_prefix + '__units'][0] = "g"
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, required=True, file_names_by_id={})
    assert not errors
    assert data['data'] == []

    form_data[id_prefix + '__data'][0] = ""
    form_data[id_prefix + '__units'][0] = "g"
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, required=False, file_names_by_id={})
    assert not errors
    assert data is None

    form_data[id_prefix + '__data'][0] = '''"2023-01-02 03:04:0500",1.0
"2023-01-02 03:04:06.678900",2.0
'''
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert errors
    assert data is None

    mock_current_user.timezone = 'Europe/Berlin'
    form_data[id_prefix + '__data'][0] = '''"2023-01-02 03:04:05.678900",1.0
"2023-01-02 03:04:06.678900",2.0
'''
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert not errors
    assert data['data'] == [
        ["2023-01-02 02:04:05.678900", 1.0, 0.001],
        ["2023-01-02 02:04:06.678900", 2.0, 0.002]
    ]

    form_data[id_prefix + '__data'][0] = '''"2023-01-02 03:04:05.678900",1.0
"2023-01-02 03:04:06.678900123",2.0
'''
    errors = {}
    data = object_form_parser.parse_timeseries_form_data(form_data, schema, id_prefix, errors, file_names_by_id={})
    assert errors
    assert data is None


def test_parse_file_form_data():
    id_prefix = 'object__file'
    schema = {
        'type': 'file',
        'title': 'Example File',
        'extensions': ['.txt']
    }

    form_data = {
        id_prefix + '__file_id': ['0']
    }
    errors = {}
    data = object_form_parser.parse_file_form_data(form_data, schema, id_prefix, errors, file_names_by_id={0: 'test.txt'})
    assert not errors
    assert data == {
        '_type': 'file',
        'file_id': 0
    }

    form_data = {
        id_prefix + '__file_id': ['2']
    }
    errors = {}
    data = object_form_parser.parse_file_form_data(form_data, schema, id_prefix, errors, file_names_by_id={1: 'test.txt'})
    assert errors
    assert data is None

    form_data = {
        id_prefix + '__file_id': ['1']
    }
    errors = {}
    data = object_form_parser.parse_file_form_data(form_data, schema, id_prefix, errors, file_names_by_id={1: 'test.png'})
    assert errors
    assert data is None

    form_data = {
        id_prefix + '__file_id': ['test.txt']
    }
    errors = {}
    data = object_form_parser.parse_file_form_data(form_data, schema, id_prefix, errors, file_names_by_id={1: 'test.txt'})
    assert errors
    assert data is None
