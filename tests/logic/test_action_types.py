import pytest

from sampledb.logic import actions, errors, action_types


def test_check_action_type_exists():
    action_type = action_types.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
        disable_create_objects=False,
        is_template=False
    )
    action_types.check_action_type_exists(action_type.id)
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        action_types.check_action_type_exists(action_type.id + 1)
