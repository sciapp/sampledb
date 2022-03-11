# coding: utf-8
"""

"""
import secrets
import pytest

from sampledb import logic
from sampledb.logic.authentication import _validate_password_hash
from sampledb.logic.component_authentication import add_own_token_authentication, add_token_authentication, \
    get_own_authentication, remove_own_component_authentication_method, remove_component_authentication_method, \
    login_via_component_token
from sampledb.logic.components import add_component
from sampledb.logic.errors import InvalidTokenError, NoAuthenticationMethodError, AuthenticationMethodDoesNotExistError
from sampledb.models import ComponentAuthentication, ComponentAuthenticationType, OwnComponentAuthentication


@pytest.fixture
def component():
    component = add_component(address=None, uuid='28b8d3ca-fb5f-59d9-8090-bfdbd6d07a71', name='Example Component', description='')
    return component


@pytest.fixture
def component2():
    component = add_component(address=None, uuid='cf7118a7-6976-5b1a-9a39-7adc72f591a4', name='Example Component 2', description='')
    return component


def test_add_token_authentication(component):
    assert len(ComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)
    description = 'Token description'

    add_token_authentication(component.id, token, description)

    assert len(ComponentAuthentication.query.all()) == 1

    auth = ComponentAuthentication.query.first()
    assert auth.component_id == component.id
    assert auth.login.get('login') == token[:8]
    assert _validate_password_hash(token[8:], auth.login.get('bcrypt_hash'))
    assert auth.login.get('description') == description
    assert auth.type == ComponentAuthenticationType.TOKEN


def test_add_token_authentication_invalid_token(component):
    assert len(ComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)[1:]
    description = 'Token description'

    with pytest.raises(InvalidTokenError):
        add_token_authentication(component.id, token, description)

    assert len(ComponentAuthentication.query.all()) == 0


def test_add_own_token_authentication(component):
    assert len(OwnComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)
    description = 'Token description'

    add_own_token_authentication(component.id, token, description)

    assert len(OwnComponentAuthentication.query.all()) == 1

    auth = OwnComponentAuthentication.query.first()
    assert auth.component_id == component.id
    assert auth.login.get('token') == token
    assert auth.login.get('description') == description
    assert auth.type == ComponentAuthenticationType.TOKEN


def test_add_own_token_authentication_invalid_token(component):
    assert len(OwnComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)[1:]
    description = 'Token description'

    with pytest.raises(InvalidTokenError):
        add_own_token_authentication(component.id, token, description)

    assert len(OwnComponentAuthentication.query.all()) == 0


def test_get_own_authentication(component):
    token = secrets.token_hex(32)
    description = 'Token description'

    assert len(OwnComponentAuthentication.query.all()) == 0
    add_own_token_authentication(component.id, token, description)
    assert len(OwnComponentAuthentication.query.all()) == 1

    auth = get_own_authentication(component.id)

    assert auth.component_id == component.id
    assert auth.login.get('token') == token
    assert auth.login.get('description') == description
    assert auth.type == ComponentAuthenticationType.TOKEN


def test_get_own_authentication_no_authentication(component):
    assert len(OwnComponentAuthentication.query.all()) == 0

    with pytest.raises(NoAuthenticationMethodError):
        get_own_authentication(component.id)


def test_remove_own_component_authentication_method(component):
    assert len(OwnComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)
    description = 'Token description'
    add_own_token_authentication(component.id, token, description)

    assert len(OwnComponentAuthentication.query.all()) == 1

    auth_id = get_own_authentication(component.id).id
    remove_own_component_authentication_method(auth_id)

    assert len(OwnComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)
    description = 'Token description 1'
    add_own_token_authentication(component.id, token, description)
    auth_id = get_own_authentication(component.id).id

    token = secrets.token_hex(32)
    description = 'Token description 2'
    add_own_token_authentication(component.id, token, description)

    assert len(OwnComponentAuthentication.query.all()) == 2

    remove_own_component_authentication_method(auth_id)

    assert len(OwnComponentAuthentication.query.all()) == 1
    assert len(OwnComponentAuthentication.query.filter_by(id=auth_id).all()) == 0


def test_remove_own_component_authentication_method_not_existing(component):
    assert len(OwnComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)
    description = 'Token description'
    add_own_token_authentication(component.id, token, description)

    assert len(OwnComponentAuthentication.query.all()) == 1

    auth_id = get_own_authentication(component.id).id
    with pytest.raises(AuthenticationMethodDoesNotExistError):
        remove_own_component_authentication_method(auth_id + 1)

    assert len(OwnComponentAuthentication.query.all()) == 1


def test_remove_component_authentication_method(component):
    assert len(ComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)
    description = 'Token description'
    add_token_authentication(component.id, token, description)

    assert len(ComponentAuthentication.query.all()) == 1

    auth_id = ComponentAuthentication.query.filter_by(component_id=component.id).first().id
    remove_component_authentication_method(auth_id)

    assert len(ComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)
    description = 'Token description 1'
    add_token_authentication(component.id, token, description)
    auth_id = ComponentAuthentication.query.filter_by(component_id=component.id).first().id

    token = secrets.token_hex(32)
    description = 'Token description 2'
    add_token_authentication(component.id, token, description)

    assert len(ComponentAuthentication.query.all()) == 2

    remove_component_authentication_method(auth_id)

    assert len(ComponentAuthentication.query.all()) == 1
    assert len(ComponentAuthentication.query.filter_by(id=auth_id).all()) == 0


def test_remove_component_authentication_method_not_existing(component):
    assert len(ComponentAuthentication.query.all()) == 0

    token = secrets.token_hex(32)
    description = 'Token description'
    add_token_authentication(component.id, token, description)

    assert len(ComponentAuthentication.query.all()) == 1

    auth_id = ComponentAuthentication.query.filter_by(component_id=component.id).first().id
    with pytest.raises(AuthenticationMethodDoesNotExistError):
        remove_component_authentication_method(auth_id + 1)

    assert len(ComponentAuthentication.query.all()) == 1


def test_login_via_component_token(component, component2):
    assert len(ComponentAuthentication.query.all()) == 0
    token1 = secrets.token_hex(32)
    description1 = 'Token description 1'
    add_token_authentication(component.id, token1, description1)
    token2 = secrets.token_hex(32)
    description2 = 'Token description 2'
    add_token_authentication(component2.id, token2, description2)
    token3 = secrets.token_hex(32)
    description3 = 'Token description 3'
    add_token_authentication(component.id, token3, description3)
    assert len(ComponentAuthentication.query.all()) == 3

    assert logic.components.Component.from_database(login_via_component_token(token3)) == component


def test_login_via_component_token_invalid_token(component, component2):
    assert len(ComponentAuthentication.query.all()) == 0
    token1 = secrets.token_hex(32)
    description1 = 'Token description 1'
    add_token_authentication(component.id, token1, description1)
    token2 = secrets.token_hex(32)
    description2 = 'Token description 2'
    add_token_authentication(component2.id, token2, description2)
    token3 = secrets.token_hex(32)
    description3 = 'Token description 3'
    add_token_authentication(component.id, token3, description3)
    assert len(ComponentAuthentication.query.all()) == 3

    token4 = secrets.token_hex(32)

    assert login_via_component_token(token4) is None
