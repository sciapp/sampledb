# coding: utf-8
"""
Logic module for versioned generic object storage

At its core, this module provides a procedural wrapper of models.objects and
models.versioned_json_object_tables. At the same time, the functions contain
additional logic, e.g. for initial default permissions or object logs.

In practice, the flask-sqlalchemy database engine instance is used. So even
though the underlying models only rely on SQLAlchemy Core and not the ORM,
the functions in this module should be called from within a Flask app context.
"""


import typing
import datetime

import flask
import sqlalchemy

from .components import get_component_by_uuid
from ..models import Objects, Object, FederatedObject, Action, ActionType, Permissions
from . import object_log, user_log, object_permissions, errors, users, actions, tags
from .notifications import create_notification_for_being_referenced_by_object_metadata
from .errors import CreatingObjectsDisabledError
from .utils import cache
from .schemas.utils import data_iter
from .. import db


def create_object(
        action_id: int,
        data: typing.Dict[str, typing.Any],
        user_id: int,
        previous_object_id: typing.Optional[int] = None,
        schema: typing.Optional[typing.Dict[str, typing.Any]] = None,
        copy_permissions_object_id: typing.Optional[int] = None,
        permissions_for_group_id: typing.Optional[int] = None,
        permissions_for_project_id: typing.Optional[int] = None,
        permissions_for_all_users: typing.Optional[Permissions] = None,
        validate_data: bool = True,
        data_validator_arguments: typing.Optional[typing.Dict[str, typing.Any]] = None,
        hash_data: typing.Optional[str] = None,
        hash_metadata: typing.Optional[str] = None
) -> Object:
    """
    Creates an object using the given action and its schema. This function
    also handles logging, object references and default object permissions.

    :param action_id: the ID of an existing action
    :param data: the object's data, which must fit to the action's schema
    :param user_id: the ID of the user who created the object
    :param previous_object_id: the ID of the base object
    :param schema: the object schema used for validation. If schema is None
        the action schema is used
    :param copy_permissions_object_id: the ID of an existing object to copy
        the permissions from or None
    :param permissions_for_group_id: the ID of an existing group to give
        permissions to
    :param permissions_for_project_id: the ID of an existing project to give
        permissions to
    :param permissions_for_all_users: permissions to be granted to all
        signed-in users, or None
    :param validate_data: whether the data should be validated
    :param data_validator_arguments: additional keyword arguments to the data
        validator
    :param hash_data: the hash value of the data and schema
    :param hash_metadata: the hash value of the metadata (user and timestamp)
    :return: the created object
    :raise errors.ActionDoesNotExistError: when no action with the given
        action ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    :raise errors.CreatingObjectsDisabledError: when creating objects is
        disabled for the given action
    """
    action = actions.get_action(action_id)
    if action.type is not None and action.type.disable_create_objects:
        raise CreatingObjectsDisabledError()
    users.check_user_exists(user_id)
    if data_validator_arguments is None:
        data_validator_arguments = {}
    # unless file names are explicitly provided, assume no files exist yet
    if 'file_names_by_id' not in data_validator_arguments:
        data_validator_arguments['file_names_by_id'] = {}
    object = Objects.create_object(
        data=data,
        schema=schema,
        user_id=user_id,
        action_id=action_id,
        validate_data=validate_data,
        data_validator_arguments=data_validator_arguments,
        hash_data=hash_data,
        hash_metadata=hash_metadata
    )
    if copy_permissions_object_id is not None:
        object_permissions.copy_permissions(object.id, copy_permissions_object_id)
        object_permissions.set_user_object_permissions(object.id, user_id, Permissions.GRANT)
    elif permissions_for_group_id is not None:
        object_permissions.set_group_object_permissions(object.id, permissions_for_group_id, Permissions.GRANT)
    elif permissions_for_project_id is not None:
        object_permissions.set_project_object_permissions(object.id, permissions_for_project_id, Permissions.GRANT)
    else:
        object_permissions.set_initial_permissions(object)
    if permissions_for_all_users is not None:
        object_permissions.set_object_permissions_for_all_users(object.id, permissions_for_all_users)
    object_log.create_object(object_id=object.object_id, user_id=user_id, previous_object_id=previous_object_id)
    user_log.create_object(object_id=object.object_id, user_id=user_id)
    _update_object_references(object, user_id=user_id)
    _send_user_references_notifications(object, user_id)
    tags.update_object_tag_usage(object)
    return object


def create_eln_import_object(
        eln_import_id: int,
        eln_object_id: str,
        action_id: typing.Optional[int],
        data: typing.Optional[typing.Dict[str, typing.Any]],
        schema: typing.Optional[typing.Dict[str, typing.Any]],
        importing_user_id: int,
        user_id: typing.Optional[int],
        utc_datetime: typing.Optional[datetime.datetime],
        data_validator_arguments: typing.Optional[typing.Dict[str, typing.Any]] = None
) -> Object:
    users.check_user_exists(importing_user_id)
    if user_id:
        users.check_user_exists(user_id)
    if data_validator_arguments is None:
        data_validator_arguments = {}
    object = Objects.create_object(
        data=data,
        schema=schema,
        user_id=user_id,
        action_id=action_id,
        utc_datetime=utc_datetime,
        eln_import_id=eln_import_id,
        eln_object_id=eln_object_id,
        data_validator_arguments=data_validator_arguments
    )
    if user_id:
        _update_object_references(object, user_id=user_id)
    object_permissions.set_initial_permissions(object, user_id=importing_user_id)
    object_log.import_from_eln_file(object_id=object.object_id, user_id=importing_user_id)
    user_log.import_from_eln_file(object_id=object.object_id, user_id=importing_user_id)
    tags.update_object_tag_usage(object)
    return object


def insert_fed_object_version(
        fed_object_id: int,
        fed_version_id: int,
        component_id: typing.Optional[int],
        action_id: typing.Optional[int],
        schema: typing.Optional[typing.Dict[str, typing.Any]],
        data: typing.Optional[typing.Dict[str, typing.Any]],
        user_id: typing.Optional[int],
        utc_datetime: typing.Optional[datetime.datetime],
        version_component_id: typing.Optional[int] = None,
        hash_data: typing.Optional[str] = None,
        hash_metadata: typing.Optional[str] = None,
        allow_disabled_languages: bool = False,
        get_missing_schema_from_action: bool = True
) -> typing.Optional[Object]:
    """
    Inserts an imported object version into local object versions.

    :param fed_object_id: the federated object ID
    :param fed_version_id: the federated version ID
    :param component_id: the ID of the component
    :param action_id: the ID of an existing action, optional
    :param schema: the object schema used for validation. If schema is None
        the action schema is used, optional
    :param data: the object's data, which must fit to the action's schema, optional
    :param user_id: the ID of the user who created the object, optional
    :param utc_datetime: the creation datetime of the version to insert
    :param version_component_id: the ID of the component where the version was created
    :param hash_data: hash value of the data of the object version
    :param hash_metadata: hash value of the metadata of the object version
    :param allow_disabled_languages: whether disabled languages may be allowed
        in data
    :param get_missing_schema_from_action: whether to use an action schema (if available) when None is passed for schema
    :return: the created object
    :raise errors.ActionDoesNotExistError: when no action with the given
        action ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    if action_id is not None:
        actions.check_action_exists(action_id)
    if user_id is not None:
        users.check_user_exists(user_id)
    if data is not None:
        from .federation.components import create_components_from_data
        create_components_from_data(data)

    object = Objects.insert_fed_object_version(
        data=data,
        schema=schema,
        user_id=user_id,
        action_id=action_id,
        utc_datetime=utc_datetime,
        fed_object_id=fed_object_id,
        fed_version_id=fed_version_id,
        component_id=component_id,
        version_component_id=version_component_id,
        hash_data=hash_data,
        hash_metadata=hash_metadata,
        allow_disabled_languages=allow_disabled_languages,
        get_missing_schema_from_action=get_missing_schema_from_action
    )
    if object is not None:
        tags.update_object_tag_usage(object)
    return object


def create_object_batch(
        action_id: int,
        data_sequence: typing.Sequence[typing.Dict[str, typing.Any]],
        user_id: int,
        copy_permissions_object_id: typing.Optional[int] = None,
        permissions_for_group_id: typing.Optional[int] = None,
        permissions_for_project_id: typing.Optional[int] = None,
        permissions_for_all_users: typing.Optional[Permissions] = None,
        validate_data: bool = True,
        data_validator_arguments: typing.Optional[typing.Dict[str, typing.Any]] = None
) -> typing.Sequence[Object]:
    """
    Creates a batch of objects using the given action and its schema. This
    function also handles logging, object references and default object
    permissions. When creating multiple objects for the same action and user
    this function should be used instead of repeatedly calling create_object.

    :param action_id: the ID of an existing action
    :param data_sequence: a sequence containing the objects' data, which must
        fit to the action's schema
    :param user_id: the ID of the user who created the objects
    :param copy_permissions_object_id: the ID of an existing object to copy
        the permissions from or None
    :param permissions_for_group_id: the ID of an existing group to give
        permissions to
    :param permissions_for_project_id: the ID of an existing project to give
        permissions to
    :param permissions_for_all_users: permissions to be granted to all
        signed-in users, or None
    :param validate_data: whether the data should be validated
    :param data_validator_arguments: additional keyword arguments to the data
        validator
    :return: the created objects
    :raise errors.ActionDoesNotExistError: when no action with the given
        action ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    objects: typing.List[Object] = []
    actions.check_action_exists(action_id)
    users.check_user_exists(user_id)
    if data_validator_arguments is None:
        data_validator_arguments = {}
    # unless file names are explicitly provided, assume no files exist yet
    if 'file_names_by_id' not in data_validator_arguments:
        data_validator_arguments['file_names_by_id'] = {}
    try:
        for data in data_sequence:
            object = Objects.create_object(
                data=data,
                schema=None,
                user_id=user_id,
                action_id=action_id,
                validate_data=validate_data,
                data_validator_arguments=data_validator_arguments
            )
            objects.append(object)
    finally:
        if objects:
            # objects created before the integrity error must still be accessible
            batch_object_ids = [object.id for object in objects]
            user_log.create_batch(user_id=user_id, batch_object_ids=batch_object_ids)
            for object in objects:
                _update_object_references(object, user_id=user_id)
                _send_user_references_notifications(object, user_id)
                if copy_permissions_object_id is not None:
                    object_permissions.copy_permissions(object.id, copy_permissions_object_id)
                    object_permissions.set_user_object_permissions(object.id, user_id, Permissions.GRANT)
                elif permissions_for_group_id is not None:
                    object_permissions.set_group_object_permissions(object.id, permissions_for_group_id, Permissions.GRANT)
                elif permissions_for_project_id is not None:
                    object_permissions.set_project_object_permissions(object.id, permissions_for_project_id, Permissions.GRANT)
                else:
                    object_permissions.set_initial_permissions(object)
                if permissions_for_all_users is not None:
                    object_permissions.set_object_permissions_for_all_users(object.id, permissions_for_all_users)
                object_log.create_batch(object_id=object.object_id, user_id=user_id, batch_object_ids=batch_object_ids)
                tags.update_object_tag_usage(object)
    return objects


def update_object(
        object_id: int,
        data: typing.Optional[typing.Dict[str, typing.Any]],
        user_id: typing.Optional[int],
        schema: typing.Optional[typing.Dict[str, typing.Any]] = None,
        version_component_id: typing.Optional[int] = None,
        hash_data: typing.Optional[str] = None,
        hash_metadata: typing.Optional[str] = None,
        data_validator_arguments: typing.Optional[typing.Dict[str, typing.Any]] = None,
        create_log_entries: bool = True,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        created_by_automerge: bool = False
) -> None:
    """
    Updates the object to a new version. This function also handles logging
    and object references.

    :param object_id: the ID of the existing object
    :param data: the object's new data, which must fit to the object's schema
    :param user_id: the ID of the user who updated the object
    :param schema: the schema for the new object data
    :param version_component_id: the ID of the component where the version was created
    :param hash_data: hash value of the data of the object version
    :param hash_metadata: hash value of the metadata of the object version
    :param data_validator_arguments: additional keyword arguments to the data
        validator
    :param create_log_entries: whether log entries should be created
    :param utc_datetime: the datetime of the update, or None
    :param created_by_automerge: whether the object was created by an automerge of two differing versions
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    if data_validator_arguments is None:
        data_validator_arguments = {}
    if 'file_names_by_id' not in data_validator_arguments:
        # local import to avoid circular imports
        from .files import get_file_names_by_id_for_object
        data_validator_arguments['file_names_by_id'] = {
            file_id: file_names[0]
            for file_id, file_names in get_file_names_by_id_for_object(object_id).items()
        }
    object = Objects.update_object(
        object_id=object_id,
        data=data,
        schema=schema,
        user_id=user_id,
        data_validator_arguments=data_validator_arguments,
        utc_datetime=utc_datetime,
        version_component_id=version_component_id,
        hash_data=hash_data,
        hash_metadata=hash_metadata
    )
    if object is None:
        raise errors.ObjectDoesNotExistError()
    if create_log_entries:
        if user_id is not None:
            user_log.edit_object(user_id=user_id, object_id=object.object_id, version_id=object.version_id)
            object_log.edit_object(object_id=object.object_id, user_id=user_id, version_id=object.version_id)
    if user_id is not None:
        _update_object_references(object, user_id=user_id)
        _send_user_references_notifications(object, user_id)
    tags.update_object_tag_usage(object)


def update_object_version(
        object_id: int,
        version_id: int,
        action_id: typing.Optional[int],
        data: typing.Optional[typing.Dict[str, typing.Any]],
        user_id: typing.Optional[int],
        schema: typing.Optional[typing.Dict[str, typing.Any]] = None,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        hash_metadata: typing.Optional[str] = None,
        hash_data_none_replacement: typing.Optional[str] = None,
        version_component_id: typing.Optional[int] = None,
        allow_disabled_languages: bool = False,
        get_missing_schema_from_action: bool = True
) -> Object:
    object = Objects.update_object_version(
        object_id=object_id,
        version_id=version_id,
        action_id=action_id,
        schema=schema,
        data=data,
        user_id=user_id,
        utc_datetime=utc_datetime,
        hash_metadata=hash_metadata,
        hash_data_none_replacement=hash_data_none_replacement,
        version_component_id=version_component_id,
        allow_disabled_languages=allow_disabled_languages,
        get_missing_schema_from_action=get_missing_schema_from_action
    )
    if object is None:
        check_object_version_exists(object_id, version_id)
        raise errors.ObjectNotFederatedError()
    tags.update_object_tag_usage(object, new_subversion=True)

    return object


def add_subversion(
    object_id: int,
    version_id: int,
    action_id: typing.Optional[int],
    schema: typing.Optional[typing.Dict[str, typing.Any]],
    data: typing.Optional[typing.Dict[str, typing.Any]],
    user_id: typing.Optional[int],
    utc_datetime: typing.Optional[datetime.datetime],
    version_component_id: typing.Optional[int],
    hash_metadata: typing.Optional[str],
    allow_disabled_languages: bool = False,
    get_missing_schema_from_action: bool = True
) -> bool:
    """
    Add a subversion for a specified version of an object.

    :param object_id: the ID of the existing object
    :param version_id: the version ID of the existing object
    :param action_id: the ID of the existing action
    :param schema: a JSON schema describing data (optional, defaults to the current object schema)
    :param data: a JSON serializable object containing the updated object data
    :param user_id: the ID of the user who updated the object
    :param utc_datetime: the datetime (in UTC) when the object was updated
    :param version_component_id: the ID of the component where the object version was created
    :param hash_metadata: the hash value of the object metadata
    :param allow_disabled_languages: whether using disabled languages should be allowed in this update
    :param get_missing_schema_from_action: whether to use an action schema (if available) when None is passed for schema
    :return: True if a new subversion was added
    """
    return Objects.add_subversion(
        object_id=object_id,
        version_id=version_id,
        action_id=action_id,
        schema=schema,
        data=data,
        user_id=user_id,
        utc_datetime=utc_datetime,
        version_component_id=version_component_id,
        hash_metadata=hash_metadata,
        utc_datetime_subversion=None,
        allow_disabled_languages=allow_disabled_languages,
        get_missing_schema_from_action=get_missing_schema_from_action
    )


def restore_object_version(object_id: int, version_id: int, user_id: int) -> None:
    """
    Reverts the changes made to an object and restores a specific version of
    it, while keeping the version history. This function merely adds a new
    version which sets the data and schema to those of the given version.

    :param object_id: the ID of the existing object
    :param version_id: the ID of the object's existing version
    :param user_id: the ID of the user who restored the object version
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.ObjectVersionDoesNotExistError: when an object with the
        given object ID exists, but does not have a version with the given
        version ID
    :raise errors.UserDoesNotExistError: when no user with the given
        user ID exists
    """
    object = Objects.restore_object_version(
        object_id=object_id,
        version_id=version_id,
        user_id=user_id
    )
    if object is None:
        # ensure the object actually exists
        check_object_version_exists(object_id=object_id, version_id=version_id)
        return
    user_log.restore_object_version(user_id=user_id, object_id=object_id, restored_version_id=version_id, version_id=object.version_id)
    object_log.restore_object_version(object_id=object_id, user_id=user_id, restored_version_id=version_id, version_id=object.version_id)
    tags.update_object_tag_usage(object)


@cache
def check_object_exists(object_id: int) -> None:
    """
    Ensures that an object with the specific ID exists.

    :param object_id: the ID of the existing object

    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    if not Objects.is_existing_object(object_id=object_id):
        raise errors.ObjectDoesNotExistError()


@cache
def check_object_version_exists(object_id: int, version_id: int, component_id: typing.Optional[int] = None) -> None:
    """
    Ensures that an object version with the given IDs exists.

    :param object_id: the ID of the existing object
    :param version_id: the ID of the existing version for that object
    :param component_id: the ID of the component of the object version (None, checks the regular object history. Otherwise, checks the federated object version)

    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.ObjectVersionDoesNotExistError: when no object version
        with the given object ID and version ID combination exists
    """
    if not Objects.is_existing_object_version(object_id=object_id, version_id=version_id, version_component_id=component_id):
        check_object_exists(object_id)
        raise errors.ObjectVersionDoesNotExistError()


def get_object(object_id: int, version_id: typing.Optional[int] = None) -> Object:
    """
    Returns either the current or a specific version of the object.

    :param object_id: the ID of the existing object
    :param version_id: the ID of the object's existing version
    :return: the object with the given object and version IDs
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.ObjectVersionDoesNotExistError: when an object with the
        given object ID exists, but does not have a version with the given
        version ID
    """
    if version_id is None:
        object = Objects.get_current_object(
            object_id=object_id
        )
        if object is None:
            raise errors.ObjectDoesNotExistError()
    else:
        object = Objects.get_object_version(
            object_id=object_id,
            version_id=version_id
        )
        if object is None:
            if Objects.get_current_object(object_id=object_id) is None:
                raise errors.ObjectDoesNotExistError()
            else:
                raise errors.ObjectVersionDoesNotExistError()
    return object


def get_fed_object(fed_object_id: int, component_id: int, fed_version_id: typing.Optional[int] = None, local_version: bool = False) -> Object:
    """
    Returns either the current or a specific version of the federated object.

    :param fed_object_id: the federated ID of the existing object
    :param component_id: the ID of the existing component
    :param fed_version_id: the ID of the object's existing version
    :param local_version: if local_version is set to true, the fed_version_id will be used as the local version id
    :return: the object with the given object and version IDs
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.ObjectVersionDoesNotExistError: when an object with the
        given object ID exists, but does not have a version with the given
        version ID
    """
    if fed_version_id is None:
        object = Objects.get_current_fed_object(
            fed_object_id=fed_object_id,
            component_id=component_id
        )
        if object is None:
            raise errors.ObjectDoesNotExistError()
    else:
        object = Objects.get_fed_object_version(
            component_id=component_id,
            fed_object_id=fed_object_id,
            fed_version_id=fed_version_id,
            local_version=local_version
        )
        if object is None:
            if Objects.get_current_fed_object(fed_object_id=fed_object_id, component_id=component_id) is None:
                raise errors.ObjectDoesNotExistError()
            else:
                raise errors.ObjectVersionDoesNotExistError()
    return object


def get_object_versions(object_id: int) -> typing.List[Object]:
    """
    Returns all versions of an object, sorted from oldest to newest.

    :param object_id: the ID of the existing object
    :return: the object versions
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    object_versions = Objects.get_object_versions(object_id=object_id)
    if not object_versions:
        raise errors.ObjectDoesNotExistError()
    return object_versions


def get_objects(
        filter_func: typing.Callable[[typing.Any], typing.Any] = lambda data: True,
        action_filter: typing.Optional[sqlalchemy.sql.ColumnElement[bool]] = None,
        **kwargs: typing.Any
) -> typing.List[Object]:
    """
    Returns all objects, optionally after filtering the objects by their data
    or by their actions' information.

    :param filter_func: a lambda that may return an SQLAlchemy filter when
        given the object table's data column
    :param action_filter: a SQLAlchemy comparator, used to query only objects
        created by specific actions
    :param kwargs: additional parameters to be passed to Objects.get_current_objects
    :return: a list of all objects or those matching the given filters
    """
    if action_filter is None:
        action_table = None
    else:
        action_table = Action.__table__
    return Objects.get_current_objects(
        filter_func=filter_func,
        action_table=action_table,
        action_filter=action_filter,
        **kwargs
    )


@typing.overload
def find_object_references(
        *,
        object_id: int,
        version_id: int,
        object_data: typing.Optional[typing.Dict[str, typing.Any]],
        find_previous_referenced_object_ids: bool = True,
        include_fed_references: typing.Literal[True]
) -> typing.Sequence[typing.Tuple[typing.Tuple[int, typing.Optional[str]], typing.Optional[int], str]]:
    ...


@typing.overload
def find_object_references(
        *,
        object_id: int,
        version_id: int,
        object_data: typing.Optional[typing.Dict[str, typing.Any]],
        find_previous_referenced_object_ids: bool = True,
        include_fed_references: typing.Literal[False] = False
) -> typing.Sequence[typing.Tuple[int, typing.Optional[int], str]]:
    ...


def find_object_references(
        *,
        object_id: int,
        version_id: int,
        object_data: typing.Optional[typing.Dict[str, typing.Any]],
        find_previous_referenced_object_ids: bool = True,
        include_fed_references: bool = False,
) -> typing.Sequence[typing.Tuple[typing.Union[int, typing.Tuple[int, typing.Optional[str]]], typing.Optional[int], str]]:
    """
    Searches for references to other objects.

    :param object_id: the object ID
    :param version_id: the object version ID
    :param object_data: the object data
    :param find_previous_referenced_object_ids: whether to find previous referenced object ids
    :param include_fed_references: whether references on other components should be included
    """
    if object_data is None:
        return []
    referenced_object_ids = []
    referenced_object_id: typing.Union[int, typing.Tuple[int, typing.Optional[str]]]
    for path, data in data_iter(data=object_data, filter_property_types={'sample', 'measurement', 'object_reference'}):
        if isinstance(data, dict) and data.get('object_id') is not None:
            if 'component_uuid' in data and data['component_uuid'] != flask.current_app.config['FEDERATION_UUID']:
                try:
                    component = get_component_by_uuid(data['component_uuid'])
                    if include_fed_references:
                        referenced_object_id = (get_fed_object(data['object_id'], component.id).object_id, None)
                    else:
                        referenced_object_id = get_fed_object(data['object_id'], component.id).object_id
                except errors.ComponentDoesNotExistError:
                    if include_fed_references:
                        referenced_object_id = (data['object_id'], data['component_uuid'])
                    else:
                        continue
                except errors.ObjectDoesNotExistError:
                    if include_fed_references:
                        referenced_object_id = (data['object_id'], data['component_uuid'])
                    else:
                        continue
                previous_referenced_object_id = None
            elif 'eln_source_url' in data:
                continue
            else:
                if include_fed_references:
                    referenced_object_id = (data['object_id'], None)
                else:
                    referenced_object_id = data['object_id']
                previous_referenced_object_id = None
                if find_previous_referenced_object_ids and version_id > 0:
                    previous_object_version = get_object(object_id, version_id - 1)
                    previous_data = previous_object_version.data
                    try:
                        for path_element in path:
                            previous_data = previous_data[path_element]  # type: ignore
                    except (KeyError, IndexError):
                        pass
                    else:
                        if previous_data is not None and 'object_id' in previous_data and previous_data['object_id'] is not None:
                            previous_referenced_object_id = previous_data['object_id']
            referenced_object_ids.append((referenced_object_id, previous_referenced_object_id, data['_type']))
    return referenced_object_ids


def _update_object_references(object: Object, user_id: int) -> None:
    """
    Searches for references to other objects and updates these accordingly.

    At this time, only measurements or samples referencing other measurements
    or samples will be handled, adding an entry to the object's log about
    being used in a sample or measurement.

    :param object: the updated (or newly created) object
    :param user_id: the user who caused the object update or creation
    """
    if object.action_id is None:
        action_type_id = None
    else:
        action_type_id = actions.get_action(object.action_id).type_id
    for referenced_object_id, previous_referenced_object_id, schema_type in find_object_references(object_id=object.object_id, version_id=object.version_id, object_data=object.data):
        if referenced_object_id != previous_referenced_object_id:
            if action_type_id == ActionType.MEASUREMENT and schema_type == 'sample':
                object_log.use_object_in_measurement(object_id=referenced_object_id, user_id=user_id, measurement_id=object.object_id)
            elif action_type_id == ActionType.SAMPLE_CREATION and schema_type == 'sample':
                object_log.use_object_in_sample(object_id=referenced_object_id, user_id=user_id, sample_id=object.object_id)
            else:
                object_log.reference_object_in_metadata(object_id=referenced_object_id, user_id=user_id, referencing_object_id=object.object_id)


def _send_user_references_notifications(object: Object, user_id: int) -> None:
    """
    Searches for references to users and notifies them accordingly.

    :param object: the updated (or newly created) object
    :param user_id: the user who caused the object update or creation
    """

    for referenced_user_id, previous_referenced_user_id in find_user_references(object):
        if referenced_user_id not in {user_id, previous_referenced_user_id}:
            create_notification_for_being_referenced_by_object_metadata(referenced_user_id, object.object_id)


def find_user_references(object: Object, find_previous_referenced_user_ids: bool = True) -> typing.List[typing.Tuple[int, typing.Optional[int]]]:
    """
    Searches for references to users.

    :param object: the updated (or newly created) object
    :param find_previous_referenced_user_ids: whether to find previous
        referenced user ids
    """
    if object.data is None:
        return []
    referenced_user_ids = []
    for path, data in data_iter(data=object.data, filter_property_types={'user'}):
        if isinstance(data, dict) and data.get('user_id') is not None:
            referenced_user_id = data['user_id']
            previous_referenced_user_id = None
            if find_previous_referenced_user_ids and object.version_id > 0:
                previous_object_version = get_object(object.object_id, object.version_id - 1)
                previous_data = previous_object_version.data
                try:
                    for path_element in path:
                        previous_data = previous_data[path_element]  # type: ignore
                except (KeyError, IndexError):
                    pass
                else:
                    if previous_data is not None and 'user_id' in previous_data and previous_data['user_id'] is not None:
                        previous_referenced_user_id = previous_data['user_id']
            referenced_user_ids.append((referenced_user_id, previous_referenced_user_id))
    return referenced_user_ids


def get_current_object_version_id(object_id: int) -> int:
    """
    Get the ID of the current version of an object.

    :param object_id: the ID of an existing object
    :return: the object's current version ID
    :raises errors.ObjectDoesNotExistError: if the object does not exist
    """
    version_id = Objects.get_current_object_version_id(object_id)
    if version_id is None:
        raise errors.ObjectDoesNotExistError()
    return version_id


def get_action_ids_for_object_ids(
        object_ids: typing.Sequence[int]
) -> typing.Dict[int, typing.Optional[int]]:
    """
    Get the action IDs for a list of object IDs.

    :param object_ids: the IDs of existing objects
    :return: the objects' action IDs
    """
    return Objects.get_action_ids_for_object_ids(object_ids)


def get_max_object_id() -> typing.Optional[int]:
    """
    Get the maximum object ID.

    :return: the largest existing object ID, or None if no objects exist
    """
    return typing.cast(typing.Optional[int], db.session.query(db.func.max(Objects.object_id_column)).scalar())


def create_conflicting_federated_object(
    object_id: int,
    fed_version_id: int,
    version_component_id: int,
    data: typing.Optional[dict[str, typing.Any]],
    schema: typing.Optional[dict[str, typing.Any]],
    action_id: typing.Optional[int],
    utc_datetime: typing.Optional[datetime.datetime],
    user_id: typing.Optional[int],
    local_parent: typing.Optional[int],
    hash_data: typing.Optional[str],
    hash_metadata: typing.Optional[str],
) -> FederatedObject:
    """
    Create a conflicting version.

    :param object_id: the ID of the existing object
    :param fed_version_id: the version ID of the existing object at the federation partner
    :param version_component_id: the ID of the component where the version was created
    :param data: a JSON serializable object containing the object data
    :param schema: a JSON schema describing data
    :param action_id: the ID of the action
    :param utc_datetime: the datetime (in UTC) when the object version was created
    :param user_id: the ID of the user who created the object version
    :param local_parent: the ID of the local parent object version (None if parent is a conflicting version)
    :param hash_data: the hash of the data and schema
    :param hash_metadata: the hash of the metadata (user and time)
    :return: the created federated object
    """
    return Objects.create_conflicting_federated_object(
        object_id=object_id,
        fed_version_id=fed_version_id,
        version_component_id=version_component_id,
        data=data,
        schema=schema,
        action_id=action_id,
        utc_datetime=utc_datetime,
        user_id=user_id,
        local_parent=local_parent,
        hash_data=hash_data,
        hash_metadata=hash_metadata
    )


def update_conflicting_federated_object_version(
    object_id: int,
    fed_version_id: int,
    version_component_id: int,
    data: typing.Optional[dict[str, typing.Any]],
    schema: typing.Optional[dict[str, typing.Any]],
    action_id: typing.Optional[int],
    utc_datetime: typing.Optional[datetime.datetime],
    user_id: typing.Optional[int]
) -> FederatedObject:
    """
    Update a conflicting object version.

    :param object_id: the ID of the existing object
    :param fed_version_id: the version ID of the existing object at the federation partner
    :param version_component_id: the ID of the component where the version was created
    :param data: a JSON serializable object containing the object data
    :param schema: a JSON schema describing data
    :param action_id: the ID of the action
    :param utc_datetime: the datetime (in UTC) when the object version was created
    :param user_id: the ID of the user who created the object version
    :return: the updated federated object
    :raise errors.FederatedObjectVersionDoesNotExistError: when the federated object version to update does not exist
    """
    object = Objects.update_conflicting_federated_object(
        object_id=object_id,
        fed_version_id=fed_version_id,
        version_component_id=version_component_id,
        data=data,
        schema=schema,
        action_id=action_id,
        utc_datetime=utc_datetime,
        user_id=user_id
    )

    if object is None:
        raise errors.FederatedObjectVersionDoesNotExistError()
    return object


def get_conflicting_federated_object_version(
    object_id: int,
    fed_version_id: int,
    version_component_id: int
) -> FederatedObject:
    """
    Get a conflicting federated object version.

    :param object_id: the local ID of the existing object
    :param fed_version_id: the version ID of the existing object at the federation partner
    :param version_component_id: the ID of the component where the object version was created
    :return: the federated object version or none
    :raise errors.FederatedObjectVersionDoesNotExistError: when no federated object version exists that matches the given parameters
    """
    object = Objects.get_conflicting_federated_object(object_id, fed_version_id, version_component_id)
    if object is None:
        raise errors.FederatedObjectVersionDoesNotExistError()
    return object


def update_federated_object_version(
    object_id: int,
    fed_version_id: int,
    version_component_id: int,
    data: typing.Optional[dict[str, typing.Any]],
    schema: typing.Optional[typing.Dict[str, typing.Any]],
    action_id: typing.Optional[int],
    user_id: typing.Optional[int],
    utc_datetime: typing.Optional[datetime.datetime],
) -> FederatedObject:
    """
    Update a conflicting object version and add updated version to the federated subversions table.

    :param object_id: the ID of the existing object
    :param fed_version_id: the version ID of the existing object at the federation partner
    :param version_component_id: the ID of the component where the version was created
    :param data: a JSON serializable object containing the object data
    :param schema: a JSON schema describing data
    :param action_id: the ID of the action
    :param utc_datetime: the datetime (in UTC) when the object version was created
    :param user_id: the ID of the user who created the object version
    :return: the created federated object
    :raise errors.FederatedObjectVersionDoesNotExistError: when the federated object version to update does not exist
    """
    if object := Objects.update_conflicting_federated_object(
        object_id,
        fed_version_id,
        version_component_id,
        data,
        schema,
        action_id,
        user_id,
        utc_datetime
    ):
        return object
    raise errors.FederatedObjectVersionDoesNotExistError()


def get_first_conflicting_object_version_by_conflict(
    object_id: int,
    version_component_id: int,
    local_parent: int
) -> FederatedObject:
    """
    Get the first federated object version of an object version conflict.

    :param object_id: the local ID of the existing object
    :param version_component_id: the ID of the component where the object version was created
    :param local_parent: the local version ID of the parent
    :return: the first federated object version of an conflict or none
    :raise errors.ObjectVersionDoesNotExistError: when no federated object version exists that matches the given parameters
    """
    if object := Objects.get_first_conflicting_object_version_by_conflict(object_id, version_component_id, local_parent):
        return object
    raise errors.ObjectVersionDoesNotExistError()


def get_latest_version_containing_data_information(object_id: int) -> typing.Optional[Object]:
    """
    Returns the latest local version that contains data and schema information.

    :param object_id: the ID of the existing object
    :return: local object version containing data and schema informations or none
    """
    versions = get_object_versions(object_id)
    for version in versions[::-1]:
        if version.data is not None and version.schema is not None:
            return version
    return None
