import pytest

from sampledb.logic import actions, errors, action_types


def test_check_action_type_exists():
    action_type = action_types.create_action_type(
        False, True, True, True, True, True, True, True, True, True, True, False, False
    )
    action_types.check_action_type_exists(action_type.id)
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        action_types.check_action_type_exists(action_type.id + 1)
