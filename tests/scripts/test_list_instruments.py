# coding: utf-8
"""

"""

import pytest
import io
import sys
from sampledb.logic.instruments import create_instrument
import sampledb.__main__ as scripts
from ..test_utils import app_context


@pytest.fixture
def instruments():
    return [
        create_instrument(name, 'Example Instrument Description')
        for name in ['Instrument 1', 'Instrument 2']
    ]


def test_list_instruments(instruments):
    stdout = sys.stdout
    sys.stdout = io.StringIO()
    scripts.main([scripts.__file__, 'list_instruments'])
    sys.stdout.seek(0)
    output = sys.stdout.read()
    sys.stdout = stdout
    for instrument_id, instrument_name in [(1, 'Instrument 1'), (2, 'Instrument 2')]:
        assert '- #{0}: {1}'.format(instrument_id, instrument_name) in output


def test_list_instruments_arguments(instruments):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'list_instruments', 1])
    assert exc_info.value != 0
