# coding: utf-8
"""

"""
import secrets

import pytest

import sampledb.logic.users
from sampledb.logic import users, authentication
import sampledb.__main__ as scripts


def test_create_other_user(capsys):
    assert len(users.get_users()) == 0
    name = 'username'
    email = 'example@example.com'

    scripts.main([scripts.__file__, 'create_other_user', name, email])
    output = capsys.readouterr()[0]
    assert 'Success' in output
    password = output.split("'")[1]
    assert len(password) == 32
    assert all((c in '0123456789abcdef') for c in password)

    assert len(users.get_users()) == 1
    user = users.get_users()[0]
    assert user.name == name
    assert user.email == email
    assert user.type == users.UserType.OTHER
    assert not authentication.login(name, "password")
    assert authentication.login(name, password)


def test_create_other_user_missing_arguments(capsys):
    assert len(users.get_users()) == 0
    name = 'username'

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_other_user', name])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
    assert len(users.get_users()) == 0


def test_create_other_user_empty_password(capsys):
    assert len(users.get_users()) == 0

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_other_user', 'username', ''])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
    assert len(users.get_users()) == 0


def test_create_other_user_empty_name(capsys):
    assert len(users.get_users()) == 0
    email = 'example@example.com'

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_other_user', '', email])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
    assert len(users.get_users()) == 0


def test_create_other_user_invalid_name(capsys):
    assert len(users.get_users()) == 0
    email = 'example@example.com'

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_other_user', 'invalid name', email])
    assert exc_info.value != 0
    assert 'Error: name may only contain lower case characters, digits and underscores' in capsys.readouterr()[1]
    assert len(users.get_users()) == 0


def test_create_other_user_duplicate_name(capsys):
    assert len(users.get_users()) == 0
    name = 'username'
    email = 'example@example.com'
    existing_user = sampledb.logic.users.create_user(name=name, email=email, type=sampledb.models.UserType.OTHER)
    sampledb.logic.authentication.add_other_authentication(
        user_id=existing_user.id,
        name=name,
        password=secrets.token_hex(32),
        confirmed=True
    )
    assert len(users.get_users()) == 1

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_other_user', name, email])
    assert exc_info.value != 0
    assert 'Error: name is already being used' in capsys.readouterr()[1]
    assert len(users.get_users()) == 1


def test_create_other_user_invalid_email(capsys):
    assert len(users.get_users()) == 0
    name = 'username'

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_other_user', name, 'example_at_example.org'])
    assert exc_info.value != 0
    assert 'Error: email must be a valid email address' in capsys.readouterr()[1]
    assert len(users.get_users()) == 0
