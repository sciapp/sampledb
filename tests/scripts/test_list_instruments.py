# coding: utf-8
"""

"""

import pytest
from sampledb.logic.instruments import create_instrument
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
    for instrument_id, instrument_name in [(1, 'Instrument 1'), (2, 'Instrument 2')]:
        assert '- #{0}: {1}'.format(instrument_id, instrument_name) in output


def test_list_instruments_arguments(instruments, capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'list_instruments', 1])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
