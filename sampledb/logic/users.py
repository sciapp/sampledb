# coding: utf-8
"""

"""
import copy
import dataclasses
import datetime
import typing
from hashlib import sha256

import flask
import flask_login
from flask_babel import gettext

from .components import get_component, get_components, Component, check_component_exists
from .. import db, logic
from . import errors, settings
from .utils import cache
from .notifications import create_notification_for_being_automatically_linked
from .. models import users, UserType, FederatedIdentity, Authentication, AuthenticationType


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
        return bool(datetime.datetime.now(datetime.timezone.utc) >= expiration_datetime)


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
    extra_fields: typing.Dict[str, typing.Any] = dataclasses.field(compare=False)
    fed_id: typing.Optional[int]
    component_id: typing.Optional[int]
    last_modified: datetime.datetime
    last_modified_by_id: typing.Optional[int]
    eln_import_id: typing.Optional[int]
    eln_object_id: typing.Optional[str]
    # for use by .languages.get_user_language, no type hint to avoid circular import
    language_cache: typing.List[typing.Optional[typing.Any]] = dataclasses.field(default_factory=lambda: [None], kw_only=True, repr=False, compare=False)
    # for use by the settings property
    _settings_cache: typing.List[typing.Optional[typing.Dict[str, typing.Any]]] = dataclasses.field(default_factory=lambda: [None], kw_only=True, repr=False, compare=False)

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
            eln_import_id=user.eln_import_id,
            eln_object_id=user.eln_object_id,
        )

    @property
    def component(self) -> typing.Optional[Component]:
        if self.component_id is None:
            return None
        return get_component(self.component_id)

    @property
    def eln_import(self) -> typing.Optional['logic.eln_import.ELNImport']:
        if self.eln_import_id is None:
            return None

        return logic.eln_import.get_eln_import(self.eln_import_id)

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

    def get_name(self, include_ref: bool = False, include_id: bool = True, use_local_identity: bool = False) -> str:
        if include_ref and self.component_id is not None:
            db_ref = f', #{self.fed_id} @ {typing.cast(Component, self.component).get_name()}'
        elif include_ref and self.eln_import_id is not None and self.eln_object_id is not None:
            db_ref = f', {self.eln_object_id} @ {gettext("ELN Import")} #{self.eln_import_id}'
        else:
            db_ref = ''
        if use_local_identity:
            local_user = get_user_by_federated_user(federated_user_id=self.id)
        else:
            local_user = None
        if not include_id:
            if db_ref:
                db_ref = " (" + db_ref[2:] + ")"
            if local_user is None or local_user.name is None:
                if self.name is None:
                    return gettext('Imported User') + db_ref
                else:
                    return self.name + db_ref
            else:
                return local_user.name + db_ref
        user_id = local_user.id if local_user else self.id
        name = local_user.name if local_user else self.name
        if name is None:
            if self.component_id or self.eln_import_id:
                name = gettext('Imported User')
            else:
                name = gettext('User')
        return f'{name} (#{user_id}{db_ref})'

    @property
    def has_admin_permissions(self) -> bool:
        """
        Return whether the user has administrator permissions.

        This is the case if the user is an admin and has admin permissions enabled in their settings.
        """
        if not self.is_admin:
            return False
        return bool(self.settings['USE_ADMIN_PERMISSIONS'])

    @property
    def timezone(self) -> typing.Optional[str]:
        if flask.current_app.config['TIMEZONE']:
            return typing.cast(str, flask.current_app.config['TIMEZONE'])
        return typing.cast(typing.Optional[str], self.settings['TIMEZONE'])

    @property
    def settings(self) -> typing.Dict[str, typing.Any]:
        if self._settings_cache[0] is not None:
            return self._settings_cache[0]
        user_settings = settings.get_user_settings(self.id)
        self._settings_cache[0] = user_settings
        return user_settings

    def clear_caches(self) -> None:
        self.language_cache[0] = None
        self._settings_cache[0] = None


class AnonymousUser(flask_login.AnonymousUserMixin):
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

    @property
    def settings(self) -> typing.Dict[str, typing.Any]:
        return copy.deepcopy(settings.DEFAULT_SETTINGS)


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
    if not db.session.query(db.exists().where(users.User.id == user_id)).scalar():
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
    if component_id is None or component_id == 0:
        user = users.User.query.filter_by(id=user_id).first()
    else:
        user = users.User.query.filter_by(fed_id=user_id, component_id=component_id).first()
    if user is None:
        if component_id is not None:
            check_component_exists(component_id)
        raise errors.UserDoesNotExistError()
    return user


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
            'component_id',
            'eln_import_id',
            'eln_object_id',
        }:
            raise AttributeError(f"'User' object has no attribute '{name}'")

    if updating_user_id is not None:
        # ensure the updating user exists
        check_user_exists(updating_user_id)

        user.last_modified = datetime.datetime.now(datetime.timezone.utc)
        user.last_modified_by_id = updating_user_id

    for name, value in attributes.items():
        setattr(user, name, value)

    db.session.add(user)
    db.session.commit()


def get_users(
        *,
        exclude_hidden: bool = False,
        order_by: typing.Optional[db.Column] = users.User.name,  # type: ignore
        exclude_fed: bool = False,
        exclude_eln_import: bool = False,
) -> typing.List[User]:
    """
    Returns all users.

    :param exclude_hidden: whether to exclude hidden users
    :param order_by: Column to order the users by, or None
    :param exclude_fed: whether to exclude federation users
    :param exclude_eln_import: whether to exclude users from an .eln file
    :return: the list of users
    """
    user_query = users.User.query
    if exclude_hidden:
        user_query = user_query.filter_by(is_hidden=False)
    if order_by is not None:
        user_query = user_query.order_by(order_by)
    if exclude_fed:
        user_query = user_query.filter(users.User.type != UserType.FEDERATION_USER)
    if exclude_eln_import:
        user_query = user_query.filter(users.User.type != UserType.ELN_IMPORT_USER)
    return [
        User.from_database(user)
        for user in user_query.all()
    ]


def get_users_by_email(email: str) -> typing.List[User]:
    return [
        User.from_database(user)
        for user in
        users.User.query.filter_by(email=email).all()
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


@typing.overload
def create_user(
        name: str,
        email: str,
        type: UserType,
        orcid: typing.Optional[str] = None,
        affiliation: typing.Optional[str] = None,
        role: typing.Optional[str] = None,
        extra_fields: typing.Optional[typing.Dict[str, str]] = None,
        *,
        fed_id: None = None,
        component_id: None = None,
        eln_import_id: None = None,
        eln_object_id: None = None
) -> User:
    ...


@typing.overload
def create_user(
        name: typing.Optional[str],
        email: typing.Optional[str],
        type: UserType,
        orcid: typing.Optional[str] = None,
        affiliation: typing.Optional[str] = None,
        role: typing.Optional[str] = None,
        extra_fields: typing.Optional[typing.Dict[str, str]] = None,
        *,
        fed_id: int,
        component_id: int,
        eln_import_id: None = None,
        eln_object_id: None = None,
) -> User:
    ...


@typing.overload
def create_user(
        name: typing.Optional[str],
        email: typing.Optional[str],
        type: UserType,
        orcid: typing.Optional[str] = None,
        affiliation: typing.Optional[str] = None,
        role: typing.Optional[str] = None,
        extra_fields: typing.Optional[typing.Dict[str, str]] = None,
        *,
        fed_id: None = None,
        component_id: None = None,
        eln_import_id: int,
        eln_object_id: str,
) -> User:
    ...


def create_user(
        name: typing.Optional[str],
        email: typing.Optional[str],
        type: UserType,
        orcid: typing.Optional[str] = None,
        affiliation: typing.Optional[str] = None,
        role: typing.Optional[str] = None,
        extra_fields: typing.Optional[typing.Dict[str, str]] = None,
        *,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None,
        eln_import_id: typing.Optional[int] = None,
        eln_object_id: typing.Optional[str] = None,
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
    :param eln_import_id: the ID of the ELN import
    :param eln_object_id: the ID of the user node inside the ELN import
    :return: the newly created user
    """

    assert (component_id is None) == (fed_id is None)
    assert (eln_import_id is None) == (eln_object_id is None)
    assert component_id is not None or eln_import_id is not None or (name is not None and email is not None)

    if component_id is not None:
        check_component_exists(component_id)

    if eln_import_id is not None:
        logic.eln_import.get_eln_import(eln_import_id)

    user = users.User(
        name=name,
        email=email,
        type=type,
        orcid=orcid,
        affiliation=affiliation,
        role=role,
        extra_fields=extra_fields,
        fed_id=fed_id,
        component_id=component_id,
        last_modified=datetime.datetime.now(datetime.timezone.utc),
        eln_import_id=eln_import_id,
        eln_object_id=eln_object_id,
    )
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
    alias.last_modified = datetime.datetime.now(datetime.timezone.utc)
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


def create_eln_federated_identity(user_id: int, eln_user_id: int) -> typing.Optional[FederatedIdentity]:
    """
    Create a new federated identity between a user and an eln imported user.

    :param user_id: id of local user
    :param eln_user_id: user id of eln imported user
    :return: not none if federated identity was successfully created
    """
    eln_user = users.User.query.filter_by(id=eln_user_id).first()
    if eln_user is None:
        raise errors.UserDoesNotExistError()
    return _create_federated_identity(
        user_id=user_id,
        eln_or_fed_user=User.from_database(eln_user),
        update_if_inactive=False
    )


def create_sampledb_federated_identity(user_id: int, component: Component, fed_id: int, update_if_inactive: bool = False, use_for_login: bool = False) -> typing.Optional[FederatedIdentity]:
    """
    Create a new federated identity between a user and a federated user.

    :param user_id: id of local user
    :param component: component of the federation
    :param fed_id: federated id of the external user
    :param update_if_inactive: if true, inactive federated identity will be set to active
    :param use_for_login: if true, the federated identity can be used to login via federated login
    :return: not none if federated identity was successfully created
    """
    db_fed_user = users.User.query.filter_by(type=UserType.FEDERATION_USER, component_id=component.id, fed_id=fed_id).first()

    if db_fed_user is None:
        fed_user = create_user(name=None, email=None, type=UserType.FEDERATION_USER, fed_id=fed_id, component_id=component.id)
        set_user_hidden(fed_user.id, hidden=True)
    else:
        fed_user = User.from_database(db_fed_user)

    federated_identity = _create_federated_identity(
        user_id=user_id,
        eln_or_fed_user=fed_user,
        update_if_inactive=update_if_inactive,
        use_for_login=use_for_login
    )

    if federated_identity and use_for_login:
        logic.authentication.add_federated_login_authentication(federated_identity)
    return federated_identity


def _create_federated_identity(user_id: int, eln_or_fed_user: User, update_if_inactive: bool = False, use_for_login: bool = False) -> typing.Optional[FederatedIdentity]:
    """
    Create a new federated user link between a local and federated or eln imported user.

    :param user_id: id of the local user
    :param eln_or_fed_user: external user (federated or eln imported)
    :param update_if_inactive: if true, inactive federated identity will be set to active
    :raises errors.FederatedUserInFederatedIdentity: if the federated user is already in a federated identity
    :raises errors.ELNUserInFederatedIdentity: if the eln user is already in a federated identity
    :return: not none if federated identity was successfully created
    """
    if eln_or_fed_user.type == UserType.FEDERATION_USER:
        identity_query = FederatedIdentity.query.join(users.User, users.User.id == FederatedIdentity.local_fed_id).filter(
            users.User.type == UserType.FEDERATION_USER,
            FederatedIdentity.local_fed_id == eln_or_fed_user.id,
        )

        result = identity_query.filter(FederatedIdentity.active.is_(True)).first()

        if result is not None:
            if result.user_id != user_id:
                raise errors.FederatedUserInFederatedIdentityError()
            else:
                return result
    elif eln_or_fed_user.type == UserType.ELN_IMPORT_USER:
        identity_query = FederatedIdentity.query.join(users.User, users.User.id == FederatedIdentity.local_fed_id).filter(
            users.User.type == UserType.ELN_IMPORT_USER,
            FederatedIdentity.user_id == user_id,
            FederatedIdentity.local_fed_id == eln_or_fed_user.id
        )
        result = identity_query.filter(FederatedIdentity.active.is_(True)).first()

        if result is not None:
            raise errors.ELNUserInFederatedIdentityError()

    inactive_identities = identity_query.filter(FederatedIdentity.active.is_(False)).all()
    if inactive_identities:
        for identity in inactive_identities:
            if identity.user_id == user_id and identity.local_fed_id == eln_or_fed_user.id and not identity.active:
                if not update_if_inactive:
                    return None
                identity.active = True
                db.session.add(identity)
                db.session.commit()
                return identity

    fed_identity = FederatedIdentity(user_id=user_id, local_fed_id=eln_or_fed_user.id, login=use_for_login)
    db.session.add(fed_identity)
    db.session.commit()
    return fed_identity


def get_user_by_federated_user(federated_user_id: int, login: bool = False) -> typing.Optional[User]:
    """
    Get the local user of a federated identity by a federated user if exists.

    :param federated_user_id: local id of the federated user
    :param login: if true, only users will be returned that are enabled for federated login
    :return: local user or none
    """
    query = FederatedIdentity.query.filter_by(local_fed_id=federated_user_id, active=True)
    if login:
        query = query.filter_by(login=True)
    federated_identity = query.first()
    user = None
    if federated_identity:
        try:
            user = get_user(federated_identity.user_id)
        except errors.UserDoesNotExistError:
            pass
    return user


def get_federated_identity_by_eln_user(federated_user_id: int) -> typing.Optional[FederatedIdentity]:
    """
    Get the local user of a federated identity by a federated user if exists.

    :param federated_user_id: local id of the federated user
    :return: local user or none
    """
    return FederatedIdentity.query.join(users.User, users.User.id == FederatedIdentity.local_fed_id).filter(FederatedIdentity.local_fed_id == federated_user_id, users.User.type == UserType.ELN_IMPORT_USER).first()


def get_federated_identities(user_id: typing.Optional[int] = None, component: typing.Optional[Component] = None, eln_import_id: typing.Optional[int] = None, active_status: typing.Optional[bool] = True) -> list[FederatedIdentity]:
    """
    Get the federated identities of a user or all within a component or an eln import as a list of user links.

    :param user_id: id of the user, or none
    :param component: add filter for a component if not none
    :param eln_import_id: add filter for an eln import id if not none
    :param active_status: active state of the federated identity which should be set, or none for both
    :return: list of filtered federated identities of the specified user
    """
    query = FederatedIdentity.query
    if user_id is not None:
        query = query.filter(FederatedIdentity.user_id == user_id)
    if component is not None:
        query = query.join(users.User, users.User.id == FederatedIdentity.local_fed_id).filter(users.User.component_id == component.id)
    elif eln_import_id is not None:
        query = query.join(users.User, users.User.id == FederatedIdentity.local_fed_id).filter(users.User.eln_import_id == eln_import_id)
    if active_status is not None:
        query = query.filter(FederatedIdentity.active.is_(active_status))
    return [row for row in query.all()]


def get_federated_identity(user_id: int, eln_or_fed_user_id: int) -> FederatedIdentity:
    """
    Get the federated identity specified by user_id and the local user id of the federated user.

    :param user_id: id of the user
    :param eln_or_fed_user_id: local id of the federated user
    """
    identity = FederatedIdentity.query.filter_by(user_id=user_id, local_fed_id=eln_or_fed_user_id).first()
    if not identity:
        raise errors.FederatedIdentityNotFoundError()
    return identity


def get_active_federated_identity_by_federated_user(federated_user_id: int) -> typing.Optional[FederatedIdentity]:
    """
    Get the active federated identity of a federated user.

    :param federated_user_id: local id of the federated user
    :return: federated identity of the federated user or none
    """
    return FederatedIdentity.query.filter_by(local_fed_id=federated_user_id, active=True).first()


def get_federated_user_links_by_component_id(component_id: int, only_active: bool = True) -> list[FederatedIdentity]:
    """
    Get all federated user links of a federation component.

    :param component_id: id of the component
    :param only_active: if true, only active federated identities will be returned
    :return: list of federated identities in the component
    """
    query = FederatedIdentity.query.join(users.User, FederatedIdentity.local_fed_id == users.User.id).filter(users.User.component_id == component_id, users.User.type == UserType.FEDERATION_USER)
    if only_active:
        query = query.filter(FederatedIdentity.active.is_(True))
    return [row for row in query.all()]


def get_user_email_hashes(user: User) -> list[str]:
    """
    Get a list of hashed email addresses from the user. Only confirmed email addresses are used.

    :param user: user whose verified email addresses should be used
    :return: all hashed email addresses for the specified user
    """
    confirmed_emails = {user.email}
    authentication_logins = Authentication.query.filter_by(user_id=user.id, type=AuthenticationType.EMAIL, confirmed=True).with_entities(Authentication.login).all()
    confirmed_emails.update({login[0]['login'] for login in authentication_logins})
    return [_hash_credential(str(mail)) for mail in confirmed_emails]


def get_email_hashes_for_federation_candidates(component_id: int) -> dict[str, int]:
    """
    Get a list of candidates within a federation. Each candidate is specified by an email address (hashed) and the
    id of the corresponding user.
    Candidates are users which do not have a federated identity with a user from the specified federation component.

    :param component_id: component in which candidates should be searched
    :return: mapping of hashed email address to corresponding user id
    """
    users = get_users(exclude_fed=True, exclude_eln_import=True)
    federated_user_ids = {federated_user.user_id for federated_user in get_federated_user_links_by_component_id(component_id, only_active=False)}

    result = {_hash_credential(str(user.email)): user.id for user in users if user.id not in federated_user_ids and user.type == UserType.PERSON}
    result.update({
        _hash_credential(auth.login['login']): auth.user_id
        for auth in Authentication.query.filter(Authentication.user_id.not_in(federated_user_ids), Authentication.type == AuthenticationType.EMAIL, Authentication.confirmed.is_(True)).all()
    })

    return result


def link_users_by_email_hashes(component_id: int, user_informations: list[dict[str, typing.Any]]) -> None:
    """
    Compare the hashed email addresses from the `user_informations` with the candidates from `get_email_hashes_for_federation_candidates`.
    If two hashes match, a federated identity will be created.

    :param component_id: id of the component
    :param user_informations: list of dictionaries containing keys: "user_id", "email_hashes", "component_uuid" for each entry
    """
    component = get_component(component_id)

    user_id_by_credential_hashes = get_email_hashes_for_federation_candidates(component_id=component_id)

    component_fed_ids = {user.fed_id for user in users.User.query.join(FederatedIdentity, users.User.id == FederatedIdentity.local_fed_id).filter(users.User.component_id == component_id).all()}

    for user_data in user_informations:
        for email_hash in user_data['email_hashes']:
            user_id = user_id_by_credential_hashes.get(email_hash, None)
            fed_id = user_data['user_id']
            if user_id is not None and fed_id not in component_fed_ids:
                create_sampledb_federated_identity(user_id, component, fed_id, use_for_login=False)
                create_notification_for_being_automatically_linked(
                    user_id=user_id,
                    component_id=component_id,
                    fed_id=fed_id
                )
                break


def delete_user_link(user_id: int, local_fed_user_id: int) -> None:
    """
    Delete the federated identity of a user by the user id and the local id of a federated/imported user.

    :param user_id: id of the local user
    :param local_fed_user_id: local id of the federated user
    """
    identity = FederatedIdentity.query.filter_by(user_id=user_id, local_fed_id=local_fed_user_id).first()
    if identity:
        db.session.delete(identity)
        db.session.commit()


def delete_user_links_by_fed_ids(user_id: int, component: Component, fed_ids: typing.Sequence[int]) -> None:
    """
    Delete the user links of a user within a federation component by the federated ids.

    :param user_id: id of the local user
    :param component: federation component
    :param fed_ids: federation ids of user within the component
    """
    rows = FederatedIdentity.query.join(users.User, FederatedIdentity.local_fed_id == users.User.id).filter(FederatedIdentity.user_id == user_id, users.User.component_id == component.id, users.User.fed_id.in_(fed_ids)).all()
    for row in rows:
        db.session.delete(row)
    db.session.commit()


def revoke_user_link(user_id: int, eln_or_fed_user_id: int) -> None:
    """
    Revoke a federated identity by the user id and the local id of the federated/imported user

    :param user_id: id of the local user
    :param eln_or_fed_user_id: local id of the federated user
    """
    identity = FederatedIdentity.query.filter_by(user_id=user_id, local_fed_id=eln_or_fed_user_id, active=True).first()
    if identity:
        if identity.login:
            auth = Authentication.query.filter(
                Authentication.user_id == identity.user_id,
                Authentication.login['fed_user_id'].astext.cast(db.Integer) == identity.local_fed_user.fed_id,
                Authentication.login['component_id'].astext.cast(db.Integer) == identity.local_fed_user.component_id
            ).first()
            if auth is not None:
                db.session.delete(auth)
        identity.active = False
        db.session.add(identity)
        db.session.commit()


def revoke_user_links_by_fed_ids(user_id: int, component_id: int, fed_ids: typing.Sequence[int]) -> None:
    """
    Revoke the user links of a user within a federation component by the federated ids.

    :user_id: local user which has the federated identity
    :component_id: federation component
    :fed_ids: federated ids of the external users
    """
    base_query = FederatedIdentity.query.join(users.User, FederatedIdentity.local_fed_id == users.User.id).filter(FederatedIdentity.user_id == user_id, users.User.component_id == component_id)
    rows = base_query.filter(users.User.fed_id.in_(fed_ids)).all()

    has_other_auth_methods = identity_not_required_for_auth(component_id)

    remaining_rows_with_login = base_query.filter(users.User.fed_id.not_in(fed_ids), FederatedIdentity.login.is_(True)).all()
    rows_to_delete_with_login = base_query.filter(users.User.fed_id.in_(fed_ids), FederatedIdentity.login.is_(True)).all()

    if not has_other_auth_methods and not remaining_rows_with_login and rows_to_delete_with_login:
        raise errors.NoAuthenticationMethodError()

    for row in rows:
        if row.login:
            auth = Authentication.query.filter(
                Authentication.user_id == row.user_id,
                Authentication.login['fed_user_id'].astext.cast(db.Integer) == row.local_fed_user.fed_id,
                Authentication.login['component_id'].astext.cast(db.Integer) == row.local_fed_user.component_id
            ).first()
            if auth is not None:
                db.session.delete(auth)
        row.active = False
        db.session.add(row)
    db.session.commit()


def enable_user_link(user_id: int, eln_or_fed_user_id: int) -> None:
    """
    Enable a federated identity by the user id and the local id of the federated/imported user

    :param user_id: id of the local user
    :param eln_or_fed_user_id: local id of the federated user
    """
    fed_identity = FederatedIdentity.query.filter_by(user_id=user_id, local_fed_id=eln_or_fed_user_id, active=False).first()
    if fed_identity:
        fed_identity.active = True
        db.session.add(fed_identity)
        db.session.commit()


def enable_federated_identity_for_login(identity: FederatedIdentity) -> None:
    """
    Allow to use the specified federated identity for the federated login

    :identity: federated identity to be enabled for the login
    """
    if not identity.login:
        try:
            logic.authentication.add_federated_login_authentication(federated_identity=identity)
        except errors.AuthenticationMethodAlreadyExists:
            pass
        identity.login = True
        db.session.add(identity)
        db.session.commit()


def identity_not_required_for_auth(component_id: int) -> bool:
    """
    Check if the federated identity of the user with users from the specified federation component is required for authentication.

    :component_id: ID of the federation component
    :return: True if the federated identity is required
    """
    return not flask.current_app.config['ENABLE_FEDERATED_LOGIN'] or (
        Authentication.query.filter(
            db.and_(Authentication.user_id == flask_login.current_user.id, Authentication.confirmed.is_(True), Authentication.type != AuthenticationType.API_TOKEN, Authentication.type != AuthenticationType.API_ACCESS_TOKEN,
                    db.or_(Authentication.type != AuthenticationType.FEDERATED_LOGIN, db.and_(Authentication.type == AuthenticationType.FEDERATED_LOGIN, Authentication.login['component_id'].astext.cast(db.Integer) != component_id)))
        ).count() > 0
    )


def _hash_credential(credential: str) -> str:
    """
    Hash a credential with sha256-algorithm.

    :param credential: credential that should be hashed, e.g. email address
    :return: hash value of the credential
    """
    return sha256(credential.encode()).hexdigest()
