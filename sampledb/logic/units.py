# coding: utf-8
"""

"""

import decimal
import os
import typing
import pint

from . import errors

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

ureg = pint.UnitRegistry(non_int_type=decimal.Decimal)
ureg.load_definitions(os.path.join(os.path.dirname(__file__), 'unit_definitions.txt'))

int_ureg = pint.UnitRegistry()
int_ureg.load_definitions(os.path.join(os.path.dirname(__file__), 'unit_definitions.txt'))


def prettify_units(units: typing.Optional[typing.Union[str, pint._typing.UnitLike]]) -> str:
    """
    Returns a prettified version of the units, if defined, otherwise returns the units unaltered.
    :param units: The pint units or their string representation
    :return: The prettified units
    """
    if units is None:
        units = '1'
    units_str = str(units).strip()
    units_str = {
        'degC': '\xb0C',
        'degree_Celsius': '\xb0C',
        'deg': '\xb0',
        'degree': '\xb0',
        'percent': '%',
        '': '—',
        '1': '—'
    }.get(units_str, units_str)
    return units_str


def get_dimensionality_for_units(units: typing.Optional[typing.Union[str, pint._typing.UnitLike]]) -> str:
    """
    Return the dimensionality of given units.

    :param units: the units to get the dimensionality for
    :return: dimensionality string in pint format
    :raise errors.InvalidUnitsError: if the units cannot be understood
    """
    if units is None:
        units = '1'
    try:
        return str(int_ureg.Unit(units).dimensionality)
    except Exception:
        raise errors.InvalidUnitsError()


def get_magnitude_in_base_units(
        magnitude: decimal.Decimal,
        units: typing.Union[str, pint._typing.UnitLike]
) -> decimal.Decimal:
    """
    Convert a given magnitude in a given unit to base units.

    :param magnitude: the given magnitude
    :param units: the units to get the dimensionality for
    :return: magnitude in base units
    :raise errors.InvalidUnitsError: if the units cannot be understood
    """
    try:
        return typing.cast(decimal.Decimal, ureg.Quantity(magnitude, ureg.Unit(units)).to_base_units().magnitude)
    except Exception:
        raise errors.InvalidUnitsError()
