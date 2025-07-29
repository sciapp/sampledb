import base64
import datetime
import typing

import flask
from flask_babel import _

from .utils import _get_id, _get_uuid, _get_str, _get_dict, _get_list, _get_utc_datetime, _get_permissions
from .users import _parse_user_ref, _get_or_create_user_id, UserRef
from .actions import _parse_action_ref, _get_or_create_action_id, schema_entry_preprocessor, _parse_schema, ActionRef
from .comments import import_comment, parse_comment, CommentData
from .files import import_file, parse_file, FileData
from .object_location_assignments import import_object_location_assignment, parse_object_location_assignment, ObjectLocationAssignmentData
from .locations import LocationRef
from .conflicts import create_object_version_conflict, update_object_version_conflict, get_object_version_conflict, get_next_object_version_conflict, solve_conflict_by_strategy, try_automerge_open_conflicts, SolvingStrategy
from ..files import get_files_for_object, get_file
from ..markdown_images import find_referenced_markdown_images, get_markdown_image
from ..object_permissions import set_user_object_permissions, set_group_object_permissions, set_project_object_permissions, set_object_permissions_for_all_users, object_permissions
from ..schemas import validate_schema, validate
from ..schemas.validate import validate_eln_urls
from ..actions import get_action
from ..comments import get_comments_for_object
from ..components import get_component_by_uuid, get_component, Component
from ..groups import get_group
from ..locations import get_location, get_object_location_assignments
from ..objects import get_fed_object, get_object, update_object_version, insert_fed_object_version, get_object_versions, create_conflicting_federated_object, get_conflicting_federated_object_version, update_conflicting_federated_object_version, add_subversion, update_federated_object_version
from ..projects import get_project
from ..users import get_user, check_user_exists
from ..components import add_component
from ..shares import get_share
from .. import errors, fed_logs, languages, markdown_to_html, object_log
from ...models import Permissions, Object
from ...models.file_log import FileLogEntry, FileLogEntryType


class ObjectVersionData(typing.TypedDict):
    fed_version_id: int
    version_component_id: typing.Optional[int]
    user: typing.Optional[UserRef]
    data: typing.Optional[typing.Dict[str, typing.Any]]
    schema: typing.Optional[typing.Dict[str, typing.Any]]
    utc_datetime: typing.Optional[datetime.datetime]
    import_notes: typing.List[str]
    hash_data: typing.Optional[str]
    hash_metadata: typing.Optional[str]


class ObjectPermissionsData(typing.TypedDict):
    users: typing.Dict[int, Permissions]
    groups: typing.Dict[int, Permissions]
    projects: typing.Dict[int, Permissions]
    all_users: Permissions


class ObjectData(typing.TypedDict):
    fed_object_id: int
    component_id: typing.Optional[int]
    action: typing.Optional[ActionRef]
    versions: typing.List[ObjectVersionData]
    comments: typing.List[CommentData]
    files: typing.List[FileData]
    object_location_assignments: typing.List[ObjectLocationAssignmentData]
    permissions: ObjectPermissionsData
    sharing_user: typing.Optional[UserRef]


class SharedFileHideData(typing.TypedDict):
    user: UserRef
    reason: str
    utc_datetime: datetime.datetime


class SharedFileData(typing.TypedDict):
    file_id: int
    component_uuid: str
    user: typing.Optional[UserRef]
    data: typing.Optional[typing.Dict[str, typing.Any]]
    utc_datetime: typing.Optional[str]
    hidden: typing.Optional[SharedFileHideData]


class SharedCommentData(typing.TypedDict):
    comment_id: int
    component_uuid: str
    user: typing.Optional[UserRef]
    content: typing.Optional[str]
    utc_datetime: datetime.datetime


class SharedObjectVersionData(typing.TypedDict):
    version_id: int
    version_component_uuid: str
    user: typing.Optional[UserRef]
    data: typing.Optional[typing.Dict[str, typing.Any]]
    schema: typing.Optional[typing.Dict[str, typing.Any]]
    utc_datetime: typing.Optional[str]
    hash_data: typing.Optional[str]
    hash_metadata: typing.Optional[str]


class SharedObjectLocationAssignmentData(typing.TypedDict):
    id: int
    component_uuid: str
    location: typing.Optional[LocationRef]
    responsible_user: typing.Optional[UserRef]
    user: typing.Optional[UserRef]
    description: typing.Optional[typing.Dict[str, str]]
    utc_datetime: typing.Optional[str]
    confirmed: bool
    declined: bool


class SharedObjectData(typing.TypedDict):
    object_id: int
    component_uuid: str
    action: typing.Optional[ActionRef]
    versions: typing.List[SharedObjectVersionData]
    comments: typing.List[SharedCommentData]
    files: typing.List[SharedFileData]
    object_location_assignments: typing.List[SharedObjectLocationAssignmentData]
    policy: typing.Dict[str, typing.Any]
    sharing_user: typing.Optional[UserRef]


class ConflictDetails(typing.TypedDict):
    fed_version_id: int
    base_version_id: int
    automerged: bool


class ImportContext(typing.TypedDict):
    component: Component
    action_id: typing.Optional[int]
    local_object_id: typing.Optional[int]
    user_id: typing.Optional[int]
    sharing_user_id: typing.Optional[int]
    base_version_id: int
    current_local_version_id: int
    changes: bool
    conflicting: bool
    conflict_between_solutions: bool
    conflict_details: typing.Optional[ConflictDetails]
    next_conflict_solution_version_id: typing.Optional[int]
    skip_until_fed_version_id: int


def import_object(
        object_data: ObjectData,
        component: Component,
        *,
        import_status: typing.Optional[typing.Dict[str, typing.Any]] = None,
        conflict_status: typing.Optional[typing.Dict[str, typing.Any]] = None
) -> typing.Tuple[Object, bool]:
    action_id = _get_or_create_action_id(object_data['action'])
    object = None
    all_import_notes: list[str] = []

    if conflict_status is None:
        conflict_status = {}

    import_context = ImportContext(
        component=component,
        action_id=action_id,
        local_object_id=None,
        user_id=None,
        sharing_user_id=None,
        base_version_id=0,
        current_local_version_id=0,
        changes=False,
        conflicting=False,
        conflict_between_solutions=False,
        conflict_details=None,
        next_conflict_solution_version_id=None,
        skip_until_fed_version_id=-1
    )

    for version in object_data['versions']:
        try:
            if object_data['component_id'] is not None:
                object = get_fed_object(object_data['fed_object_id'], component.id, fed_version_id=import_context['current_local_version_id'], local_version=True)
            else:
                object = get_object(object_data['fed_object_id'], version_id=import_context['current_local_version_id'])
            import_context['local_object_id'] = object.object_id
        except errors.ObjectDoesNotExistError:
            object = None
        except errors.ObjectVersionDoesNotExistError:
            object = None

        import_context['user_id'] = _get_or_create_user_id(version['user'])

        if object_data['component_id'] is not None:
            import_context['sharing_user_id'] = _get_or_create_user_id(object_data.get('sharing_user'))
        else:
            import_context['sharing_user_id'] = import_context['user_id']  # Use the version user id as sharing user for changes made by a federated instance on a local object

        if version['fed_version_id'] < import_context['skip_until_fed_version_id'] and import_context['local_object_id'] is not None:
            _add_or_update_conflicting_version(version=version, import_context=import_context)
            continue

        if import_context['next_conflict_solution_version_id'] is not None and import_context['conflicting'] and import_context['local_object_id'] is not None:
            if import_context['next_conflict_solution_version_id'] == version['fed_version_id']:
                if object is None:
                    _add_federated_conflict_solution(
                        object_data=object_data,
                        version=version,
                        import_context=import_context,
                        notes=all_import_notes,
                    )

                else:
                    _update_federated_conflict_solution(
                        object=object,
                        version=version,
                        import_context=import_context,
                        notes=all_import_notes
                    )
        elif not import_context['conflicting'] or import_context['conflict_between_solutions']:
            if object is None:
                object = _add_new_local_version(object_data=object_data, version=version, import_context=import_context)
            elif object.hash_metadata != version['hash_metadata']:
                if object.hash_data == version['hash_data']:
                    import_context['current_local_version_id'] += 1
                    import_context['base_version_id'] = object.version_id
                    if add_subversion(
                        object_id=object.object_id,
                        version_id=object.version_id,
                        data=version['data'],
                        schema=version['schema'],
                        user_id=import_context['user_id'],
                        action_id=action_id,
                        utc_datetime=version['utc_datetime'],
                        version_component_id=version['version_component_id'],
                        hash_metadata=version['hash_metadata'],
                        imported_from_component_id=import_context['component'].id,
                        allow_disabled_languages=True,
                        get_missing_schema_from_action=False  # if the version contains None for the schema, do not try to load it from the action
                    ):
                        fed_logs.update_object(object.id, component.id, version.get('import_notes', []), import_context['sharing_user_id'], version['fed_version_id'])
                elif object.hash_data is None and object.hash_metadata is None:
                    if import_context['local_object_id'] is None:
                        raise errors.FederationObjectImportError()
                    update_object_version(
                        object_id=import_context['local_object_id'],
                        version_id=import_context['current_local_version_id'],
                        action_id=action_id,
                        data=version['data'],
                        user_id=import_context['user_id'],
                        schema=version['schema'],
                        utc_datetime=version['utc_datetime'],
                        hash_metadata=version['hash_metadata'],
                        hash_data_none_replacement=version['hash_data'],
                        version_component_id=version['version_component_id'],
                        imported_from_component_id=import_context['component'].id,
                    )
                    import_context['current_local_version_id'] += 1
                    import_context['base_version_id'] = object.version_id
                else:
                    import_context['conflicting'] = True
                    _check_conflicting_version_exists(version=version, import_context=import_context)
                    _find_and_apply_conflict_solution(
                        object_data=object_data,
                        version=version,
                        import_context=import_context,
                        conflict_status=conflict_status
                    )
            else:
                if (
                    object.hash_metadata == version['hash_metadata'] and
                    object.hash_data == version['hash_data'] and
                    object.version_component_id is not None and
                    (
                        object.data != version['data'] or
                        object.schema != version['schema'] or
                        object.action_id != action_id or
                        object.user_id != import_context['user_id'] or
                        object.utc_datetime != version['utc_datetime']
                    )
                ):
                    if import_context['local_object_id'] is None:
                        raise errors.FederationObjectImportError()
                    update_object_version(
                        object_id=import_context['local_object_id'],
                        version_id=import_context['current_local_version_id'],
                        action_id=action_id,
                        data=version['data'],
                        user_id=import_context['user_id'],
                        schema=version['schema'],
                        utc_datetime=version['utc_datetime'],
                        hash_metadata=version['hash_metadata'],
                        version_component_id=version['version_component_id'],
                        imported_from_component_id=import_context['component'].id,
                    )
                import_context['current_local_version_id'] += 1
                import_context['base_version_id'] = object.version_id
            all_import_notes.extend(version.get('import_notes', []))
        else:
            if import_context['local_object_id'] is None or import_context['conflict_details'] is None:
                raise errors.FederationObjectImportError()

            try:
                conflicting_object_version = get_conflicting_federated_object_version(object_id=import_context['local_object_id'], fed_version_id=version['fed_version_id'], version_component_id=component.id)
            except errors.FederatedObjectVersionDoesNotExistError:
                conflicting_object_version = None
            import_context['conflict_details']['fed_version_id'] = version['fed_version_id']
            if conflicting_object_version is None:
                if version['version_component_id'] is None:
                    raise errors.FederationObjectImportError()
                create_conflicting_federated_object(
                    object_id=import_context['local_object_id'],
                    fed_version_id=version['fed_version_id'],
                    version_component_id=version['version_component_id'],
                    data=version['data'],
                    schema=version['schema'],
                    action_id=action_id,
                    utc_datetime=version['utc_datetime'],
                    user_id=import_context['user_id'],
                    local_parent=None,
                    hash_data=version['hash_data'],
                    hash_metadata=version['hash_metadata'],
                    imported_from_component_id=import_context['component'].id,
                )
                if import_context['user_id'] is not None:
                    object_log.import_conflicting_version(
                        user_id=import_context['user_id'],
                        object_id=import_context['local_object_id'],
                        fed_version_id=version['fed_version_id'],
                        component_id=version['version_component_id'],
                    )
            elif conflicting_object_version.data != version['data']:
                update_federated_object_version(
                    object_id=conflicting_object_version.object_id,
                    fed_version_id=conflicting_object_version.fed_version_id,
                    version_component_id=conflicting_object_version.version_component_id,
                    data=version['data'],
                    schema=version['schema'],
                    action_id=action_id,
                    user_id=import_context['user_id'],
                    utc_datetime=version['utc_datetime'],
                    imported_from_component_id=import_context['component'].id,
                )

    last_version = object_data['versions'][-1]
    if import_context['conflicting'] and last_version is not None:
        if import_context['conflict_details'] is None or import_context['local_object_id'] is None:
            raise errors.FederationObjectImportError()

        try:
            conflict = get_object_version_conflict(
                object_id=import_context['local_object_id'],
                component_id=component.id,
                fed_version_id=import_context['conflict_details']['fed_version_id']
            )
        except errors.ObjectVersionConflictDoesNotExistError:
            conflict = None

        if object is not None:
            if not conflict:
                conflict = create_object_version_conflict(
                    object_id=import_context['local_object_id'],
                    component_id=component.id,
                    fed_version_id=import_context['conflict_details']['fed_version_id'],
                    base_version_id=import_context['conflict_details']['base_version_id']
                )
                all_import_notes.append(_("A conflict with version #%(version_id)s occurred.", version_id=last_version['fed_version_id']))
                fed_logs.create_version_conflict(object.object_id, component.id, fed_version_id=last_version['fed_version_id'])

            if conflict.local_version_id is None:
                try:
                    solve_conflict_by_strategy(conflict, SolvingStrategy.AUTOMERGE, None)
                    import_context['changes'] = True
                    fed_logs.solve_version_conflict(
                        object_id=object.object_id,
                        component_id=component.id,
                        fed_version_id=last_version['fed_version_id'],
                        automerged=True,
                        user_id=None
                    )
                except errors.FailedSolvingByStrategyError:
                    pass
    elif import_context['local_object_id'] is not None:
        try_automerge_open_conflicts(object_id=import_context['local_object_id'])

    if object is None:
        object = get_fed_object(
            fed_object_id=object_data['fed_object_id'],
            component_id=object_data['component_id']
        ) if object_data['component_id'] is not None else get_object(object_data['fed_object_id'])

    for comment_data in object_data['comments']:
        _c, comment_changes = import_comment(comment_data, object, component)
        import_context['changes'] = import_context['changes'] or comment_changes

    for file_data in object_data['files']:
        _f, file_changes = import_file(file_data, object, component)
        import_context['changes'] = import_context['changes'] or file_changes

    for assignment_data in object_data['object_location_assignments']:
        _a, assignment_changes = import_object_location_assignment(assignment_data, object, component)
        import_context['changes'] = import_context['changes'] or assignment_changes

    # apply policy permissions as a minimum, but do not reduce existing permissions
    current_permissions_for_users = object_permissions.get_permissions_for_users(resource_id=object.object_id)
    for user_id, permission in object_data['permissions']['users'].items():
        if permission not in current_permissions_for_users.get(user_id, Permissions.NONE):
            set_user_object_permissions(object.object_id, user_id, permission)

    current_permissions_for_groups = object_permissions.get_permissions_for_groups(resource_id=object.object_id)
    for group_id, permission in object_data['permissions']['groups'].items():
        if permission not in current_permissions_for_groups.get(group_id, Permissions.NONE):
            set_group_object_permissions(object.object_id, group_id, permission)

    current_permissions_for_projects = object_permissions.get_permissions_for_projects(resource_id=object.object_id)
    for project_id, permission in object_data['permissions']['projects'].items():
        if permission not in current_permissions_for_projects.get(project_id, Permissions.NONE):
            set_project_object_permissions(object.object_id, project_id, permission)

    current_permissions_for_all_users = object_permissions.get_permissions_for_all_users(resource_id=object.object_id)
    permission = object_data['permissions']['all_users']
    if permission not in current_permissions_for_all_users:
        set_object_permissions_for_all_users(object.object_id, permission)

    if import_status is not None and import_context['changes']:
        import_status['success'] = True
        import_status['notes'] = all_import_notes
        import_status['object_id'] = object.object_id
        import_status['utc_datetime'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    return object, import_context['changes']


def _add_or_update_conflicting_version(version: ObjectVersionData, import_context: ImportContext) -> None:
    """
    If the federated version does not exist, it will be created. Otherwise it will be updated if changes are detected. The versions are
    added/updated on the federated_objects table.

    :param version: the object version that should be processed
    :param import_context: the internal data used in the import process
    """
    if version['version_component_id'] is not None and import_context['local_object_id'] is not None:
        try:
            existing_version = get_conflicting_federated_object_version(
                import_context['local_object_id'],
                fed_version_id=version['fed_version_id'],
                version_component_id=version['version_component_id']
            )
        except errors.FederatedObjectVersionDoesNotExistError:
            create_conflicting_federated_object(
                import_context['local_object_id'],
                fed_version_id=version['fed_version_id'],
                version_component_id=version['version_component_id'],
                data=version['data'],
                schema=version['schema'],
                action_id=import_context['action_id'],
                utc_datetime=version['utc_datetime'],
                user_id=import_context['user_id'],
                local_parent=None,
                hash_data=version['hash_data'],
                hash_metadata=version['hash_metadata'],
                imported_from_component_id=import_context['component'].id,
            )
            if import_context['user_id'] is not None:
                object_log.import_conflicting_version(
                    user_id=import_context['user_id'],
                    object_id=import_context['local_object_id'],
                    fed_version_id=version['fed_version_id'],
                    component_id=version['version_component_id']
                )
        else:
            if existing_version.user_id != import_context['user_id'] or existing_version.data != version['data'] or existing_version.schema != version['schema'] or existing_version.utc_datetime != version['utc_datetime'] or existing_version.action_id != import_context['action_id']:
                update_conflicting_federated_object_version(
                    object_id=import_context['local_object_id'],
                    fed_version_id=version['fed_version_id'],
                    version_component_id=version['version_component_id'],
                    data=version['data'],
                    schema=version['schema'],
                    action_id=import_context['action_id'],
                    utc_datetime=version['utc_datetime'],
                    user_id=import_context['user_id'],
                    imported_from_component_id=import_context['component'].id,
                )


def _add_federated_conflict_solution(
    object_data: ObjectData,
    version: ObjectVersionData,
    import_context: ImportContext,
    notes: list[str],
) -> None:
    """
    Creates a solution for the conflict specified in the `import_context`. `notes` parameter is used to add an import note
    to the object when a new version is successfully created.

    :param object_data: fully parsed object data
    :param version: the object version that should be imported
    :param import_context: the internal data used in the import process
    :param notes: contains import notes for the object
    :raise errors.FederationObjectImportError: if an internal error occurs
    """
    import_context['changes'] = True
    object = insert_fed_object_version(
        fed_object_id=object_data['fed_object_id'],
        fed_version_id=version['fed_version_id'],
        component_id=object_data['component_id'],
        data=version['data'],
        schema=version['schema'],
        user_id=import_context['user_id'],
        action_id=import_context['action_id'],
        utc_datetime=version['utc_datetime'],
        version_component_id=version['version_component_id'],
        hash_data=version['hash_data'],
        hash_metadata=version['hash_metadata'],
        imported_from_component_id=import_context['component'].id,
        allow_disabled_languages=True,
        get_missing_schema_from_action=False  # if the version contains None for the schema, do not try to load it from the action
    )
    if object is not None:
        if import_context['conflict_details'] is None or import_context['local_object_id'] is None:
            raise errors.FederationObjectImportError()
        _create_or_update_object_version_conflict(
            object_id=import_context['local_object_id'],
            fed_version_id=import_context['conflict_details']['fed_version_id'],
            component_id=import_context['component'].id,
            base_version_id=import_context['conflict_details']['base_version_id'],
            solver_id=import_context['user_id'],
            version_solved_in=object.version_id,
            local_version_id=object.version_id - 1,
            automerged=import_context['conflict_details']['automerged'],
            notes=notes,
        )
        fed_logs.update_object(
            object.id,
            import_context['component'].id,
            version.get('import_notes', []),
            import_context['sharing_user_id'],
            version['fed_version_id']
        )
        object_log.solve_version_conflict(
            user_id=import_context['user_id'],
            object_id=import_context['local_object_id'],
            component_id=import_context['component'].id,
            version_id=import_context['conflict_details']['fed_version_id'],
            solved_in=object.version_id,
            automerged=import_context['conflict_details']['automerged'],
        )

    import_context['current_local_version_id'] += 1
    import_context['next_conflict_solution_version_id'] = None


def _update_federated_conflict_solution(
    object: Object,
    version: ObjectVersionData,
    import_context: ImportContext,
    notes: list[str],
) -> None:
    """
    Updates the current object version conflict specified in the `import_context`. If the import version and the current version
    have the same data but were created by different users, a subversion will be created.

    :param object: the current local object version
    :param version: the object version that should be imported
    :param import_context: the internal data used in the import process
    :param notes: contains import notes for the object
    :raise errors.FederationObjectImportError: if an internal error occurs
    """
    if object.hash_data == version['hash_data']:
        if import_context['conflict_details'] is None or import_context['local_object_id'] is None:
            raise errors.FederationObjectImportError()
        import_context['current_local_version_id'] += 1
        import_context['next_conflict_solution_version_id'] = None
        import_context['conflicting'] = False
        _create_or_update_object_version_conflict(
            object_id=import_context['local_object_id'],
            fed_version_id=import_context['conflict_details']['fed_version_id'],
            component_id=import_context['component'].id,
            base_version_id=import_context['conflict_details']['base_version_id'],
            solver_id=import_context['user_id'],
            version_solved_in=object.version_id,
            local_version_id=object.version_id - 1,
            automerged=import_context['conflict_details']['automerged'],
            notes=notes,
        )

        if version['hash_metadata'] != object.hash_metadata:
            add_subversion(
                object_id=import_context['local_object_id'],
                version_id=object.version_id,
                action_id=object.action_id,
                schema=object.schema,
                data=object.data,
                user_id=import_context['user_id'],
                utc_datetime=version['utc_datetime'],
                version_component_id=version['version_component_id'],
                hash_metadata=version['hash_metadata'],
                imported_from_component_id=import_context['component'].id,
            )

    else:
        if import_context['local_object_id'] is None or version['version_component_id'] is None:
            raise errors.FederationObjectImportError()
        try:
            get_object_version_conflict(object_id=import_context['local_object_id'], fed_version_id=version['fed_version_id'], component_id=version['version_component_id'])
        except errors.ObjectVersionConflictDoesNotExistError:
            create_object_version_conflict(
                object_id=import_context['local_object_id'],
                fed_version_id=version['fed_version_id'],
                component_id=version['version_component_id'],
                base_version_id=import_context['base_version_id']
            )
            notes.append(_("A conflict with version #%(version_id)s occurred.", version_id=version['fed_version_id']))

        fed_logs.create_version_conflict(object.object_id, import_context['component'].id, fed_version_id=version['fed_version_id'])


def _add_new_local_version(
    object_data: ObjectData,
    version: ObjectVersionData,
    import_context: ImportContext,
) -> typing.Optional[Object]:
    """
    Creates a new local object version.

    :param object_data: fully parsed object data
    :param version: the object version that should be imported
    :param import_context: the internal data used in the import process
    :return: the new local object version or none
    """
    object = insert_fed_object_version(
        fed_object_id=object_data['fed_object_id'],
        fed_version_id=version['fed_version_id'],
        component_id=object_data['component_id'],
        data=version['data'],
        schema=version['schema'],
        user_id=import_context['user_id'],
        action_id=import_context['action_id'],
        utc_datetime=version['utc_datetime'],
        version_component_id=version['version_component_id'],
        hash_data=version['hash_data'],
        hash_metadata=version['hash_metadata'],
        imported_from_component_id=import_context['component'].id,
        allow_disabled_languages=True,
        get_missing_schema_from_action=False  # if the version contains None for the schema, do not try to load it from the action
    )
    import_context['changes'] = True
    if object:
        import_context['base_version_id'] = object.version_id
        import_context['current_local_version_id'] += 1
        fed_logs.import_object(object.id, import_context['component'].id, version.get('import_notes', []), import_context['sharing_user_id'], version['fed_version_id'])
        if import_context['user_id'] is not None:
            if version['fed_version_id'] == 0:
                object_log.create_object(
                    user_id=import_context['user_id'],
                    object_id=object.id,
                    utc_datetime=version['utc_datetime'],
                    is_imported=True,
                    imported_from_component_id=import_context['component'].id,
                )
            else:
                object_log.edit_object(
                    user_id=import_context['user_id'],
                    object_id=object.id,
                    version_id=object.version_id,
                    utc_datetime=version['utc_datetime'],
                    is_imported=True,
                    imported_from_component_id=import_context['component'].id,
                )
    return object


def _check_conflicting_version_exists(version: ObjectVersionData, import_context: ImportContext) -> None:
    """
    Checks if the conflicting object version `version` already exists locally. If the object version already exists
    locally stored version gets updated if changes were made. If the object version does not exist locally, it will be
    created.

    :param version: the object version that should be imported
    :param import_context: the internal data used in the import process
    :raise errors.FederationObjectImportError: if an internal error occurs
    """
    if version['version_component_id'] is None or import_context['local_object_id'] is None:
        raise errors.FederationObjectImportError()
    try:
        conflicting_object_version = get_conflicting_federated_object_version(
            object_id=import_context['local_object_id'],
            fed_version_id=version['fed_version_id'],
            version_component_id=version['version_component_id']
        )
    except Exception:
        conflicting_object_version = None

    import_context['conflict_details'] = ConflictDetails(
        fed_version_id=version['fed_version_id'],
        base_version_id=import_context['base_version_id'],
        automerged=False
    )

    if not conflicting_object_version:
        create_conflicting_federated_object(
            object_id=import_context['local_object_id'],
            fed_version_id=version['fed_version_id'],
            version_component_id=version['version_component_id'],
            data=version['data'],
            schema=version['schema'],
            action_id=import_context['action_id'],
            utc_datetime=version['utc_datetime'],
            user_id=import_context['user_id'],
            local_parent=import_context['base_version_id'],
            hash_data=version['hash_data'],
            hash_metadata=version['hash_metadata'],
            imported_from_component_id=import_context['component'].id,
        )
        if import_context['user_id'] is not None:
            object_log.import_conflicting_version(
                user_id=import_context['user_id'],
                object_id=import_context['local_object_id'],
                fed_version_id=version['fed_version_id'],
                component_id=version['version_component_id']
            )

    elif (conflicting_object_version.user_id != import_context['user_id'] or
          conflicting_object_version.data != version['data'] or
          conflicting_object_version.schema != version['schema'] or
          conflicting_object_version.utc_datetime != version['utc_datetime']):
        update_conflicting_federated_object_version(
            object_id=import_context['local_object_id'],
            fed_version_id=conflicting_object_version.fed_version_id,
            version_component_id=version['version_component_id'],
            data=version['data'],
            schema=version['schema'],
            action_id=conflicting_object_version.action_id,
            utc_datetime=version['utc_datetime'],
            user_id=import_context['user_id'],
            imported_from_component_id=import_context['component'].id,
        )


def _find_and_apply_conflict_solution(
    object_data: ObjectData,
    version: ObjectVersionData,
    import_context: ImportContext,
    conflict_status: typing.Dict[str, typing.Any]
) -> None:
    """
    Check if a solution for the current conflict (specified in the `import_context`) already exists in the local database
    or at the federation partner (using the `conflict_status`). If a solution exists, it will be applied.

    In case of two differing conflict solutions, both solutions will be discarded.

    :param object_data: fully parsed object data
    :param version: the object version that should be imported
    :param import_context: the internal data used in the import process
    :param conflict_status: the conflict solutions of the federation partner
    :raise errors.FederationObjectImportError: if an internal error occurs
    """
    if import_context['local_object_id'] is None or import_context['conflict_details'] is None:
        raise errors.FederationObjectImportError()
    try:
        local_solution = get_next_object_version_conflict(
            object_id=import_context['local_object_id'],
            base_version_id=import_context['base_version_id'],
            current_fed_version_id=version['fed_version_id'],
            component_id=import_context['component'].id
        )
    except errors.ObjectVersionConflictDoesNotExistError:
        local_solution = None

    next_version_ids = [
        int(version_id) for version_id in conflict_status.keys()
        if int(version_id) >= version['fed_version_id']
    ]

    imported_conflict_next_version_id = None
    if next_version_ids:
        imported_conflict_next_version_id = sorted(next_version_ids)[0]

    if local_solution is not None and local_solution.version_solved_in is not None:
        if imported_conflict_next_version_id is not None:
            imported_solution_id = conflict_status.get(str(imported_conflict_next_version_id), {}).get('version_solved_in')
            imported_solution_version = _get_specific_version_from_object_data(imported_solution_id, object_data)
            local_solution_version = get_object(import_context['local_object_id'], version_id=local_solution.version_solved_in)

            import_context['conflict_between_solutions'] = (
                imported_solution_version is not None and
                local_solution_version.hash_data != imported_solution_version['hash_data']
            )
        else:
            import_context['conflict_between_solutions'] = object_data['versions'][-1]['fed_version_id'] > local_solution.fed_version_id

        if import_context['conflict_between_solutions']:
            import_context['conflicting'] = True
            import_context['base_version_id'] = local_solution.base_version_id
        else:
            import_context['conflicting'] = False
            import_context['base_version_id'] = local_solution.version_solved_in

        import_context['next_conflict_solution_version_id'] = None
        import_context['current_local_version_id'] = local_solution.version_solved_in
        import_context['skip_until_fed_version_id'] = local_solution.fed_version_id + 1

    elif imported_conflict_next_version_id is not None:
        imported_solution = conflict_status.get(str(imported_conflict_next_version_id))

        if imported_solution is not None:
            import_context['next_conflict_solution_version_id'] = imported_solution.get('version_solved_in')
            import_context['current_local_version_id'] = imported_solution.get('fed_version_id') + 1
            import_context['skip_until_fed_version_id'] = imported_conflict_next_version_id + 1
            import_context['conflict_details']['fed_version_id'] = imported_conflict_next_version_id

            try:
                next_local_version = get_object(object_id=import_context['local_object_id'], version_id=import_context['current_local_version_id'])
            except errors.ObjectVersionDoesNotExistError:
                next_local_version = None

            imported_solution_version = _get_specific_version_from_object_data(import_context['next_conflict_solution_version_id'], object_data)
            if next_local_version is not None and imported_solution_version is not None and next_local_version.hash_data != imported_solution_version['hash_data']:
                import_context['conflict_between_solutions'] = True
                import_context['next_conflict_solution_version_id'] = None
    else:
        import_context['conflicting'] = True


def _get_specific_version_from_object_data(fed_version_id: typing.Optional[int], object_data: ObjectData) -> typing.Optional[ObjectVersionData]:
    """
    Returns the object version data for a specific federated version id (`fed_version_id`).

    :param fed_version_id: the federated version id
    :param object_data: fully parsed object data
    :return: if a version with the specified `fed_version_id` exists, the version data, otherwise None
    """
    if fed_version_id is None:
        return None

    for version in object_data['versions']:
        if version['fed_version_id'] == fed_version_id:
            return version
    return None


def parse_object(
        object_data: typing.Dict[str, typing.Any],
        component: Component
) -> ObjectData:
    fed_object_id = _get_id(object_data.get('object_id'))
    versions = _get_list(object_data.get('versions'), mandatory=True)
    parsed_versions = []
    for version in versions:
        import_notes = []
        fed_version_id = _get_id(version.get('version_id'), mandatory=True, min=0)
        component_uuid = _get_uuid(version.get('version_component_uuid', component.uuid), mandatory=True)
        hash_data = _get_str(version.get('hash_data'))
        hash_metadata = _get_str(version.get('hash_metadata'))
        data: typing.Optional[typing.Dict[str, typing.Any]] = _get_dict(version.get('data'))
        schema: typing.Optional[typing.Dict[str, typing.Any]] = _get_dict(version.get('schema'))
        if data is None or schema is None:
            data = None
            schema = None
        else:
            parse_entry(data, component)
            _parse_schema(schema)
            try:
                if schema is not None:
                    validate_schema(schema, strict=False)
                    if data is not None:
                        validate(data, schema, allow_disabled_languages=True, strict=False)
            except errors.ValidationError as e:
                schema = None
                data = None
                import_notes.append(f'Invalid data or schema in version {fed_version_id} of object #{fed_object_id} @ {component.uuid} ({e})')

        component_id = None
        if component_uuid != flask.current_app.config['FEDERATION_UUID']:
            try:
                component_id = get_component_by_uuid(component_uuid).id
            except errors.ComponentDoesNotExistError:
                component_id = add_component(component_uuid, is_hidden=True).id

        parsed_versions.append(ObjectVersionData(
            fed_version_id=fed_version_id,
            version_component_id=component_id,
            data=data,
            schema=schema,
            user=_parse_user_ref(_get_dict(version.get('user'))),
            utc_datetime=_get_utc_datetime(version.get('utc_datetime'), default=None),
            import_notes=import_notes,
            hash_data=hash_data,
            hash_metadata=hash_metadata
        ))

    component_id = None
    if object_data.get('component_uuid', None) is None:
        component_id = component.id
    elif object_data['component_uuid'] != flask.current_app.config['FEDERATION_UUID']:
        try:
            component_id = get_component_by_uuid(object_data['component_uuid']).id
        except errors.ComponentDoesNotExistError:
            component_id = add_component(object_data['component_uuid'], is_hidden=True).id
    else:
        try:
            get_share(object_id=fed_object_id, component_id=component.id)
        except errors.ShareDoesNotExistError:
            raise errors.InvalidDataExportError(f"Object #{fed_object_id} is not shared with component #{component.id}")

    action_ref = _parse_action_ref(_get_dict(object_data.get('action')))

    if action_ref is None and component_id is None:
        action_ref = _get_action_from_older_version(fed_object_id)

    result = ObjectData(
        fed_object_id=fed_object_id,
        component_id=component_id,
        versions=parsed_versions,
        action=action_ref,
        comments=[],
        files=[],
        object_location_assignments=[],
        permissions=ObjectPermissionsData(
            users={},
            groups={},
            projects={},
            all_users=Permissions.NONE
        ),
        sharing_user=_parse_user_ref(_get_dict(object_data.get('sharing_user')))
    )

    comments = _get_list(object_data.get('comments'))
    if comments is not None:
        for comment in comments:
            if parsed_comment := parse_comment(comment):
                result['comments'].append(parsed_comment)

    files = _get_list(object_data.get('files'))
    if files is not None:
        for file in files:
            try:
                if component_id is None:
                    local_object_id = get_object(object_id=fed_object_id).id
                else:
                    local_object_id = get_fed_object(fed_object_id=fed_object_id, component_id=component_id).id
            except errors.ObjectDoesNotExistError:
                if component_id is None:
                    local_object_id = fed_object_id
                else:
                    local_object_id = None

            if parsed_file := parse_file(file, local_object_id):
                result['files'].append(parsed_file)

    assignments = _get_list(object_data.get('object_location_assignments'))
    if assignments is not None:
        for assignment in assignments:
            if parsed_assignment := parse_object_location_assignment(assignment):
                result['object_location_assignments'].append(parsed_assignment)

    policy = _get_dict(object_data.get('policy'), mandatory=True)

    permissions = _get_permissions(policy.get('permissions'))
    if permissions is not None:
        users = _get_dict(permissions.get('users'))
        if users is not None:
            for user_id, permission in users.items():
                user_id = _get_id(user_id, convert=True)
                try:
                    check_user_exists(user_id)
                except errors.UserDoesNotExistError:
                    continue
                try:
                    result['permissions']['users'][user_id] = Permissions.from_name(permission)
                except ValueError:
                    raise errors.InvalidDataExportError(f'Unknown permission "{permission}"')
        groups = _get_dict(permissions.get('groups'))
        if groups is not None:
            for group_id, permission in groups.items():
                group_id = _get_id(group_id, convert=True)
                try:
                    get_group(group_id)
                except errors.GroupDoesNotExistError:
                    continue
                try:
                    result['permissions']['groups'][group_id] = Permissions.from_name(permission)
                except ValueError:
                    raise errors.InvalidDataExportError(f'Unknown permission "{permission}"')
        projects = _get_dict(permissions.get('projects'))
        if projects is not None:
            for project_id, permission in projects.items():
                project_id = _get_id(project_id, convert=True)
                try:
                    get_project(project_id)
                except errors.ProjectDoesNotExistError:
                    continue
                try:
                    result['permissions']['projects'][project_id] = Permissions.from_name(permission)
                except ValueError:
                    raise errors.InvalidDataExportError(f'Unknown permission "{permission}"')
        all_users = _get_str(permissions.get('all_users'))
        if all_users is not None:
            permission = all_users
            try:
                result['permissions']['all_users'] = Permissions.from_name(permission)
            except ValueError:
                raise errors.InvalidDataExportError(f'Unknown permission "{permission}"')
    return result


def parse_import_object(
        object_data: typing.Dict[str, typing.Any],
        component: Component,
        conflict_status: typing.Optional[typing.Dict[str, typing.Any]] = None,
) -> typing.Tuple[Object, bool]:
    return import_object(parse_object(object_data, component), component, conflict_status=conflict_status)


def shared_object_preprocessor(
        object_id: int,
        policy: typing.Dict[str, typing.Any],
        refs: typing.List[typing.Tuple[str, int]],
        markdown_images: typing.Dict[str, str],
        *,
        sharing_user_id: typing.Optional[int] = None
) -> SharedObjectData:

    object = get_object(object_id)

    result = SharedObjectData(
        object_id=object.fed_object_id if object.fed_object_id and object.component else object_id,
        versions=[],
        component_uuid=object.component.uuid if object.component and object.fed_object_id else flask.current_app.config['FEDERATION_UUID'],
        action=None,
        comments=[],
        object_location_assignments=[],
        files=[],
        policy=policy,
        sharing_user=None
    )
    if sharing_user_id is not None:
        if ('users', sharing_user_id) not in refs:
            refs.append(('users', sharing_user_id))
        sharing_user = get_user(sharing_user_id)
        if sharing_user.fed_id is not None and sharing_user.component is not None:
            result['sharing_user'] = {
                'user_id': sharing_user.fed_id,
                'component_uuid': sharing_user.component.uuid
            }
        else:
            result['sharing_user'] = {
                'user_id': sharing_user.id,
                'component_uuid': flask.current_app.config['FEDERATION_UUID']
            }
    object_versions = get_object_versions(object_id)
    if 'access' in policy:
        if 'action' in policy['access'] and policy['access']['action'] and object.action_id is not None:
            if ('actions', object.action_id) not in refs:
                refs.append(('actions', object.action_id))
            action = get_action(object.action_id)
            if action.component is not None and action.fed_id is not None:
                comp = action.component
                result['action'] = ActionRef(
                    action_id=action.fed_id,
                    component_uuid=comp.uuid
                )
            else:
                result['action'] = ActionRef(
                    action_id=action.id,
                    component_uuid=flask.current_app.config['FEDERATION_UUID']
                )
        if 'comments' in policy['access'] and policy['access']['comments']:
            comments = get_comments_for_object(object_id)
            result['comments'] = []
            for comment in comments:
                if comment.component is None or comment.fed_id is None:
                    res_comment = {
                        'comment_id': comment.id,
                        'component_uuid': flask.current_app.config['FEDERATION_UUID']
                    }
                else:
                    comp = comment.component
                    res_comment = {
                        'comment_id': comment.fed_id,
                        'component_uuid': comp.uuid
                    }
                res_comment['content'] = comment.content
                res_comment['utc_datetime'] = comment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') if comment.utc_datetime is not None else None
                if 'users' in policy['access'] and policy['access']['users'] and comment.user_id is not None:
                    if ('users', comment.user_id) not in refs:
                        refs.append(('users', comment.user_id))
                    user = get_user(comment.user_id)
                    if user.fed_id is not None and user.component is not None:
                        comp = user.component
                        res_comment['user'] = {
                            'user_id': user.fed_id,
                            'component_uuid': comp.uuid
                        }
                    else:
                        res_comment['user'] = {
                            'user_id': comment.user_id,
                            'component_uuid': flask.current_app.config['FEDERATION_UUID']
                        }
                result['comments'].append(SharedCommentData(
                    comment_id=res_comment['comment_id'],
                    component_uuid=res_comment['component_uuid'],
                    user=res_comment.get('user'),
                    content=res_comment['content'],
                    utc_datetime=res_comment['utc_datetime']
                ))
        if 'files' in policy['access'] and policy['access']['files']:
            files = get_files_for_object(object_id)
            result['files'] = []
            for file in files:
                if file.component_id is None:
                    res_file = {
                        'file_id': file.id,
                        'component_uuid': flask.current_app.config['FEDERATION_UUID']
                    }
                else:
                    comp = get_component(file.component_id)
                    res_file = {
                        'file_id': file.fed_id,
                        'component_uuid': comp.uuid
                    }
                res_file['utc_datetime'] = file.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') if file.utc_datetime else None
                if 'users' in policy['access'] and policy['access']['users'] and file.user_id is not None:
                    if ('users', file.user_id) not in refs:
                        refs.append(('users', file.user_id))
                    user = get_user(file.user_id)
                    if user.fed_id is not None and user.component is not None:
                        comp = user.component
                        res_file['user'] = {
                            'user_id': user.fed_id,
                            'component_uuid': comp.uuid
                        }
                    else:
                        res_file['user'] = {
                            'user_id': file.user_id,
                            'component_uuid': flask.current_app.config['FEDERATION_UUID']
                        }
                if file.is_hidden:
                    log_entry = FileLogEntry.query.filter_by(
                        object_id=file.object_id,
                        file_id=file.id,
                        type=FileLogEntryType.HIDE_FILE
                    ).order_by(FileLogEntry.utc_datetime.desc()).first()
                    res_file['hidden'] = {
                        'reason': file.hide_reason,
                        'utc_datetime': log_entry.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') if log_entry is not None else None
                    }
                    if log_entry is not None:
                        if ('users', log_entry.user_id) not in refs:
                            refs.append(('users', log_entry.user_id))
                    if file.user_id:
                        user = get_user(file.user_id)
                        if user.fed_id is not None and user.component is not None:
                            comp = user.component
                            res_file['hidden']['user'] = {
                                'user_id': user.fed_id,
                                'component_uuid': comp.uuid
                            }
                        else:
                            res_file['hidden']['user'] = {
                                'user_id': file.user_id,
                                'component_uuid': flask.current_app.config['FEDERATION_UUID']
                            }
                    else:
                        res_file['hidden']['user'] = None
                else:
                    res_file['data'] = file.data
                    if file.storage == 'database':
                        res_file['data']['storage'] = 'federation'

                result['files'].append(SharedFileData(
                    file_id=res_file['file_id'],
                    component_uuid=res_file['component_uuid'],
                    user=res_file.get('user'),
                    data=res_file.get('data'),
                    utc_datetime=res_file['utc_datetime'],
                    hidden=res_file.get('hidden')
                ))
        if 'object_location_assignments' in policy['access'] and policy['access']['object_location_assignments']:
            olas = get_object_location_assignments(object_id)
            for ola in olas:
                if ola.location_id is not None and ('locations', ola.location_id) not in refs:
                    refs.append(('locations', ola.location_id))
                if ola.user_id is not None and ('users', ola.user_id) not in refs:
                    refs.append(('users', ola.user_id))
                if ola.responsible_user_id is not None and ('users', ola.responsible_user_id) not in refs:
                    refs.append(('users', ola.responsible_user_id))
                if ola.location_id is not None:
                    location = get_location(ola.location_id)
                    if location.component is not None and location.fed_id is not None:
                        comp = location.component
                        location_ref = LocationRef(
                            location_id=location.fed_id,
                            component_uuid=comp.uuid
                        )
                    else:
                        location_ref = LocationRef(
                            location_id=location.id,
                            component_uuid=flask.current_app.config['FEDERATION_UUID']
                        )
                else:
                    location_ref = None
                if ola.responsible_user_id is not None:
                    responsible_user = get_user(ola.responsible_user_id)
                    if responsible_user.component is not None and responsible_user.fed_id is not None:
                        comp = responsible_user.component
                        responsible_user_ref = UserRef(
                            user_id=responsible_user.fed_id,
                            component_uuid=comp.uuid
                        )
                    else:
                        responsible_user_ref = UserRef(
                            user_id=responsible_user.id,
                            component_uuid=flask.current_app.config['FEDERATION_UUID']
                        )
                else:
                    responsible_user_ref = None
                if ola.user_id is not None:
                    ola_user = get_user(ola.user_id)
                    if ola_user.component is not None and ola_user.fed_id is not None:
                        comp = ola_user.component
                        c_user = UserRef(
                            user_id=ola_user.fed_id,
                            component_uuid=comp.uuid
                        )
                    else:
                        c_user = UserRef(
                            user_id=ola_user.id,
                            component_uuid=flask.current_app.config['FEDERATION_UUID']
                        )
                else:
                    c_user = None
                if ola.component_id is None:
                    component_uuid = flask.current_app.config['FEDERATION_UUID']
                else:
                    comp = get_component(ola.component_id)
                    component_uuid = comp.uuid
                result['object_location_assignments'].append(SharedObjectLocationAssignmentData(
                    id=ola.id if component_uuid == flask.current_app.config['FEDERATION_UUID'] or ola.fed_id is None else ola.fed_id,
                    component_uuid=component_uuid,
                    location=location_ref,
                    responsible_user=responsible_user_ref,
                    user=c_user,
                    description=ola.description,
                    utc_datetime=ola.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') if ola.utc_datetime else None,
                    confirmed=ola.confirmed,
                    declined=ola.declined,
                ))
    for version in object_versions:
        version_data: typing.Optional[typing.Dict[str, typing.Any]] = None
        version_schema: typing.Optional[typing.Dict[str, typing.Any]] = None
        version_user: typing.Optional[UserRef] = None
        if policy.get('access', {'data': True}).get('data', True):
            if version.data is not None:
                version_data = version.data.copy()
                entry_preprocessor(version_data, refs, markdown_images, object_id)
            if version.schema is not None:
                version_schema = version.schema.copy()
                schema_entry_preprocessor(version_schema, refs)
        if policy.get('access', {}).get('users', False) and version.user_id:
            if ('users', version.user_id) not in refs:
                refs.append(('users', version.user_id))
            user = get_user(version.user_id)
            if user.component is not None and user.fed_id is not None:
                comp = user.component
                version_user = UserRef(
                    user_id=user.fed_id,
                    component_uuid=comp.uuid
                )
            else:
                version_user = UserRef(
                    user_id=user.id,
                    component_uuid=flask.current_app.config['FEDERATION_UUID']
                )
        if 'modification' in policy:
            modification = policy['modification']
            if 'insert' in modification:
                if 'data' in modification['insert'] and version_data is not None:
                    for key in modification['insert']['data']:
                        version_data[key] = modification['insert']['data'][key]
                if 'schema' in modification['insert'] and version_schema is not None:
                    for key in modification['insert']['schema']:
                        version_schema['properties'][key] = modification['insert']['schema'][key]

            if 'update' in modification:
                if 'data' in modification['update'] and version_data is not None:
                    for key in modification['update']['data']:
                        if key not in version_data:
                            pass
                        for k in modification['update']['data'][key]:
                            version_data[key][k] = modification['update']['data'][key][k]
                if 'schema' in modification['update'] and version_schema is not None:
                    for key in modification['update']['schema']:
                        if key not in version_schema['properties']:
                            pass
                        version_schema['properties'][key] = {
                            key: value
                            for key, value in modification['update']['schema'][key].items()
                        }
        result['versions'].append(SharedObjectVersionData(
            version_id=version.version_id,
            version_component_uuid=version.version_component.uuid if version.version_component else flask.current_app.config['FEDERATION_UUID'],
            schema=version_schema,
            data=version_data,
            user=version_user,
            utc_datetime=version.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') if version.utc_datetime else None,
            hash_data=version.hash_data,
            hash_metadata=version.hash_metadata
        ))
    return result


def entry_preprocessor(
        data: typing.Any,
        refs: typing.List[typing.Tuple[str, int]],
        markdown_images: typing.Dict[str, str],
        object_id: typing.Optional[int] = None,
) -> None:
    if type(data) is list:
        for entry in data:
            entry_preprocessor(entry, refs, markdown_images, object_id)
    elif type(data) is dict:
        if '_type' not in data.keys():
            for key in data:
                entry_preprocessor(data[key], refs, markdown_images, object_id)
        else:
            if data['_type'] in ['sample', 'object_reference', 'measurement']:
                if (data.get('component_uuid') is None or data.get('component_uuid') == flask.current_app.config['FEDERATION_UUID']) and 'eln_source_url' not in data:
                    o = get_object(data['object_id'])
                    if o.component_id is not None:
                        c = get_component(o.component_id)
                        data['object_id'] = o.fed_object_id
                        data['component_uuid'] = c.uuid
                    else:
                        data['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
            if data['_type'] == 'user':
                if (data.get('component_uuid') is None or data.get('component_uuid') == flask.current_app.config['FEDERATION_UUID']) and 'eln_source_url' not in data:
                    try:
                        u = get_user(data.get('user_id'))  # type: ignore
                        if u.component_id is not None:
                            c = get_component(u.component_id)
                            data['user_id'] = u.fed_id
                            data['component_uuid'] = c.uuid
                        else:
                            data['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
                    except errors.UserDoesNotExistError:
                        pass
            if data['_type'] == 'file':
                if (data.get('component_uuid') is None or data.get('component_uuid') == flask.current_app.config['FEDERATION_UUID']) and 'eln_source_url' not in data:
                    file_id = data.get('file_id')
                    if object_id is None:
                        data['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
                    elif file_id is not None:
                        file = get_file(file_id, object_id)
                        if file.component_id is None:
                            data['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
                        else:
                            c = get_component(file.component_id)
                            data['file_id'] = file.fed_id
                            data['component_uuid'] = c.uuid

            if data['_type'] == 'text' and data.get('is_markdown'):
                if isinstance(data.get('text'), str):
                    markdown_as_html = markdown_to_html.markdown_to_safe_html(data['text'])
                    for file_name in find_referenced_markdown_images(markdown_as_html):
                        pure_filename = file_name
                        component_id = None
                        if '/' not in file_name:
                            data['text'] = data['text'].replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                        else:
                            component_uuid, pure_filename = file_name.split('/')
                            if component_uuid != flask.current_app.config['FEDERATION_UUID']:
                                component_id = get_component_by_uuid(component_uuid=component_uuid).id

                        markdown_image_b = get_markdown_image(pure_filename, None, component_id=component_id)
                        if markdown_image_b is not None and file_name not in markdown_images:
                            markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')
                elif isinstance(data.get('text'), dict):
                    for lang in data['text'].keys():
                        markdown_as_html = markdown_to_html.markdown_to_safe_html(data['text'][lang])
                        for file_name in find_referenced_markdown_images(markdown_as_html):
                            pure_filename = file_name
                            component_id = None
                            if '/' not in file_name:
                                data['text'][lang] = data['text'][lang].replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                            else:
                                component_uuid, pure_filename = file_name.split('/')
                                if component_uuid != flask.current_app.config['FEDERATION_UUID']:
                                    component_id = get_component_by_uuid(component_uuid=component_uuid).id

                            markdown_image_b = get_markdown_image(pure_filename, None, component_id=component_id)
                            if markdown_image_b is not None and file_name not in markdown_images:
                                markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')


def parse_entry(
        entry_data: typing.Any,
        component: Component
) -> None:
    if type(entry_data) is list:
        for entry in entry_data:
            parse_entry(entry, component)
    elif type(entry_data) is dict:
        if '_type' not in entry_data.keys():
            for key in entry_data:
                parse_entry(entry_data[key], component)
        else:
            if entry_data.get('_type') == 'user':
                user_id = _get_id(entry_data.get('user_id'), mandatory=False)
                if user_id is None:
                    return
                if 'component_uuid' not in entry_data and 'eln_source_url' in entry_data:
                    try:
                        validate_eln_urls(entry_data, [])
                    except errors.ValidationError:
                        raise errors.InvalidDataExportError('Invalid .eln file URLs')
                elif _get_uuid(entry_data.get('component_uuid')) == flask.current_app.config['FEDERATION_UUID']:
                    try:
                        user = get_user(user_id)
                    except errors.UserDoesNotExistError:
                        raise errors.InvalidDataExportError(f'Local user #{user_id} does not exist')
                    del entry_data['component_uuid']
                    entry_data['user_id'] = user.id
                else:
                    try:
                        data_component = get_component_by_uuid(_get_uuid(entry_data.get('component_uuid')))
                        try:
                            user = get_user(_get_id(entry_data.get('user_id')), data_component.id)
                            del entry_data['component_uuid']
                            entry_data['user_id'] = user.id
                        except errors.UserDoesNotExistError:
                            pass
                    except errors.ComponentDoesNotExistError:
                        pass

            if entry_data.get('_type') in ('sample', 'object_reference', 'measurement'):
                data_obj_id = _get_id(entry_data.get('object_id'), mandatory=False)
                if data_obj_id is None:
                    return
                if 'component_uuid' not in entry_data and 'eln_source_url' in entry_data:
                    try:
                        validate_eln_urls(entry_data, [])
                    except errors.ValidationError:
                        raise errors.InvalidDataExportError('Invalid .eln file URLs')
                elif _get_uuid(entry_data.get('component_uuid')) == flask.current_app.config['FEDERATION_UUID']:
                    try:
                        obj = get_object(data_obj_id)
                    except errors.ObjectDoesNotExistError:
                        raise errors.InvalidDataExportError(f'Local object #{data_obj_id} does not exist')
                    del entry_data['component_uuid']
                    entry_data['object_id'] = obj.id
                else:
                    try:
                        data_component = get_component_by_uuid(_get_uuid(entry_data.get('component_uuid')))
                        obj = get_fed_object(data_obj_id, data_component.id)
                        if obj is not None:
                            del entry_data['component_uuid']
                            entry_data['object_id'] = obj.object_id
                    except errors.ComponentDoesNotExistError:
                        pass
                    except errors.ObjectDoesNotExistError:
                        pass
            all_lang_codes = languages.get_language_codes()

            if entry_data.get('_type') == 'text':
                text_data = entry_data.get('text')
                if isinstance(text_data, dict):
                    for lang_code in list(text_data.keys()):
                        if lang_code not in all_lang_codes:
                            del entry_data['text'][lang_code]


def _get_action_from_older_version(object_id: int) -> typing.Optional[ActionRef]:
    try:
        object = get_object(object_id)
    except (errors.ObjectDoesNotExistError, errors.ObjectVersionDoesNotExistError):
        object = None

    if object is not None and object.action_id is not None:
        return ActionRef(
            action_id=object.action_id,
            component_uuid=flask.current_app.config['FEDERATION_UUID']
        )
    return None


def _create_or_update_object_version_conflict(
    object_id: int,
    fed_version_id: int,
    component_id: int,
    base_version_id: int,
    version_solved_in: int,
    local_version_id: int,
    automerged: bool,
    solver_id: typing.Optional[int],
    notes: list[str],
) -> None:
    try:
        conflict = get_object_version_conflict(object_id, fed_version_id=fed_version_id, component_id=component_id)
    except errors.ObjectVersionConflictDoesNotExistError:
        create_object_version_conflict(
            object_id=object_id,
            fed_version_id=fed_version_id,
            component_id=component_id,
            base_version_id=base_version_id,
            version_solved_in=version_solved_in,
            local_version_id=local_version_id,
            automerged=automerged,
            solver_id=solver_id,
        )
        notes.append(_("A conflict with version #%(version_id)s was solved.", version_id=fed_version_id))
    else:
        if conflict.local_version_id is not None:
            notes.append(_("A conflict with version #%(version_id)s was solved.", version_id=fed_version_id))
        update_object_version_conflict(
            object_id=object_id,
            fed_version_id=fed_version_id,
            component_id=component_id,
            base_version_id=base_version_id,
            version_solved_in=version_solved_in,
            local_version_id=local_version_id,
            automerged=automerged,
            solver_id=solver_id,
        )
