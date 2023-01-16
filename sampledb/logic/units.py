# coding: utf-8
"""

"""

import decimal
import os
import typing
import pint

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

ureg = pint.UnitRegistry(non_int_type=decimal.Decimal)
ureg.load_definitions(os.path.join(os.path.dirname(__file__), 'unit_definitions.txt'))

int_ureg = pint.UnitRegistry()
int_ureg.load_definitions(os.path.join(os.path.dirname(__file__), 'unit_definitions.txt'))


def prettify_units(units: typing.Union[str, pint.Unit]) -> str:
    """
    Returns a prettified version of the units, if defined, otherwise returns the units unaltered.
    :param units: The pint units or their string representation
    :return: The prettified units
    """
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
