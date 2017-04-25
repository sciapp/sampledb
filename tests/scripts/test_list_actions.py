# coding: utf-8
"""

"""

import json
import os
import pytest
import io
import sys
from sampledb.logic import instruments
import sampledb.__main__ as scripts
from ..test_utils import app_context


@pytest.fixture
def instrument():
    return instruments.create_instrument('Example Instrument', 'Example Instrument Description')


@pytest.fixture
def actions(instrument):
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    with open(schema_file_name) as schema_file:
        schema = json.load(schema_file)
    return [
        instruments.create_action(
            instrument_id=instrument.id,
            action_type=instruments.ActionType.SAMPLE_CREATION,
            name=name,
            description='',
            schema=schema
        )
        for name in ['Action 1', 'Action 2']
    ]


def test_list_actions(instrument, actions, capsys):
    scripts.main([scripts.__file__, 'list_actions'])
    output = capsys.readouterr()[0]
    for action_id, action_name in [(1, 'Action 1'), (2, 'Action 2')]:
        assert '- #{0}: {1}'.format(action_id, action_name) in output


def test_list_actions_arguments(instrument, actions, capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'list_actions', 1])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
