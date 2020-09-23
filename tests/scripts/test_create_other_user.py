# coding: utf-8
"""

"""

import pytest
from sampledb.logic import users, authentication
import sampledb.__main__ as scripts


def test_create_other_user(capsys):
    assert len(users.get_users()) == 0
    name = 'username'
    email = 'example@fz-juelich.de'

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

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'create_other_user', '', 'password'])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
    assert len(users.get_users()) == 0
