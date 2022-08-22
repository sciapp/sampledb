# coding: utf-8
"""

"""

import pytest
from sampledb.logic.instruments import create_instrument, get_instruments
from sampledb.logic.instrument_translations import set_instrument_translation
from sampledb.logic.languages import Language
import sampledb.__main__ as scripts


@pytest.fixture
def instruments():
    return [
        create_instrument()
        for _ in range(3)
    ]


@pytest.fixture
def instrument_translations(instruments):
    return [
        set_instrument_translation(
            language_id=Language.ENGLISH,
            instrument_id=instrument.id,
            name=f"Instrument {i}",
            description="This is an example instrument"
        )
        for i, instrument in enumerate(instruments, start=1)
    ]


def test_list_instruments(instrument_translations, capsys):
    scripts.main([scripts.__file__, 'list_instruments'])
    output = capsys.readouterr()[0]
    for instrument in get_instruments():
        assert f'- #{instrument.id}: {instrument.name.get("en", "Unnamed Instrument")}' in output


def test_list_instruments_arguments(instrument_translations, capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'list_instruments', 1])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
