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
    return sampledb.logic.instruments.create_instrument()


@pytest.fixture
def actions(instrument):
    schema_file_name = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'schemas', 'minimal.json'))
    with open(schema_file_name) as schema_file:
        schema = json.load(schema_file)
    actions = [
        sampledb.logic.actions.create_action(
            instrument_id=instrument.id,
            action_type_id=sampledb.models.ActionType.SAMPLE_CREATION,
            schema=schema
        )
        for _ in range(2)
    ]
    for i, action in enumerate(actions, start=1):
        sampledb.logic.action_translations.set_action_translation(
            language_id=sampledb.logic.languages.Language.ENGLISH,
            action_id=action.id,
            name=f'Action {i}'
        )
    return actions


def test_list_actions(instrument, actions, capsys):
    scripts.main([scripts.__file__, 'list_actions'])
    output = capsys.readouterr()[0]
    for action in sampledb.logic.actions.get_actions():
        assert '- #{0}: {1}'.format(action.id, action.name.get('en', 'Unnamed Action')) in output


def test_list_actions_arguments(instrument, actions, capsys):
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'list_actions', 1])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
