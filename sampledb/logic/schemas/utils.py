# coding: utf-8
"""

"""

import pint

from ..units import ureg
from ..errors import UndefinedUnitError

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def units_are_valid(units: str) -> bool:
    try:
        ureg.Unit(units)
        return True
    except pint.UndefinedUnitError:
        return False


def get_dimensionality_for_units(units: str) -> str:
    """
    Returns the units' dimensionality in the dimensionality syntax of the pint package.

    :param units: a valid
    :return: dimensionality as string
    :raise errors.UndefinedUnitError: if the units are undefined
    """
    try:
        return str(ureg.Unit(units).dimensionality)
    except pint.UndefinedUnitError:
        raise UndefinedUnitError()
