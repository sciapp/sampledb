import typing

from .. import db
from ..models import ComponentAuthentication, ComponentAuthenticationType, OwnComponentAuthentication
from .errors import NoAuthenticationMethodError, InvalidTokenError, AuthenticationMethodDoesNotExistError, \
    TokenExistsError
from .authentication import _hash_password, _validate_password_hash
from .components import Component


def get_own_authentication(
        component_id: int,
        type: ComponentAuthenticationType = ComponentAuthenticationType.TOKEN
) -> OwnComponentAuthentication:
    auth: typing.Optional[OwnComponentAuthentication] = OwnComponentAuthentication.query.filter_by(component_id=component_id, type=type).first()
    if auth is None:
        raise NoAuthenticationMethodError()
    return auth


def own_token_exists(
        component_id: int,
        token: str
) -> bool:
    authentication_methods = OwnComponentAuthentication.query.filter(
        db.and_(OwnComponentAuthentication.login['token'].astext == token,
                db.and_(OwnComponentAuthentication.type == ComponentAuthenticationType.TOKEN,
                        OwnComponentAuthentication.component_id == component_id))
    ).first()
    return authentication_methods is not None


def add_token_authentication(
        component_id: int,
        token: str,
        description: str
) -> None:
    if len(token) != 64:
        raise InvalidTokenError()
    token = token.lower()
    # split into a short part (8 hex digits / 4 bytes) for identification and a long part for authentication
    login, password = token[:8], token[8:]
    authentication = ComponentAuthentication(
        login={
            'login': login,
            'bcrypt_hash': _hash_password(password),
            'description': description
        },
        authentication_type=ComponentAuthenticationType.TOKEN,
        component_id=component_id
    )
    db.session.add(authentication)
    db.session.commit()


def add_own_token_authentication(
        component_id: int,
        token: str,
        description: str
) -> None:
    token = token.lower().strip()
    if len(token) != 64:
        raise InvalidTokenError()
    if own_token_exists(component_id, token):
        raise TokenExistsError()
    authentication = OwnComponentAuthentication(
        login={
            'token': token,
            'description': description
        },
        authentication_type=ComponentAuthenticationType.TOKEN,
        component_id=component_id
    )
    db.session.add(authentication)
    db.session.commit()


def login_via_component_token(
        component_token: str
) -> typing.Optional[Component]:
    """
    Authenticate a component using an API token.

    :param component_token: the API token to use during authentication
    :return: the component or None
    """
    # convert to lower case to enforce case insensitivity
    component_token = component_token.lower().strip()
    login, password = component_token[:8], component_token[8:]
    authentication_methods = ComponentAuthentication.query.filter(
        db.and_(ComponentAuthentication.login['login'].astext == login,
                ComponentAuthentication.type == ComponentAuthenticationType.TOKEN)
    ).all()

    for authentication_method in authentication_methods:
        if _validate_password_hash(password, authentication_method.login['bcrypt_hash']):
            if authentication_method.component:
                return Component.from_database(authentication_method.component)
    return None


def remove_component_authentication_method(
        authentication_method_id: int
) -> None:
    """
    Remove a component authentication method.

    :param authentication_method_id: the ID of an existing authentication method
    :raise error.AuthenticationMethodDoesNotExistError: when no component
        authentication method with the given ID exists
    """
    authentication_method = ComponentAuthentication.query.filter(ComponentAuthentication.id == authentication_method_id).first()
    if authentication_method is None:
        raise AuthenticationMethodDoesNotExistError()

    db.session.delete(authentication_method)
    db.session.commit()


def remove_own_component_authentication_method(
        authentication_method_id: int
) -> None:
    """
    Remove a component authentication method.

    :param authentication_method_id: the ID of an existing authentication method
    :raise error.AuthenticationMethodDoesNotExistError: when no component
        authentication method with the given ID exists
    """
    authentication_method = OwnComponentAuthentication.query.filter(OwnComponentAuthentication.id == authentication_method_id).first()
    if authentication_method is None:
        raise AuthenticationMethodDoesNotExistError()

    db.session.delete(authentication_method)
    db.session.commit()
