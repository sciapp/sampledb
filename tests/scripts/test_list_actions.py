# coding: utf-8
"""

"""

import json
import os
import pytest
import sampledb.logic
import sampledb.__main__ as scripts


@pytest.fixture
def instrument():
    return sampledb.logic.instruments.create_instrument('Example Instrument', 'Example Instrument Description')


@pytest.fixture
def actions(instrument):
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'sampledb', 'schemas', 'minimal.json'))
    with open(schema_file_name) as schema_file:
        schema = json.load(schema_file)
    return [
        sampledb.logic.actions.create_action(
            instrument_id=instrument.id,
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
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
