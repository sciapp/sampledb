# coding: utf-8
"""

"""

import decimal
import functools
import json
import os
import typing
import pint
import pint.compat
import pint.facets.nonmultiplicative.definitions

from . import errors

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@functools.wraps(pint.compat.log)  # type: ignore
def _decimal_compatible_log(x: typing.Any) -> typing.Any:
    if isinstance(x, decimal.Decimal):
        return x.ln()
    return pint.compat.log(x)  # type: ignore


# monkey patch the log function used for non-multiplicative units in pint, as
# numpy.log (used by pint) expects the presence of a method log(), but the
# (natural) logarithm of a decimal.Decimal instance is calculated using ln().
pint.facets.nonmultiplicative.definitions.log = _decimal_compatible_log  # type: ignore

ureg = pint.UnitRegistry(non_int_type=decimal.Decimal)
ureg.load_definitions(os.path.join(os.path.dirname(__file__), 'unit_definitions.txt'))

int_ureg = pint.UnitRegistry()
int_ureg.load_definitions(os.path.join(os.path.dirname(__file__), 'unit_definitions.txt'))

with open(os.path.join(os.path.dirname(__file__), 'un_cefact_code_unit_pairs.json'), encoding='utf-8') as _json_file:
    _un_cefact_code_unit_pairs: typing.List[typing.Tuple[str, str]] = [
        (code, unit)
        for code, unit in json.load(_json_file)
    ]
_un_cefact_code_to_symbol = {
    code: unit
    for code, unit in _un_cefact_code_unit_pairs
}
_symbol_to_un_cefact_code = {
    unit: code
    for code, unit in _un_cefact_code_unit_pairs
}


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


@functools.cache
def get_un_cefact_code_for_unit(
        unit: str
) -> typing.Optional[str]:
    """
    Get the UN CEFACT code for a given unit.

    :param unit: the unit to get the UN CEFACT code for
    :return: the UN CEFACT code for the given unit, or None
    """
    code = _symbol_to_un_cefact_code.get(unit)
    if code is not None:
        return code
    try:
        pint_unit = ureg.Unit(unit)
    except Exception:
        return None
    for code, other_unit in _un_cefact_code_unit_pairs:
        try:
            pint_other_unit = ureg.Unit(other_unit)
        except Exception:
            continue
        if pint_other_unit == pint_unit:
            return code
    return None


@functools.cache
def get_unit_for_un_cefact_code(
        code: str
) -> typing.Optional[str]:
    """
    Get the unit for a given UN CEFACT code.

    :param code: the UN CEFACT code to get the unit for
    :return: the unit for the given UN CEFACT code, or None
    """
    unit = _un_cefact_code_to_symbol.get(code)
    if unit is None:
        return None
    try:
        ureg.Unit(unit)
    except Exception:
        return None
    return unit
