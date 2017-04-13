# coding: utf-8
"""

"""

import typing
import pint

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

ureg = pint.UnitRegistry()


def prettify_units(units: typing.Union[str, ureg.Unit]):
    """
    Returns a prettified version of the units, if defined, otherwise returns the units unaltered.
    :param units: The pint units or their string representation
    :return: The prettified units
    """
    units = str(units)
    units = {
        'degC': '˚C'
    }.get(units, units)
    return units
