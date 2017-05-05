# coding: utf-8
"""

"""

import pytest
import sampledb
import sampledb.logic
import sampledb.models

from ..test_utils import app_context


def test_create_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.groups.Group.query.all()) == 0

    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)

    assert len(sampledb.models.groups.Group.query.all()) == 1
    group = sampledb.models.groups.Group.query.get(group_id)
    assert group is not None
    assert group.id == group_id
    assert group.name == "Example Group"
    assert group.description == ""


def test_create_group_with_user_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.groups.Group.query.all()) == 0

    with pytest.raises(sampledb.logic.groups.UserDoesNotExistError):
        sampledb.logic.groups.create_group("Example Group", "", user.id+1)

    assert len(sampledb.models.groups.Group.query.all()) == 0


def test_create_duplicate_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.groups.create_group("Example Group", "", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 1

    with pytest.raises(sampledb.logic.groups.GroupAlreadyExistsError):
        sampledb.logic.groups.create_group("Example Group", "", user.id)

    assert len(sampledb.models.groups.Group.query.all()) == 1


def test_create_group_with_empty_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.groups.Group.query.all()) == 0

    with pytest.raises(sampledb.logic.groups.InvalidGroupNameError):
        sampledb.logic.groups.create_group("", "", user.id)

    assert len(sampledb.models.groups.Group.query.all()) == 0


def test_create_group_with_long_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    assert len(sampledb.models.groups.Group.query.all()) == 0

    with pytest.raises(sampledb.logic.groups.InvalidGroupNameError):
        sampledb.logic.groups.create_group("A"*101, "", user.id)

    assert len(sampledb.models.groups.Group.query.all()) == 0

    group_id = sampledb.logic.groups.create_group("A"*100, "", user.id)

    assert len(sampledb.models.groups.Group.query.all()) == 1
    group = sampledb.models.groups.Group.query.get(group_id)
    assert group is not None
    assert group.id == group_id
    assert group.name == "A"*100
    assert group.description == ""


def test_get_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 1

    group = sampledb.logic.groups.get_group(group_id)

    assert group.id == group_id
    assert group.name == "Example Group"
    assert group.description == ""


def test_get_group_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 1

    with pytest.raises(sampledb.logic.groups.GroupDoesNotExistError):
        sampledb.logic.groups.get_group(group_id+1)


def test_update_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 1

    sampledb.logic.groups.update_group(group_id, "Test Group", "Test Description")

    group = sampledb.models.groups.Group.query.get(group_id)
    assert group is not None
    assert group.id == group_id
    assert group.name == "Test Group"
    assert group.description == "Test Description"


def test_update_group_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 1

    with pytest.raises(sampledb.logic.groups.GroupDoesNotExistError):
        sampledb.logic.groups.update_group(group_id+1, "Test Group", "Test Description")

    group = sampledb.models.groups.Group.query.get(group_id)
    assert group is not None
    assert group.id == group_id
    assert group.name == "Example Group"
    assert group.description == ""


def test_update_group_with_existing_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.groups.create_group("Example Group", "", user.id)
    group_id = sampledb.logic.groups.create_group("Example Group 2", "", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 2

    with pytest.raises(sampledb.logic.groups.GroupAlreadyExistsError):
        sampledb.logic.groups.update_group(group_id, "Example Group", "")

    group = sampledb.models.groups.Group.query.get(group_id)
    assert group is not None
    assert group.id == group_id
    assert group.name == "Example Group 2"
    assert group.description == ""


def test_update_group_with_empty_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 1

    with pytest.raises(sampledb.logic.groups.InvalidGroupNameError):
        sampledb.logic.groups.update_group(group_id, "", "Test Description")

    group = sampledb.models.groups.Group.query.get(group_id)
    assert group is not None
    assert group.id == group_id
    assert group.name == "Example Group"
    assert group.description == ""


def test_update_group_with_long_name():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 1

    with pytest.raises(sampledb.logic.groups.InvalidGroupNameError):
        sampledb.logic.groups.update_group(group_id, "A"*101, "")

    group = sampledb.models.groups.Group.query.get(group_id)
    assert group is not None
    assert group.id == group_id
    assert group.name == "Example Group"
    assert group.description == ""

    sampledb.logic.groups.update_group(group_id, "A"*100, "")

    group = sampledb.models.groups.Group.query.get(group_id)
    assert group is not None
    assert group.id == group_id
    assert group.name == "A"*100
    assert group.description == ""


def test_delete_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.groups.create_group("Test Group", "Test Description", user.id)
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 2

    sampledb.logic.groups.delete_group(group_id)

    assert len(sampledb.models.groups.Group.query.all()) == 1
    group = sampledb.models.groups.Group.query.first()
    assert group is not None
    assert group.id != group_id
    assert group.name == "Test Group"
    assert group.description == "Test Description"


def test_delete_group_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Test Group", "Test Description", user.id)
    assert len(sampledb.models.groups.Group.query.all()) == 1

    with pytest.raises(sampledb.logic.groups.GroupDoesNotExistError):
        sampledb.logic.groups.delete_group(group_id+1)

    assert len(sampledb.models.groups.Group.query.all()) == 1
    group = sampledb.models.groups.Group.query.get(group_id)
    assert group is not None
    assert group.id == group_id
    assert group.name == "Test Group"
    assert group.description == "Test Description"


def test_add_user_to_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    assert len(group.members) == 1

    sampledb.logic.groups.add_user_to_group(group_id, user.id)

    assert len(group.members) == 2
    assert user in group.members


def test_add_user_to_group_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    assert len(group.members) == 1

    with pytest.raises(sampledb.logic.groups.GroupDoesNotExistError):
        sampledb.logic.groups.add_user_to_group(group_id+1, user.id)

    assert len(group.members) == 1


def test_add_user_that_does_not_exist_to_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    assert len(group.members) == 1

    with pytest.raises(sampledb.logic.groups.UserDoesNotExistError):
        sampledb.logic.groups.add_user_to_group(group_id, user.id+1)

    assert len(group.members) == 1


def test_add_user_that_is_already_a_member_to_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    assert len(group.members) == 1
    assert user in group.members

    with pytest.raises(sampledb.logic.groups.UserAlreadyMemberOfGroupError):
        sampledb.logic.groups.add_user_to_group(group_id, user.id)

    assert len(group.members) == 1
    assert user in group.members


def test_remove_user_from_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)

    group.members.append(user)
    sampledb.db.session.commit()

    assert len(group.members) == 2
    assert user in group.members

    sampledb.logic.groups.remove_user_from_group(group_id, user.id)

    assert len(group.members) == 1
    assert user not in group.members


def test_remove_last_user_from_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    assert len(group.members) == 1
    assert user in group.members

    sampledb.logic.groups.remove_user_from_group(group_id, user.id)

    assert len(sampledb.models.groups.Group.query.all()) == 0


def test_remove_user_from_group_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    assert len(group.members) == 1
    assert user in group.members

    with pytest.raises(sampledb.logic.groups.GroupDoesNotExistError):
        sampledb.logic.groups.remove_user_from_group(group_id+1, user.id)

    assert len(group.members) == 1
    assert user in group.members


def test_remove_user_that_does_not_exist_from_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    assert len(group.members) == 1
    assert user in group.members

    with pytest.raises(sampledb.logic.groups.UserDoesNotExistError):
        sampledb.logic.groups.remove_user_from_group(group_id, user.id+1)

    assert len(group.members) == 1
    assert user in group.members


def test_remove_user_that_is_not_a_member_from_group():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    assert len(group.members) == 1

    with pytest.raises(sampledb.logic.groups.UserNotMemberOfGroupError):
        sampledb.logic.groups.remove_user_from_group(group_id, user.id)

    assert len(group.members) == 1


def test_get_user_groups():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    sampledb.logic.groups.create_group("Test Group", "", user.id)
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    groups = sampledb.logic.groups.get_user_groups(user.id)

    assert len(groups) == 0

    group.members.append(user)
    sampledb.db.session.commit()

    groups = sampledb.logic.groups.get_user_groups(user.id)

    assert len(groups) == 1
    group = groups[0]
    assert group.id == group_id
    assert group.name == "Example Group"
    assert group.description == ""


def test_get_user_groups_for_user_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    with pytest.raises(sampledb.logic.groups.UserDoesNotExistError):
        sampledb.logic.groups.get_user_groups(user.id+1)


def test_get_group_member_ids():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    group = sampledb.models.groups.Group.query.get(group_id)

    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()

    member_ids = sampledb.logic.groups.get_group_member_ids(group_id)

    assert len(member_ids) == 1
    assert user.id not in member_ids

    group.members.append(user)
    sampledb.db.session.commit()

    member_ids = sampledb.logic.groups.get_group_member_ids(group_id)

    assert len(member_ids) == 2
    assert user.id in member_ids


def test_get_group_member_ids_for_group_that_does_not_exist():
    user = sampledb.models.User("Example User", "example@fz-juelich.de", sampledb.models.UserType.PERSON)
    sampledb.db.session.add(user)
    sampledb.db.session.commit()
    group_id = sampledb.logic.groups.create_group("Example Group", "", user.id)
    sampledb.models.groups.Group.query.get(group_id)

    with pytest.raises(sampledb.logic.groups.GroupDoesNotExistError):
        sampledb.logic.groups.get_group_member_ids(group_id+1)
