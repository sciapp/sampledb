# coding: utf-8
"""

"""

import pytest
from sampledb.logic import instruments
import sampledb.__main__ as scripts
from ..test_utils import app_context




def test_create_instrument():
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    assert len(instruments.get_instruments()) == 0

    scripts.main([scripts.__file__, 'create_instrument', name, description])

    assert len(instruments.get_instruments()) == 1
    instrument = instruments.get_instruments()[0]
    assert instrument.name == name
    assert instrument.description == description
    assert len(instrument.responsible_users) == 0


def test_create_instrument_missing_arguments():
    assert len(instruments.get_instruments()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_instrument'])
    assert exc_info.value != 0
    assert len(instruments.get_instruments()) == 0


def test_create_existing_instrument():
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    instruments.create_instrument(name, description)
    assert len(instruments.get_instruments()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_instrument', name, description])
    assert exc_info.value != 0
    assert len(instruments.get_instruments()) == 1
