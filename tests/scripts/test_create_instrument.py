# coding: utf-8
"""

"""

import pytest
from sampledb.logic import instruments
import sampledb.__main__ as scripts


def test_create_instrument(capsys):
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    assert len(instruments.get_instruments()) == 0

    scripts.main([scripts.__file__, 'create_instrument', name, description])
    assert 'Success' in capsys.readouterr()[0]

    assert len(instruments.get_instruments()) == 1
    instrument = instruments.get_instruments()[0]
    assert instrument.name == name
    assert instrument.description == description
    assert len(instrument.responsible_users) == 0


def test_create_instrument_missing_arguments(capsys):
    assert len(instruments.get_instruments()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_instrument'])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
    assert len(instruments.get_instruments()) == 0


def test_create_existing_instrument(capsys):
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    instruments.create_instrument(name, description)
    assert len(instruments.get_instruments()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_instrument', name, description])
    assert exc_info.value != 0
    assert 'Error: an instrument with this name already exists' in capsys.readouterr()[1]
    assert len(instruments.get_instruments()) == 1
