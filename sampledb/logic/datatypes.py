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
import decimal
import json
import typing

import pint

from .units import ureg, int_ureg, get_dimensionality_for_units

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class _ReducingEncoder(json.JSONEncoder):
    """
    A JSONEncoder subclass that replaces all objects of serializable types with an empty dictionary.

    This class is used for the _contains_type(obj) function and should not be re-used for other purposes.
    """
    def default(self, o: typing.Any) -> typing.Any:
        for cls in JSONEncoder.serializable_types.values():
            if isinstance(o, cls):
                return {}
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)


def _contains_type(obj: typing.Any) -> bool:
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

    STRICT: bool = False
    serializable_types: typing.Dict[str, typing.Any] = {}

    def encode(self, o: typing.Any) -> typing.Any:
        if JSONEncoder.STRICT:
            # Create a version of the object without any objects that are instances of the serializable types
            reduced_obj = json.loads(json.dumps(o, cls=_ReducingEncoder))
            assert not _contains_type(reduced_obj)
        return super().encode(o)

    def default(self, o: typing.Any) -> typing.Any:
        for type_name, cls in JSONEncoder.serializable_types.items():
            if isinstance(o, cls):
                o = o.to_json()
                o['_type'] = type_name
                return o
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)

    @classmethod
    def object_hook(cls, obj: typing.Any) -> typing.Any:
        """
        Function for json.loads() that will deserialize the objects serialized using default().

        :param obj: the dictionary to be deserialized
        :return: the deserialized object
        """
        if '_type' in obj:
            if obj['_type'] in cls.serializable_types:
                return cls.serializable_types[obj['_type']].from_json(obj)
        return obj

    T = typing.TypeVar('T')

    @classmethod
    def serializable_type(cls, type_name: str) -> typing.Callable[[T], T]:
        """
        Parameterized decorator that adds a class to the dictionary of serializable types using the given type name.
        """

        T2 = typing.TypeVar('T2')

        def serializable_type_decorator(c: T2) -> T2:
            cls.serializable_types[type_name] = c
            return c
        return serializable_type_decorator


@JSONEncoder.serializable_type('datetime')
class DateTime:
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

    def __init__(self, utc_datetime: typing.Optional[datetime.datetime] = None) -> None:
        if utc_datetime is None:
            utc_datetime = datetime.datetime.now(datetime.timezone.utc)
        self.utc_datetime = utc_datetime.replace(microsecond=0)

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(utc_datetime={self.utc_datetime.strftime(self.FORMAT_STRING)})>'

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.utc_datetime == other.utc_datetime

    def to_json(self) -> typing.Dict[str, str]:
        return {'utc_datetime': self.utc_datetime.strftime(self.FORMAT_STRING)}

    @classmethod
    def from_json(cls, obj: typing.Dict[str, str]) -> 'DateTime':
        return cls(datetime.datetime.strptime(obj['utc_datetime'], cls.FORMAT_STRING).replace(tzinfo=datetime.timezone.utc))


@JSONEncoder.serializable_type('quantity')
class Quantity:
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

    def __init__(
            self,
            magnitude: typing.Union[int, float, decimal.Decimal],
            units: typing.Optional[str],
            already_in_base_units: bool = False
    ) -> None:
        if units is None:
            self.units = None
            self.pint_units = ureg.Unit('1')
            self.magnitude = float(magnitude)
            self.magnitude_in_base_units = float(magnitude)
        else:
            if isinstance(units, ureg.Unit):
                self.pint_units = units
                self.units = str(self.pint_units)
            else:
                self.units = units
                try:
                    self.pint_units = ureg.Unit(self.units)
                except (pint.errors.UndefinedUnitError, AttributeError):
                    raise ValueError(f"Invalid units '{self.units}'")
            if already_in_base_units:
                magnitude_in_base_units = magnitude
                _, pint_base_units = ureg.get_base_units(self.pint_units)
                magnitude = ureg.Quantity(decimal.Decimal(magnitude), pint_base_units).to(self.pint_units).magnitude
            else:
                magnitude_in_base_units = ureg.Quantity(decimal.Decimal(magnitude), self.pint_units).to_base_units().magnitude
            self.magnitude = float(magnitude)
            self.magnitude_in_base_units = float(magnitude_in_base_units)
        # use integer unit registry to ensure compatible dimensionalities
        # e.g. [length] ** 2 instead of [length] * 2.000
        self.dimensionality = str(int_ureg.Unit(self.pint_units).dimensionality)

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(magnitude={self.magnitude}, units="{self.units}")>'

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.dimensionality == other.dimensionality and self.magnitude_in_base_units == other.magnitude_in_base_units

    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'magnitude': self.magnitude,
            'magnitude_in_base_units': self.magnitude_in_base_units,
            'units': self.units,
            'dimensionality': str(self.dimensionality)
        }

    @classmethod
    def from_json(cls, obj: typing.Dict[str, typing.Any]) -> 'Quantity':
        units = obj['units']
        if units is None:
            pint_units = ureg.Unit('1')
        else:
            try:
                pint_units = ureg.Unit(units)
            except (pint.errors.UndefinedUnitError, AttributeError):
                raise ValueError(f"Invalid units '{units}'")

        if 'magnitude' in obj:
            magnitude = obj['magnitude']
        else:
            # convert magnitude back from base unit to desired unit
            magnitude_in_base_units = obj['magnitude_in_base_units']
            pint_base_units = ureg.Quantity(1, pint_units).to_base_units().units
            magnitude = ureg.Quantity(decimal.Decimal(magnitude_in_base_units), pint_base_units).to(pint_units).magnitude
        quantity = cls(magnitude, units)
        if pint_units.dimensionless:
            assert obj['dimensionality'] == 'dimensionless'
        else:
            assert (1 * pint_units).check(obj['dimensionality'])
        return quantity


@JSONEncoder.serializable_type('bool')
class Boolean:
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

    def __init__(self, value: bool) -> None:
        self.value = bool(value)

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(value={self.value})>'

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.value == other.value

    def to_json(self) -> typing.Dict[str, bool]:
        return {'value': self.value}

    @classmethod
    def from_json(cls, obj: typing.Dict[str, bool]) -> 'Boolean':
        return cls(obj['value'])


@JSONEncoder.serializable_type('text')
class Text:
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

    def __init__(
            self,
            text: typing.Union[str, typing.Dict[str, str]]
    ) -> None:
        self.text = text

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(text="{self.text}")>'

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.text == other.text

    def to_json(self) -> typing.Dict[str, typing.Union[str, typing.Dict[str, str]]]:
        return {'text': self.text}

    @classmethod
    def from_json(cls, obj: typing.Dict[str, typing.Union[str, typing.Dict[str, str]]]) -> 'Text':
        return cls(obj['text'])


@JSONEncoder.serializable_type('timeseries')
class Timeseries:
    JSON_SCHEMA = {
        'type': 'object',
        'properties': {
            '_type': {
                'enum': ['timeseries']
            },
            'dimensionality': {
                'type': 'string'
            },
            'data': {
                'type': 'array',
                'items': {
                    'type': 'array',
                    'items': {
                        'anyOf': [
                            {'type': 'number'},
                            {'type': 'string'}
                        ]
                    }
                }
            },
            'units': {
                'anyOf': [
                    {'type': 'null'},
                    {'type': 'string'}
                ]
            }
        },
        'required': ['_type', 'dimensionality', 'data', 'units'],
        'additionalProperties': False
    }
    DATETIME_FORMAT_STRING = '%Y-%m-%d %H:%M:%S.%f'

    def __init__(
            self,
            data: typing.List[typing.List[typing.Union[int, float]]],
            units: typing.Optional[str]
    ) -> None:
        self.data = data
        if units is None:
            self.units = None
        else:
            self.units = str(units)
        self.dimensionality = get_dimensionality_for_units(units)

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(length={len(self.data)}, units="{self.units}")>'

    def __eq__(self, other: typing.Any) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.units == other.units and self.data == other.data

    def to_json(self) -> typing.Dict[str, typing.Any]:
        return {
            'data': self.data,
            'units': self.units,
            'dimensionality': self.dimensionality
        }

    @classmethod
    def from_json(cls, obj: typing.Dict[str, typing.Any]) -> 'Timeseries':
        return cls(obj['data'], obj['units'])
