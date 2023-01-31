import typing

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_str, _get_dict
from ..users import get_mutable_user, create_user, set_user_hidden, get_user, get_user_alias, User
from ..components import Component
from .. import errors, fed_logs
from ...models import UserType
from ... import db


class UserData(typing.TypedDict):
    fed_id: int
    component_uuid: str
    name: typing.Optional[str]
    email: typing.Optional[str]
    orcid: typing.Optional[str]
    affiliation: typing.Optional[str]
    role: typing.Optional[str]
    extra_fields: typing.Dict[str, str]


class UserRef(typing.TypedDict):
    user_id: int
    component_uuid: str


class SharedUserData(typing.TypedDict):
    user_id: int
    component_uuid: str
    name: typing.Optional[str]
    email: typing.Optional[str]
    orcid: typing.Optional[str]
    affiliation: typing.Optional[str]
    role: typing.Optional[str]
    extra_fields: typing.Dict[str, str]


def import_user(
        user_data: UserData,
        component: Component
) -> User:
    component_id = _get_or_create_component_id(user_data['component_uuid'])
    # component_id will only be None if this would import a local user
    assert component_id is not None
    try:
        mutable_user = get_mutable_user(user_data['fed_id'], component_id)
        ignored_keys = {
            'fed_id',
            'component_uuid'
        }
        if any(
                value != getattr(mutable_user, key)
                for key, value in user_data.items()
                if key not in ignored_keys
        ):
            mutable_user.name = user_data['name']
            mutable_user.email = user_data['email']
            mutable_user.orcid = user_data['orcid']
            mutable_user.affiliation = user_data['affiliation']
            mutable_user.role = user_data['role']
            mutable_user.extra_fields = user_data['extra_fields']
            db.session.add(mutable_user)
            db.session.commit()
            fed_logs.update_user(mutable_user.id, component.id)
        user = User.from_database(mutable_user)
    except errors.UserDoesNotExistError:
        user = create_user(
            fed_id=user_data['fed_id'],
            component_id=component_id,
            name=user_data['name'],
            email=user_data['email'],
            orcid=user_data['orcid'],
            affiliation=user_data['affiliation'],
            role=user_data['role'],
            extra_fields=user_data['extra_fields'],
            type=UserType.FEDERATION_USER
        )
        set_user_hidden(user.id, True)
        fed_logs.import_user(user.id, component.id)
    return user


def parse_import_user(
        user_data: typing.Dict[str, typing.Any],
        component: Component
) -> User:
    return import_user(parse_user(user_data, component), component)


def parse_user(
        user_data: typing.Dict[str, typing.Any],
        component: Component
) -> UserData:
    uuid = _get_uuid(user_data.get('component_uuid'))
    fed_id = _get_id(user_data.get('user_id'))
    if uuid != component.uuid:
        # only accept user data from original source
        raise errors.InvalidDataExportError(f'User data update for user #{fed_id} @ {uuid}')
    return UserData(
        fed_id=fed_id,
        component_uuid=uuid,
        name=_get_str(user_data.get('name')),
        email=_get_str(user_data.get('email')),
        orcid=_get_str(user_data.get('orcid')),
        affiliation=_get_str(user_data.get('affiliation')),
        role=_get_str(user_data.get('role')),
        extra_fields=_get_dict(user_data.get('extra_fields'), default={})
    )


@typing.overload
def _parse_user_ref(
        user_data: typing.Union[UserRef, typing.Dict[str, typing.Any]]
) -> UserRef:
    ...


@typing.overload
def _parse_user_ref(
        user_data: None
) -> None:
    ...


def _parse_user_ref(
        user_data: typing.Optional[typing.Union[UserRef, typing.Dict[str, typing.Any]]]
) -> typing.Optional[UserRef]:
    if user_data is None:
        return None
    user_id = _get_id(user_data.get('user_id'))
    component_uuid = _get_uuid(user_data.get('component_uuid'))
    return UserRef(
        user_id=user_id,
        component_uuid=component_uuid
    )


@typing.overload
def _get_or_create_user_id(
        user_data: UserRef
) -> int:
    ...


@typing.overload
def _get_or_create_user_id(
        user_data: None
) -> None:
    ...


def _get_or_create_user_id(
        user_data: typing.Optional[UserRef]
) -> typing.Optional[int]:
    if user_data is None:
        return None
    component_id = _get_or_create_component_id(user_data['component_uuid'])
    try:
        user = get_user(user_data['user_id'], component_id)
    except errors.UserDoesNotExistError:
        assert component_id is not None
        user = create_user(
            name=None,
            email=None,
            fed_id=user_data['user_id'],
            component_id=component_id,
            type=UserType.FEDERATION_USER
        )
        set_user_hidden(user.id, True)
        fed_logs.create_ref_user(user.id, component_id)
    return user.id


def shared_user_preprocessor(
        user_id: int,
        component: Component,
        _refs: typing.List[typing.Tuple[str, int]],
        _markdown_images: typing.Dict[str, str]
) -> typing.Optional[SharedUserData]:
    user = get_user(user_id)
    if user.component_id is not None:
        return None
    try:
        alias = get_user_alias(user_id, component.id)
        return SharedUserData(
            user_id=user.id,
            component_uuid=flask.current_app.config['FEDERATION_UUID'],
            name=alias.name,
            email=alias.email,
            orcid=alias.orcid,
            affiliation=alias.affiliation,
            role=alias.role,
            extra_fields=alias.extra_fields
        )
    except errors.UserAliasDoesNotExistError:
        return SharedUserData(
            user_id=user.id,
            component_uuid=flask.current_app.config['FEDERATION_UUID'],
            name=None,
            email=None,
            orcid=None,
            affiliation=None,
            role=None,
            extra_fields={}
        )
