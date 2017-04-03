# coding: utf-8
"""

"""

import pint

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


# TODO: global unit registry
ureg = pint.UnitRegistry()


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
    """
    return str(ureg.Unit(units).dimensionality)
