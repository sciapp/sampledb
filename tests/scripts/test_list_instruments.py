# coding: utf-8
"""

"""

import pytest
from sampledb.logic.instruments import create_instrument, get_instruments
import sampledb.__main__ as scripts


@pytest.fixture
def instruments():
    return [
        create_instrument(name, 'Example Instrument Description')
        for name in ['Instrument 1', 'Instrument 2']
    ]


def test_list_instruments(instruments, capsys):
    scripts.main([scripts.__file__, 'list_instruments'])
    output = capsys.readouterr()[0]
    instruments = get_instruments()
    for instrument in get_instruments():
        assert '- #{0}: {1}'.format(instrument.id, instrument.name) in output


def test_list_instruments_arguments(instruments, capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'list_instruments', 1])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
