# coding: utf-8
"""

"""

import copy
import dataclasses
import datetime
import typing

import flask
import flask_login
from flask_babel import gettext

from .components import get_component, get_components, Component, check_component_exists
from .. import db
from . import errors, settings
from .utils import cache
from .. models import users, UserType


@dataclasses.dataclass(frozen=True)
class UserInvitation:
    """
    This class provides an immutable wrapper around models.users.UserInvitation.
    """
    id: int
    inviter_id: int
    utc_datetime: datetime.datetime
    accepted: bool

    @classmethod
    def from_database(cls, user_invitation: users.UserInvitation) -> 'UserInvitation':
        return UserInvitation(
            id=user_invitation.id,
            inviter_id=user_invitation.inviter_id,
            utc_datetime=user_invitation.utc_datetime,
            accepted=user_invitation.accepted
        )

    @property
    def expired(self) -> bool:
        expiration_datetime = self.utc_datetime + datetime.timedelta(seconds=flask.current_app.config['INVITATION_TIME_LIMIT'])
        return bool(datetime.datetime.utcnow() >= expiration_datetime)


@dataclasses.dataclass(frozen=True)
class User:
    """
    This class provides an immutable wrapper around models.users.User.
    """

    id: int
    name: typing.Optional[str]
    email: typing.Optional[str]
    type: UserType
    is_admin: bool
    is_readonly: bool
    is_hidden: bool
    is_active: bool
    orcid: typing.Optional[str]
    affiliation: typing.Optional[str]
    role: typing.Optional[str]
    extra_fields: typing.Dict[str, typing.Any]
    fed_id: typing.Optional[int]
    component_id: typing.Optional[int]
    last_modified: datetime.datetime
    last_modified_by_id: typing.Optional[int]
    # for use by .languages.get_user_language, no type hint to avoid circular import
    language_cache: typing.List[typing.Optional[typing.Any]] = dataclasses.field(default_factory=lambda: [None], kw_only=True, repr=False, compare=False)

    @classmethod
    def from_database(cls, user: users.User) -> 'User':
        return User(
            id=user.id,
            name=user.name,
            email=user.email,
            type=user.type,
            is_admin=user.is_admin,
            is_readonly=user.is_readonly,
            is_hidden=user.is_hidden,
            is_active=user.is_active,
            orcid=user.orcid,
            affiliation=user.affiliation,
            role=user.role,
            extra_fields=copy.deepcopy(user.extra_fields),
            fed_id=user.fed_id,
            component_id=user.component_id,
            last_modified=user.last_modified,
            last_modified_by_id=user.last_modified_by_id,
        )

    @property
    def component(self) -> typing.Optional[Component]:
        if self.component_id is None:
            return None
        return get_component(self.component_id)

    def get_id(self) -> int:
        return self.id

    @property
    def is_authenticated(self) -> bool:
        return self.is_active

    @property
    def is_anonymous(self) -> bool:
        return False

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, (flask_login.UserMixin, User)):
            return bool(self.get_id() == other.get_id())
        return NotImplemented

    def __ne__(self, other: typing.Any) -> bool:
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal

    def get_name(self, include_ref: bool = False) -> str:
        if include_ref and self.component_id is not None:
            db_ref = ', #{} @ {}'.format(self.fed_id, typing.cast(Component, self.component).get_name())
        else:
            db_ref = ''
        if self.name is None:
            return gettext('Imported User (#%(user_id)s%(db_ref)s)', user_id=self.id, db_ref=db_ref)  # type: ignore
        else:
            return '{} (#{}{})'.format(self.name, self.id, db_ref)

    @property
    def has_admin_permissions(self) -> bool:
        """
        Return whether the user has administrator permissions.

        This is the case if the user is an admin and has admin permissions enabled in their settings.
        """
        if not self.is_admin:
            return False
        return bool(settings.get_user_setting(self.id, 'USE_ADMIN_PERMISSIONS'))

    @property
    def timezone(self) -> typing.Optional[str]:
        if flask.current_app.config['TIMEZONE']:
            return typing.cast(str, flask.current_app.config['TIMEZONE'])
        return typing.cast(typing.Optional[str], settings.get_user_setting(self.id, 'TIMEZONE'))


class AnonymousUser(flask_login.AnonymousUserMixin):  # type: ignore
    @property
    def id(self) -> typing.Optional[int]:
        return None

    @property
    def has_admin_permissions(self) -> bool:
        return False

    @property
    def timezone(self) -> typing.Optional[str]:
        if flask.current_app.config['TIMEZONE']:
            return typing.cast(str, flask.current_app.config['TIMEZONE'])
        return None

    @property
    def is_readonly(self) -> bool:
        # anonymous users cannot change anything but are not specifically marked as readonly
        return False


@dataclasses.dataclass(frozen=True)
class UserFederationAlias:
    """
    This class provides an immutable wrapper around models.users.UserFederationAlias.
    """
    user_id: int
    component_id: int
    name: typing.Optional[str]
    use_real_name: bool
    email: typing.Optional[str]
    use_real_email: bool
    orcid: typing.Optional[str]
    use_real_orcid: bool
    affiliation: typing.Optional[str]
    use_real_affiliation: bool
    role: typing.Optional[str]
    use_real_role: bool
    extra_fields: typing.Dict[str, typing.Any]
    last_modified: datetime.datetime
    is_default: bool

    @classmethod
    def from_database(cls, alias: users.UserFederationAlias) -> 'UserFederationAlias':
        if any([alias.use_real_name, alias.use_real_email, alias.use_real_orcid, alias.use_real_affiliation, alias.use_real_role]):
            user = get_user(alias.user_id)
            return UserFederationAlias(
                is_default=False,
                user_id=alias.user_id,
                component_id=alias.component_id,
                name=user.name if alias.use_real_name else alias.name,
                use_real_name=alias.use_real_name,
                email=user.email if alias.use_real_email else alias.email,
                use_real_email=alias.use_real_email,
                orcid=user.orcid if alias.use_real_orcid else alias.orcid,
                use_real_orcid=alias.use_real_orcid,
                affiliation=user.affiliation if alias.use_real_affiliation else alias.affiliation,
                use_real_affiliation=alias.use_real_affiliation,
                role=user.role if alias.use_real_role else alias.role,
                use_real_role=alias.use_real_role,
                extra_fields=copy.deepcopy(alias.extra_fields),
                last_modified=alias.last_modified
            )
        else:
            return UserFederationAlias(
                is_default=False,
                user_id=alias.user_id,
                component_id=alias.component_id,
                name=alias.name,
                use_real_name=alias.use_real_name,
                email=alias.email,
                use_real_email=alias.use_real_email,
                orcid=alias.orcid,
                use_real_orcid=alias.use_real_orcid,
                affiliation=alias.affiliation,
                use_real_affiliation=alias.use_real_affiliation,
                role=alias.role,
                use_real_role=alias.use_real_role,
                extra_fields=copy.deepcopy(alias.extra_fields),
                last_modified=alias.last_modified
            )

    @classmethod
    def from_user_profile(cls, user_id: int, component_id: int) -> 'UserFederationAlias':
        user = get_user(user_id)
        return UserFederationAlias(
            is_default=True,
            user_id=user_id,
            component_id=component_id,
            name=user.name,
            use_real_name=True,
            email=user.email,
            use_real_email=True,
            orcid=user.orcid,
            use_real_orcid=True,
            affiliation=user.affiliation,
            use_real_affiliation=True,
            role=user.role,
            use_real_role=True,
            extra_fields=copy.deepcopy(user.extra_fields),
            last_modified=user.last_modified
        )


@cache
def check_user_exists(
        user_id: int
) -> None:
    """
    Check whether a user with the given user ID exists.

    :param user_id: the ID of an existing user
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    if not db.session.query(db.exists().where(users.User.id == user_id)).scalar():  # type: ignore
        raise errors.UserDoesNotExistError()


def get_user(user_id: int, component_id: typing.Optional[int] = None) -> User:
    return User.from_database(get_mutable_user(user_id, component_id))


def get_mutable_user(user_id: int, component_id: typing.Optional[int] = None) -> users.User:
    """
    Get the mutable user instance to perform changes in the database on.

    :param user_id: the user ID of an existing user
    :param component_id: the ID of an existing component, or None
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    if user_id is None:
        raise TypeError("user_id must be int")
    if component_id is None or component_id == 0:
        user = users.User.query.filter_by(id=user_id).first()
    else:
        user = users.User.query.filter_by(fed_id=user_id, component_id=component_id).first()
    if user is None:
        if component_id is not None:
            check_component_exists(component_id)
        raise errors.UserDoesNotExistError()
    return typing.cast(users.User, user)


def update_user(
        user_id: int,
        updating_user_id: typing.Optional[int],
        **attributes: typing.Any
) -> None:
    """
    Update one or multiple attributes of an existing user in the database.

    :param user_id: the user ID of an existing user
    :param updating_user_id: the ID of the user causing the update, or None
    :param attributes: a mapping of attribute names and values
    :raise AttributeError: when a non-existing attribute is set
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID or updating user ID exists
    """
    user = get_mutable_user(user_id)
    for name in attributes:
        if name not in {
            'name',
            'email',
            'type',
            'is_admin',
            'is_readonly',
            'is_hidden',
            'is_active',
            'orcid',
            'affiliation',
            'role',
            'extra_fields',
            'fed_id',
            'component_id'
        }:
            raise AttributeError(f"'User' object has no attribute '{name}'")

    if updating_user_id is not None:
        # ensure the updating user exists
        check_user_exists(updating_user_id)

        user.last_modified = datetime.datetime.utcnow()
        user.last_modified_by_id = updating_user_id

    for name, value in attributes.items():
        setattr(user, name, value)

    db.session.add(user)
    db.session.commit()


def get_users(
        exclude_hidden: bool = False,
        order_by: typing.Optional[db.Column] = users.User.name,  # type: ignore
        exclude_fed: bool = False
) -> typing.List[User]:
    """
    Returns all users.

    :param exclude_hidden: whether to exclude hidden users
    :param order_by: Column to order the users by, or None
    :param exclude_fed: whether imported users should be included
    :return: the list of users
    """
    user_query = users.User.query
    if exclude_hidden:
        user_query = user_query.filter_by(is_hidden=False)
    if order_by is not None:
        user_query = user_query.order_by(order_by)
    if exclude_fed:
        user_query = user_query.filter(users.User.type != UserType.FEDERATION_USER)
    return [
        User.from_database(user)
        for user in user_query.all()
    ]


def get_users_for_component(
        component_id: int,
        exclude_hidden: bool = False,
        order_by: typing.Optional[db.Column] = users.User.name  # type: ignore
) -> typing.List[User]:
    user_query = users.User.query.filter_by(component_id=component_id)
    if exclude_hidden:
        user_query = user_query.filter_by(is_hidden=False)
    if order_by is not None:
        user_query = user_query.order_by(order_by)
    return [
        User.from_database(user)
        for user in user_query.all()
    ]


def get_administrators() -> typing.List[User]:
    """
    Returns all current administrators.

    :return: the list of administrators
    """
    return [
        User.from_database(user)
        for user in users.User.query.filter_by(is_admin=True).all()
    ]


def get_users_by_name(name: str) -> typing.List[User]:
    """
    Return all users with a given name.

    :param name: the user name to search for
    :return: the list of users with this name
    """
    return [
        User.from_database(user)
        for user in users.User.query.filter_by(name=name).all()
    ]


def create_user(
        name: typing.Optional[str],
        email: typing.Optional[str],
        type: UserType,
        orcid: typing.Optional[str] = None,
        affiliation: typing.Optional[str] = None,
        role: typing.Optional[str] = None,
        extra_fields: typing.Optional[typing.Dict[str, str]] = None,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None
) -> User:
    """
    Create a new user.

    This function cannot create a user as an administrator. To set whether a user is
    an administrator, use the set_administrator script or set_user_administrator function.

    :param name: the user's name
    :param email: the user's email address
    :param type: the user's type
    :param orcid: the user's ORCID iD
    :param affiliation: the user's affiliation
    :param role: the user's role
    :param extra_fields: a dict describing the values for defined extra fields
    :param fed_id: the ID of the related user at the exporting component
    :param component_id: the ID of the exporting component
    :return: the newly created user
    """

    if (component_id is None) != (fed_id is None) or (component_id is None and (name is None or email is None)):
        raise TypeError('Invalid parameter combination.')

    if component_id is not None:
        check_component_exists(component_id)

    user = users.User(name=name, email=email, type=type, orcid=orcid, affiliation=affiliation, role=role, extra_fields=extra_fields, fed_id=fed_id, component_id=component_id, last_modified=datetime.datetime.utcnow())
    db.session.add(user)
    db.session.commit()
    return User.from_database(user)


def set_user_readonly(user_id: int, readonly: bool) -> None:
    """
    Set whether a user should be limited to READ permissions.

    :param user_id: the user ID of an existing user
    :param readonly: True, if the user should be read only, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    update_user(
        user_id,
        updating_user_id=None,
        is_readonly=readonly
    )


def set_user_hidden(user_id: int, hidden: bool) -> None:
    """
    Set whether a user should be hidden from user lists.

    :param user_id: the user ID of an existing user
    :param hidden: True, if the user should be hidden, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    update_user(
        user_id,
        updating_user_id=None,
        is_hidden=hidden
    )


def set_user_active(user_id: int, active: bool) -> None:
    """
    Set whether a user should be allowed to sign in.

    :param user_id: the user ID of an existing user
    :param active: True, if the user should be active, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    update_user(
        user_id,
        updating_user_id=None,
        is_active=active
    )


def set_user_administrator(user_id: int, is_admin: bool) -> None:
    """
    Set whether a user is an administrator.

    :param user_id: the user ID of an existing user
    :param is_admin: True, if the user is an administrator, False otherwise
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    update_user(
        user_id,
        updating_user_id=None,
        is_admin=is_admin
    )


def get_user_invitation(invitation_id: int) -> UserInvitation:
    """
    Get an existing invitation.

    :param invitation_id: the ID of an existing invitation
    :return: the invitation
    :raise errors.UserInvitationDoesNotExistError: when no invitation with
        the given ID exists
    """
    invitation = users.UserInvitation.query.filter_by(id=invitation_id).first()
    if invitation is None:
        raise errors.UserInvitationDoesNotExistError()
    return UserInvitation.from_database(invitation)


def set_user_invitation_accepted(invitation_id: int) -> None:
    """
    Mark an invitation as having been accepted.

    :param invitation_id: the ID of an existing invitation
    :raise errors.UserInvitationDoesNotExistError: when no invitation with
        the given ID exists
    """
    invitation = users.UserInvitation.query.filter_by(id=invitation_id).first()
    if invitation is None:
        raise errors.UserInvitationDoesNotExistError()
    invitation.accepted = True
    db.session.add(invitation)
    db.session.commit()


def get_user_alias(user_id: int, component_id: int) -> UserFederationAlias:
    """
    Get an existing user alias.

    :param user_id: the ID of an existing user
    :param component_id: the ID of an existing component
    :return: the user alias
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    :raise errors.ComponentDoesNotExistError: when no component with given ID exists
    :raise errors.UserAliasDoesNotExistError: when no alias with given IDs exists
    """
    alias = users.UserFederationAlias.query.filter_by(user_id=user_id, component_id=component_id).first()
    if alias is None:
        user = get_user(user_id)
        check_component_exists(component_id)
        if flask.current_app.config['ENABLE_DEFAULT_USER_ALIASES'] and user.type == UserType.PERSON:
            return UserFederationAlias.from_user_profile(user_id, component_id)
        raise errors.UserAliasDoesNotExistError()
    return UserFederationAlias.from_database(alias)


def get_user_aliases_for_user(user_id: int) -> typing.List[UserFederationAlias]:
    """
    Get all aliases for a user.

    :param user_id: the ID of an existing user
    :return: list of user aliases
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    """
    user = get_user(user_id)
    alias = users.UserFederationAlias.query.filter_by(user_id=user_id).all()
    if flask.current_app.config['ENABLE_DEFAULT_USER_ALIASES'] and user.type == UserType.PERSON:
        return [
            UserFederationAlias.from_database(a) for a in alias
        ] + [
            UserFederationAlias.from_user_profile(user_id, component.id)
            for component in get_components()
            if not any(
                component.id == a.component_id
                for a in alias
            )
        ]
    return [UserFederationAlias.from_database(a) for a in alias]


def get_user_aliases_for_component(component_id: int, modified_since: typing.Optional[datetime.datetime] = None) -> typing.List[UserFederationAlias]:
    """
    Get all aliases for a component.

    :param component_id: the ID of an existing component
    :param modified_since: Only return aliases modified since modified_since. None to query every alias. (default: None)
    :return: list of user aliases
    :raise errors.ComponentDoesNotExistError: when no component with the given ID exists
    """
    check_component_exists(component_id)
    if modified_since is None:
        alias = users.UserFederationAlias.query.filter_by(component_id=component_id).all()
    else:
        alias = users.UserFederationAlias.query.join(
            users.User, users.User.id == users.UserFederationAlias.user_id
        ).filter(
            db.or_(
                db.and_(
                    users.UserFederationAlias.component_id == component_id,
                    users.UserFederationAlias.last_modified >= modified_since
                ),
                db.and_(
                    db.or_(users.UserFederationAlias.use_real_name, users.UserFederationAlias.use_real_email, users.UserFederationAlias.use_real_orcid, users.UserFederationAlias.use_real_affiliation, users.UserFederationAlias.use_real_role),
                    users.User.last_modified >= modified_since
                )
            )
        ).all()
    if flask.current_app.config['ENABLE_DEFAULT_USER_ALIASES']:
        return [
            UserFederationAlias.from_database(a) for a in alias
        ] + [
            UserFederationAlias.from_user_profile(user.id, component_id)
            for user in get_users()
            if not any(
                user.id == a.user_id
                for a in alias
            ) and (modified_since is None or user.last_modified >= modified_since) and user.type == UserType.PERSON
        ]
    return [UserFederationAlias.from_database(a) for a in alias]


def create_user_alias(
    user_id: int,
    component_id: int,
    name: typing.Optional[str] = None,
    use_real_name: bool = False,
    email: typing.Optional[str] = None,
    use_real_email: bool = False,
    orcid: typing.Optional[str] = None,
    use_real_orcid: bool = False,
    affiliation: typing.Optional[str] = None,
    use_real_affiliation: bool = False,
    role: typing.Optional[str] = None,
    use_real_role: bool = False
) -> UserFederationAlias:
    """
    Create a new user alias for a component.

    :param user_id: the ID of an existing user
    :param component_id:  the ID of an existing component
    :param name: the alias name
    :param use_real_name: boolean whether to use the name from the users' profile
    :param email: the alias email
    :param use_real_email: boolean whether to use the email from the users' profile
    :param orcid: the alias orcid
    :param use_real_orcid: boolean whether to use the orcid from the users' profile
    :param affiliation: the alias affiliation
    :param use_real_affiliation: boolean whether to use the affiliation from the users' profile
    :param role: the alias role
    :param use_real_role: boolean whether to use the role from the users' profile
    :return: the new created alias
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    :raise errors.ComponentDoesNotExistError: when no component with given ID exists
    :raise errors.UserAliasAlreadyExistsError: when an alias with given IDs already exists
    """
    alias = users.UserFederationAlias.query.filter_by(user_id=user_id, component_id=component_id).first()
    if alias is not None:
        check_user_exists(user_id)
        check_component_exists(component_id)
        raise errors.UserAliasAlreadyExistsError()
    if use_real_name:
        name = None
    if use_real_email:
        email = None
    if use_real_orcid:
        orcid = None
    if use_real_affiliation:
        affiliation = None
    if use_real_role:
        role = None
    alias = users.UserFederationAlias(user_id, component_id, name, use_real_name, email, use_real_email, orcid, use_real_orcid, affiliation, use_real_affiliation, role, use_real_role, {})
    db.session.add(alias)
    db.session.commit()
    return UserFederationAlias.from_database(alias)


def update_user_alias(
    user_id: int,
    component_id: int,
    name: typing.Optional[str] = None,
    use_real_name: bool = False,
    email: typing.Optional[str] = None,
    use_real_email: bool = False,
    orcid: typing.Optional[str] = None,
    use_real_orcid: bool = False,
    affiliation: typing.Optional[str] = None,
    use_real_affiliation: bool = False,
    role: typing.Optional[str] = None,
    use_real_role: bool = False
) -> None:
    """
    Update a users' alias for a component.

    If a user does not have an alias for this component yet, but default
    aliases are enabled, a new non-default alias will be created with the
    given settings without raising a UserAliasDoesNotExistError exception.

    :param user_id: the ID of an existing user
    :param component_id:  the ID of an existing component
    :param name: the alias name
    :param use_real_name: boolean whether to use the name from the users' profile
    :param email: the alias email
    :param use_real_email: boolean whether to use the email from the users' profile
    :param orcid: the alias orcid
    :param use_real_orcid: boolean whether to use the orcid from the users' profile
    :param affiliation: the alias affiliation
    :param use_real_affiliation: boolean whether to use the affiliation from the users' profile
    :param role: the alias role
    :param use_real_role: boolean whether to use the role from the users' profile
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    :raise errors.ComponentDoesNotExistError: when no component with given ID exists
    :raise errors.UserAliasDoesNotExistError: when no alias with given IDs exists
    """
    alias = users.UserFederationAlias.query.filter_by(user_id=user_id, component_id=component_id).first()
    if alias is None:
        user = get_user(user_id)
        check_component_exists(component_id)
        if flask.current_app.config['ENABLE_DEFAULT_USER_ALIASES'] and user.type == UserType.PERSON:
            create_user_alias(
                user_id=user_id,
                component_id=component_id,
                name=name,
                use_real_name=use_real_name,
                email=email,
                use_real_email=use_real_email,
                orcid=orcid,
                use_real_orcid=use_real_orcid,
                affiliation=affiliation,
                use_real_affiliation=use_real_affiliation,
                role=role,
                use_real_role=use_real_role
            )
            return
        raise errors.UserAliasDoesNotExistError()
    if use_real_name:
        name = None
    if use_real_email:
        email = None
    if use_real_orcid:
        orcid = None
    if use_real_affiliation:
        affiliation = None
    if use_real_role:
        role = None
    alias.name = name
    alias.use_real_name = use_real_name
    alias.email = email
    alias.use_real_email = use_real_email
    alias.orcid = orcid
    alias.use_real_orcid = use_real_orcid
    alias.affiliation = affiliation
    alias.use_real_affiliation = use_real_affiliation
    alias.role = role
    alias.use_real_role = use_real_role
    alias.last_modified = datetime.datetime.utcnow()
    db.session.add(alias)
    db.session.commit()


def delete_user_alias(user_id: int, component_id: int) -> None:
    """
    Delete a user alias.

    :param user_id: the ID of an existing user
    :param component_id:  the ID of an existing component
    :raise errors.UserDoesNotExistError: when no user with given ID exists
    :raise errors.ComponentDoesNotExistError: when no component with given ID exists
    :raise errors.UserAliasDoesNotExistError: when no alias with given IDs exists
    """
    alias = users.UserFederationAlias.query.filter_by(user_id=user_id, component_id=component_id).first()
    if alias is None:
        check_user_exists(user_id)
        check_component_exists(component_id)
        raise errors.UserAliasDoesNotExistError()
    db.session.delete(alias)
    db.session.commit()
