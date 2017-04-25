# coding: utf-8
"""

"""

import pytest
from sampledb.logic import instruments
import sampledb.__main__ as scripts
from ..test_utils import app_context


def test_update_instrument():
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    instrument = instruments.create_instrument(name, description)
    assert len(instruments.get_instruments()) == 1

    scripts.main([scripts.__file__, 'update_instrument', str(instrument.id), name, ''])

    assert len(instruments.get_instruments()) == 1
    instrument = instruments.get_instruments()[0]
    assert instrument.name == name
    assert instrument.description == ''
    assert len(instrument.responsible_users) == 0


def test_update_instrument_missing_arguments():
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    instrument = instruments.create_instrument(name, description)
    assert len(instruments.get_instruments()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument', str(instrument.id)])
    assert exc_info.value != 0
    assert len(instruments.get_instruments()) == 1
    instrument = instruments.get_instruments()[0]
    assert instrument.name == name
    assert instrument.description == description


def test_update_missing_instrument():
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    assert len(instruments.get_instruments()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument', str(1), name, description])
    assert exc_info.value != 0
    assert len(instruments.get_instruments()) == 0


def test_update_instrument_invalid_instrument_id():
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    instrument = instruments.create_instrument(name, description)
    assert len(instruments.get_instruments()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument', name, name, ""])
    assert exc_info.value != 0
    assert len(instruments.get_instruments()) == 1
    instrument = instruments.get_instruments()[0]
    assert instrument.name == name
    assert instrument.description == description
