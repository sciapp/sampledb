# coding: utf-8
"""

"""

import os
import typing
import pint

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

ureg = pint.UnitRegistry()
ureg.load_definitions(os.path.join(os.path.dirname(__file__), 'unit_definitions.txt'))


def prettify_units(units: typing.Union[str, ureg.Unit]) -> str:
    """
    Returns a prettified version of the units, if defined, otherwise returns the units unaltered.
    :param units: The pint units or their string representation
    :return: The prettified units
    """
    units = str(units)
    units = {
        'degC': '\xb0C',
        'degree_Celsius': '\xb0C',
        'deg': '\xb0',
        'degree': '\xb0',
        'percent': '%'
    }.get(units, units)
    return units
