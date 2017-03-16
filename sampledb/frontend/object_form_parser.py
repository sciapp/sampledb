# coding: utf-8
"""

"""

import os
import itertools
import pint
ureg = pint.UnitRegistry()
import json

from sampledb.rest_api.objects import SCHEMA_DIR


# TODO: handle errors

def parse_any_form_data(form_data, schema, id_prefix):
    if schema.get('type') == 'object':
        return parse_object_form_data(form_data, schema, id_prefix)
    elif schema.get('type') == 'array':
        return parse_array_form_data(form_data, schema, id_prefix)
    elif schema.get('$ref') == '#/definitions/text' or schema.get('allOf', [None])[0] == {'$ref': '#/definitions/text'}:
        return parse_text_form_data(form_data, schema, id_prefix)
    elif schema.get('$ref') == '#/definitions/datetime':
        return parse_datetime_form_data(form_data, schema, id_prefix)
    elif schema.get('$ref') == '#/definitions/bool':
        return parse_boolean_form_data(form_data, schema, id_prefix)
    elif schema.get('allOf', [None])[0] == {'$ref': '#/definitions/quantity'}:
        return parse_quantity_form_data(form_data, schema, id_prefix)
    raise ValueError('invalid schema')


def parse_text_form_data(form_data, schema, id_prefix):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix)]
    # TODO: validate schema?
    if keys != [id_prefix + '_text']:
        raise ValueError('invalid text form data')
    text = form_data.get(id_prefix + '_text', [''])[0]
    return {
        '_type': 'text',
        'text': str(text)
    }


def parse_quantity_form_data(form_data, schema, id_prefix):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix)]
    # TODO: validate schema?
    if set(keys) != {id_prefix + '_magnitude', id_prefix + '_units'} and keys != [id_prefix + '_magnitude']:
        raise ValueError('invalid quantity form data')
    magnitude = form_data[id_prefix + '_magnitude'][0].strip()
    if not magnitude:
        return None
    try:
        magnitude = float(magnitude)
    except ValueError:
        raise ValueError('invalid quantity form data')
    if id_prefix + '_units' in form_data:
        # TODO: handle exceptions
        units = form_data[id_prefix + '_units'][0]
        pint_units = ureg.Unit(units)
    else:
        units = '1'
        pint_units = ureg.Unit('1')
    dimensionality = str(pint_units.dimensionality)
    magnitude_in_base_units = ureg.Quantity(magnitude, pint_units).to_base_units().magnitude
    return {
        '_type': 'quantity',
        'magnitude_in_base_units': magnitude_in_base_units,
        'dimensionality': dimensionality,
        'units': units
    }


def parse_datetime_form_data(form_data, schema, id_prefix):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix)]
    # TODO: validate schema?
    if keys != [id_prefix + '_datetime']:
        raise ValueError('invalid datetime form data')
    datetime = form_data.get(id_prefix + '_datetime', [''])[0]
    return {
        '_type': 'datetime',
        'utc_datetime': str(datetime)
    }


def parse_boolean_form_data(form_data, schema, id_prefix):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix)]
    # TODO: validate schema?
    if set(keys) == {id_prefix + '_hidden', id_prefix + '_value'}:
        print(form_data[id_prefix + '_value'])
        value = True
    elif keys == [id_prefix + '_hidden']:
        value = False
    else:
        raise ValueError('invalid boolean form data')
    return {
        '_type': 'bool',
        'value': value
    }


def parse_array_form_data(form_data, schema, id_prefix):
    keys = [key for key in form_data.keys() if key.startswith(id_prefix)]
    item_schema = schema['items']
    item_indices = set()
    for key in keys:
        key_rest = key.replace(id_prefix, '', 1)
        if not key_rest.startswith('_'):
            raise ValueError('invalid array form data')
        key_parts = key_rest.split('_')
        if not key_parts[0] == '':
            raise ValueError('invalid array form data')
        try:
            item_index = int(key_parts[1])
        except ValueError:
            raise ValueError('invalid array form data')
        item_indices.add(item_index)
    items = []
    if item_indices:
        num_items = max([i for i in item_indices])+1
        for i in range(num_items):
            if i not in item_indices:
                items.append(None)
            else:
                item_id_prefix = id_prefix+'_{}'.format(i)
                items.append(parse_any_form_data(form_data, item_schema, item_id_prefix))
    return items


def parse_object_form_data(form_data, schema, id_prefix):
    assert schema['type'] == 'object'
    data = {}
    for property_name, property_schema in schema['properties'].items():
        property_id_prefix = id_prefix + '_' + property_name
        if any(key.startswith(id_prefix) for key in form_data.keys()):
            property = parse_any_form_data(form_data, property_schema, property_id_prefix)
            if property is not None:
                data[property_name] = property
    return data


def parse_form_data(form_data, schema):
    id_prefix = 'object'
    return parse_object_form_data(form_data, schema, id_prefix)
