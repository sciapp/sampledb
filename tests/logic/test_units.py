# coding: utf-8
"""

"""
import decimal

import pytest

import sampledb.logic


def test_unit_registry():
    meter = sampledb.logic.units.ureg.Unit("m")
    inch = sampledb.logic.units.ureg.Unit("in")
    assert meter.dimensionality == inch.dimensionality


def test_custom_units():
    sccm = sampledb.logic.units.ureg.Unit("sccm")
    cubic_centimeter_per_minute = sampledb.logic.units.ureg.Unit("cm**3 / min")
    assert sccm.dimensionality == cubic_centimeter_per_minute.dimensionality
    one_sccm = sampledb.logic.units.ureg.Quantity("1sccm")
    one_cubic_centimeter_per_minute = sampledb.logic.units.ureg.Quantity("1 cm**3 / min")
    assert one_sccm.to_base_units() == one_cubic_centimeter_per_minute.to_base_units()


def test_prettify_degrees_celsius():
    celsius = sampledb.logic.units.ureg.Unit("degC")
    assert sampledb.logic.units.prettify_units(celsius) == '\xb0C'


@pytest.mark.parametrize(
    ['ureg'],
    [
        [sampledb.logic.units.ureg],
        [sampledb.logic.units.int_ureg]
    ]
)
def test_logarithmic_units(ureg):
    non_int_type = ureg.non_int_type
    one_mw_in_dbm = ureg.Quantity(non_int_type(0), ureg.Unit("dBm"))
    print(one_mw_in_dbm)
    one_mw_in_base_units = one_mw_in_dbm.to_base_units()
    assert one_mw_in_base_units.units == ureg.Unit('kg * m ** 2 / s ** 3')
    assert float(round(one_mw_in_base_units.magnitude, 15)) == 0.001
    one_mw_in_w = ureg.Quantity(non_int_type(0.001), ureg.Unit('W'))
    assert float(round(one_mw_in_w.to('dBm').magnitude, 15)) == 0
