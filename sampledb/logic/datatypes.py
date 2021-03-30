#!/usr/bin/env python3
# coding: utf-8

"""
This module defines a JSONEncoder and several data types which allow for de-/serialization to and from JSON using this
JSONEncoder. The format for serialized objects of these types is always a JavaScript object or Python dictionary,
containing a special attribute/key named '_type'. This value defines what class will be used for deserializing it, and
it also allows for some assumptions when dealing with the data, e.g. a "_type" equal to "quantity" guarantees that the
attribute/key "magnitude" will be exist and will be a Number.

While it would be simple to just verify this in Python, the advantage lies in using this information in a database,
where an invalid cast might lead to an erroneous query.

It has to be ensured, however, that no "_type" attribute or key can be set when not using these data types, as that
could potentially lead to the above assumptions and advantages being void. This can be verified when encoding by
setting JSONEncoder.STRICT = True, but the verification will greatly reduce the performance of the JSONEncoder.
"""

import datetime
import json
import pint

from .units import ureg

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class _ReducingEncoder(json.JSONEncoder):
    """
    A JSONEncoder subclass that replaces all objects of serializable types with an empty dictionary.

    This class is used for the _contains_type(obj) function and should not be re-used for other purposes.
    """
    def default(self, obj):
        for type_name, cls in JSONEncoder.serializable_types.items():
            if isinstance(obj, cls):
                return {}
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def _contains_type(obj):
    """
    This function checks whether a JSON-serializable object does not contain any "_type" attributes or keys.

    :param obj: the object to check, should be created using the _ReducingEncoder
    :return: True if the object contains _type, False otherwise
    """
    if isinstance(obj, dict):
        return any(key == '_type' or _contains_type(value) for key, value in obj.items())
    if isinstance(obj, list):
        return any(_contains_type(value) for value in obj)
    return False


class JSONEncoder(json.JSONEncoder):
    """
    A JSONEncoder with support for registering additional JSON-serializable types.
    """

    STRICT = False
    serializable_types = {}

    def encode(self, obj):
        if JSONEncoder.STRICT:
            # Create a version of the object without any objects that are instances of the serializable types
            reduced_obj = json.loads(json.dumps(obj, cls=_ReducingEncoder))
            assert not _contains_type(reduced_obj)
        return super(JSONEncoder, self).encode(obj)

    def default(self, obj):
        for type_name, cls in JSONEncoder.serializable_types.items():
            if isinstance(obj, cls):
                obj = obj.to_json()
                obj['_type'] = type_name
                return obj
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

    @classmethod
    def object_hook(cls, obj):
        """
        Function for json.loads() that will deserialize the objects serialized using default().

        :param obj: the dictionary to be deserialized
        :return: the deserialized object
        """
        if '_type' in obj:
            if obj['_type'] in cls.serializable_types:
                return cls.serializable_types[obj['_type']].from_json(obj)
        return obj

    @classmethod
    def serializable_type(cls, type_name):
        """
        Parameterized decorator that adds a class to the dictionary of serializable types using the given type name.
        """
        def serializable_type_decorator(c):
            cls.serializable_types[type_name] = c
            return c
        return serializable_type_decorator


@JSONEncoder.serializable_type('datetime')
class DateTime(object):
    JSON_SCHEMA = {
        'type': 'object',
        'properties': {
            '_type': {
                'enum': ['datetime']
            },
            'utc_datetime': {
                'type': 'string',
                'pattern': '^[0-9]{4}\\-[0-1][0-9]\\-[0-3][0-9]\\ [0-9]{2}:[0-9]{2}:[0-9]{2}$'
            }
        },
        'required': ['_type', 'utc_datetime'],
        'additionalProperties': False
    }

    FORMAT_STRING = '%Y-%m-%d %H:%M:%S'

    def __init__(self, utc_datetime=None):
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime.replace(microsecond=0)

    def __repr__(self):
        return '<{0}(utc_datetime={1})>'.format(type(self).__name__, self.utc_datetime.strftime(DateTime.FORMAT_STRING))

    def __eq__(self, other):
        return self.utc_datetime == other.utc_datetime

    def to_json(self):
        return {'utc_datetime': self.utc_datetime.strftime(DateTime.FORMAT_STRING)}

    @classmethod
    def from_json(cls, obj):
        return cls(datetime.datetime.strptime(obj['utc_datetime'], cls.FORMAT_STRING))


@JSONEncoder.serializable_type('quantity')
class Quantity(object):
    JSON_SCHEMA = {
        'type': 'object',
        'properties': {
            '_type': {
                'enum': ['quantity']
            },
            'dimensionality': {
                'type': 'string',
                'magnitude_in_base_units': 'string'
            },
            'magnitude_in_base_units': {
                'type': 'number'
            },
            'magnitude': {
                'type': 'number'
            },
            'units': {
                'anyOf': [
                    {'type': 'null'},
                    {'type': 'string'}
                ]
            }
        },
        'required': ['_type', 'dimensionality', 'magnitude_in_base_units', 'units'],
        'additionalProperties': False
    }

    def __init__(self, magnitude, units, already_in_base_units=False):
        self.magnitude = float(magnitude)
        if units is None:
            self.units = None
            self.pint_units = ureg.Unit('1')
            self.magnitude_in_base_units = self.magnitude
        else:
            if isinstance(units, ureg.Unit):
                self.pint_units = units
                self.units = str(self.pint_units)
            else:
                self.units = units
                try:
                    self.pint_units = ureg.Unit(self.units)
                except (pint.errors.UndefinedUnitError, AttributeError):
                    raise ValueError("Invalid units '{}'".format(self.units))
            if already_in_base_units is False:
                self.magnitude_in_base_units = ureg.Quantity(self.magnitude, self.pint_units).to_base_units().magnitude
            else:
                self.magnitude_in_base_units = self.magnitude
                pint_base_units = ureg.Quantity(1, self.pint_units).to_base_units().units
                self.magnitude = ureg.Quantity(self.magnitude_in_base_units, pint_base_units).to(self.pint_units).magnitude
        self.dimensionality = self.pint_units.dimensionality

    def __repr__(self):
        return '<{0}(magnitude={1.magnitude}, units="{1.units}")>'.format(type(self).__name__, self)

    def __eq__(self, other):
        return ureg.Quantity(self.magnitude, self.pint_units) == ureg.Quantity(other.magnitude, other.pint_units)

    def to_json(self):
        return {
            'magnitude': self.magnitude,
            'magnitude_in_base_units': self.magnitude_in_base_units,
            'units': self.units,
            'dimensionality': str(self.dimensionality)
        }

    @classmethod
    def from_json(cls, obj):
        magnitude_in_base_units = obj['magnitude_in_base_units']
        units = obj['units']
        if units is None:
            pint_units = ureg.Unit('1')
        else:
            try:
                pint_units = ureg.Unit(units)
            except (pint.errors.UndefinedUnitError, AttributeError):
                raise ValueError("Invalid units '{}'".format(units))

        if 'magnitude' in obj:
            magnitude = obj['magnitude']
        else:
            # convert magnitude back from base unit to desired unit
            pint_base_units = ureg.Quantity(1, pint_units).to_base_units().units
            magnitude = ureg.Quantity(magnitude_in_base_units, pint_base_units).to(pint_units).magnitude
        quantity = cls(magnitude, units)
        if pint_units.dimensionless:
            assert obj['dimensionality'] == 'dimensionless'
        else:
            assert (1 * pint_units).check(obj['dimensionality'])
        return quantity


@JSONEncoder.serializable_type('bool')
class Boolean(object):
    JSON_SCHEMA = {
        'type': 'object',
        'properties': {
            '_type': {
                'enum': ['bool']
            },
            'value': {
                'type': 'boolean'
            }
        },
        'required': ['_type', 'value'],
        'additionalProperties': False
    }

    def __init__(self, value):
        self.value = bool(value)

    def __repr__(self):
        return '<{0}(value={1.value})>'.format(type(self).__name__, self)

    def __eq__(self, other):
        return self.value == other.value

    def to_json(self):
        return {'value': self.value}

    @classmethod
    def from_json(cls, obj):
        return cls(obj['value'])


@JSONEncoder.serializable_type('text')
class Text(object):
    JSON_SCHEMA = {
        'type': 'object',
        'properties': {
            '_type': {
                'enum': ['text']
            },
            'text': {
                'type': 'string'
            }
        },
        'required': ['_type', 'text'],
        'additionalProperties': False
    }

    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return '<{0}(text="{1.text}")>'.format(type(self).__name__, self)

    def __eq__(self, other):
        return self.text == other.text

    def to_json(self):
        return {'text': self.text}

    @classmethod
    def from_json(cls, obj):
        return cls(obj['text'])
