# coding: utf-8
"""

"""

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
