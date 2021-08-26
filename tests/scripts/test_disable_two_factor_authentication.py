# coding: utf-8
"""

"""

import pytest
from sampledb.logic import users, authentication
import sampledb.__main__ as scripts


@pytest.fixture
def user_id():
    user = users.create_user('test', 'user_id@example.com', users.UserType.PERSON)
    method = authentication._create_two_factor_authentication_method(user.id, {'type': 'test'})
    authentication.activate_two_factor_authentication_method(method.id)
    assert user.id is not None
    return user.id


def test_disable_two_factor_authentication(capsys, user_id):
    assert authentication.get_active_two_factor_authentication_method(user_id) is not None
    scripts.main([scripts.__file__, 'disable_two_factor_authentication', str(user_id)])
    assert 'Success' in capsys.readouterr()[0]
    assert authentication.get_active_two_factor_authentication_method(user_id) is None

    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'disable_two_factor_authentication', str(user_id)])
    assert exc_info.value != 0
    assert 'Error' in capsys.readouterr()[1]
    assert authentication.get_active_two_factor_authentication_method(user_id) is None


def test_disable_two_factor_authentication_missing_arguments(capsys, user_id):
    assert authentication.get_active_two_factor_authentication_method(user_id) is not None
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'disable_two_factor_authentication'])
    assert exc_info.value != 0
    assert 'Usage' in capsys.readouterr()[0]
    assert authentication.get_active_two_factor_authentication_method(user_id) is not None


def test_disable_two_factor_authentication_invalid_user_id(capsys, user_id):
    assert authentication.get_active_two_factor_authentication_method(user_id) is not None
    with pytest.raises(SystemExit) as exc_info:
        scripts.main([scripts.__file__, 'disable_two_factor_authentication', 'user_id'])
    assert exc_info.value != 0
    assert 'Error' in capsys.readouterr()[1]
    assert authentication.get_active_two_factor_authentication_method(user_id) is not None

