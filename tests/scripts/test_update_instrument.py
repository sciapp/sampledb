# coding: utf-8
"""

"""

import pytest
from sampledb.logic import instruments, instrument_translations, languages
import sampledb.__main__ as scripts


def test_update_instrument(capsys):
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    instrument = instruments.create_instrument()
    instrument_translations.set_instrument_translation(
        language_id=languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name=name,
        description=description
    )
    assert len(instruments.get_instruments()) == 1

    scripts.main([scripts.__file__, 'update_instrument', str(instrument.id), name, ''])
    assert "Success" in capsys.readouterr()[0]

    assert len(instruments.get_instruments()) == 1
    instrument = instruments.get_instruments()[0]
    assert len(instrument.responsible_users) == 0
    assert instrument.name['en'] == name
    assert instrument.description['en'] == ''


def test_update_instrument_missing_arguments(capsys):
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    instrument = instruments.create_instrument()
    instrument_translations.set_instrument_translation(
        language_id=languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name=name,
        description=description
    )
    assert len(instruments.get_instruments()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument', str(instrument.id)])
    assert exc_info.value != 0
    assert "Usage" in capsys.readouterr()[0]

    assert len(instruments.get_instruments()) == 1
    instrument = instruments.get_instruments()[0]
    assert instrument.name['en'] == name
    assert instrument.description['en'] == 'Example Instrument Description'


def test_update_missing_instrument(capsys):
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    assert len(instruments.get_instruments()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument', str(1), name, description])
    assert exc_info.value != 0
    assert "Error: no instrument with this id exists" in capsys.readouterr()[1]
    assert len(instruments.get_instruments()) == 0


def test_update_instrument_invalid_instrument_id(capsys):
    name = 'Example Instrument'
    description = 'Example Instrument Description'
    instrument = instruments.create_instrument()
    instrument_translations.set_instrument_translation(
        language_id=languages.Language.ENGLISH,
        instrument_id=instrument.id,
        name=name,
        description=description
    )
    assert len(instruments.get_instruments()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'update_instrument', name, name, ""])
    assert exc_info.value != 0
    assert "Error: instrument_id must be an integer" in capsys.readouterr()[1]

    assert len(instruments.get_instruments()) == 1
    instrument = instruments.get_instruments()[0]
    assert instrument.name['en'] == name
    assert instrument.description['en'] == 'Example Instrument Description'
