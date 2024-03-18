import base64
import datetime
import typing

import flask

from .utils import _get_id, _get_uuid, _get_str, _get_dict, _get_list, _get_utc_datetime, _get_permissions
from .users import _parse_user_ref, _get_or_create_user_id, UserRef
from .actions import _parse_action_ref, _get_or_create_action_id, schema_entry_preprocessor, _parse_schema, ActionRef
from .comments import import_comment, parse_comment, CommentData
from .files import import_file, parse_file, FileData
from .object_location_assignments import import_object_location_assignment, parse_object_location_assignment, ObjectLocationAssignmentData
from .locations import LocationRef
from ..files import get_files_for_object
from ..markdown_images import find_referenced_markdown_images, get_markdown_image
from ..object_permissions import set_user_object_permissions, set_group_object_permissions, set_project_object_permissions, set_object_permissions_for_all_users, object_permissions
from ..schemas import validate_schema, validate
from ..schemas.validate import validate_eln_urls
from ..actions import get_action
from ..comments import get_comments_for_object
from ..components import get_component_by_uuid, get_component, Component
from ..groups import get_group
from ..locations import get_location, get_object_location_assignments
from ..objects import get_fed_object, get_object, update_object_version, insert_fed_object_version, get_object_versions
from ..object_log import create_object, edit_object
from ..projects import get_project
from ..users import get_user, check_user_exists
from .. import errors, fed_logs, languages, markdown_to_html
from ...models import Permissions, Object
from ...models.file_log import FileLogEntry, FileLogEntryType


class ObjectVersionData(typing.TypedDict):
    fed_version_id: int
    user: typing.Optional[UserRef]
    data: typing.Optional[typing.Dict[str, typing.Any]]
    schema: typing.Optional[typing.Dict[str, typing.Any]]
    utc_datetime: typing.Optional[datetime.datetime]
    import_notes: typing.List[str]


class ObjectPermissionsData(typing.TypedDict):
    users: typing.Dict[int, Permissions]
    groups: typing.Dict[int, Permissions]
    projects: typing.Dict[int, Permissions]
    all_users: Permissions


class ObjectData(typing.TypedDict):
    fed_object_id: int
    component_id: int
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
    user: typing.Optional[UserRef]
    data: typing.Optional[typing.Dict[str, typing.Any]]
    schema: typing.Optional[typing.Dict[str, typing.Any]]
    utc_datetime: typing.Optional[str]


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


def import_object(
        object_data: ObjectData,
        component: Component,
        *,
        import_status: typing.Optional[typing.Dict[str, typing.Any]] = None
) -> Object:
    action_id = _get_or_create_action_id(object_data['action'])
    object = None
    all_import_notes = []
    did_perform_import = False
    for version in object_data['versions']:
        try:
            object = get_fed_object(object_data['fed_object_id'], component.id, version['fed_version_id'])
        except errors.ObjectDoesNotExistError:
            object = None
        except errors.ObjectVersionDoesNotExistError:
            object = None

        user_id = _get_or_create_user_id(version['user'])
        sharing_user_id = _get_or_create_user_id(object_data.get('sharing_user'))

        if object is None:
            object = insert_fed_object_version(
                fed_object_id=object_data['fed_object_id'],
                fed_version_id=version['fed_version_id'],
                component_id=component.id,
                data=version['data'],
                schema=version['schema'],
                user_id=user_id,
                action_id=action_id,
                utc_datetime=version['utc_datetime'],
                allow_disabled_languages=True,
                get_missing_schema_from_action=False  # if the version contains None for the schema, do not try to load it from the action
            )
            if object:
                fed_logs.import_object(object.id, component.id, version.get('import_notes', []), sharing_user_id, version['fed_version_id'])
                if user_id is not None:
                    if version['fed_version_id'] == 0:
                        create_object(
                            user_id=user_id,
                            object_id=object.id,
                            utc_datetime=version['utc_datetime'],
                            is_imported=True
                        )
                    else:
                        edit_object(
                            user_id=user_id,
                            object_id=object.id,
                            version_id=object.version_id,
                            utc_datetime=version['utc_datetime'],
                            is_imported=True
                        )
                did_perform_import = True
        elif object.schema != version['schema'] or object.data != version['data'] or object.user_id != user_id or object.action_id != action_id or object.utc_datetime != version['utc_datetime']:
            object = update_object_version(
                object_id=object.object_id,
                version_id=object.version_id,
                data=version['data'],
                schema=version['schema'],
                user_id=user_id,
                action_id=action_id,
                utc_datetime=version['utc_datetime'],
                allow_disabled_languages=True,
                get_missing_schema_from_action=False  # if the version contains None for the schema, do not try to load it from the action
            )
            fed_logs.update_object(object.id, component.id, version.get('import_notes', []), sharing_user_id, version['fed_version_id'])
            did_perform_import = True
        all_import_notes.extend(version.get('import_notes', []))
    if object is None:
        object = get_fed_object(
            fed_object_id=object_data['fed_object_id'],
            component_id=object_data['component_id']
        )

    for comment_data in object_data['comments']:
        import_comment(comment_data, object, component)

    for file_data in object_data['files']:
        import_file(file_data, object, component)

    for assignment_data in object_data['object_location_assignments']:
        import_object_location_assignment(assignment_data, object, component)

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

    if import_status is not None and did_perform_import:
        import_status['success'] = True
        import_status['notes'] = all_import_notes
        import_status['object_id'] = object.object_id
        import_status['utc_datetime'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    return object


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
        data: typing.Optional[typing.Dict[str, typing.Any]] = _get_dict(version.get('data'))
        schema: typing.Optional[typing.Dict[str, typing.Any]] = _get_dict(version.get('schema'))
        if schema is None or schema is None:
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
        parsed_versions.append(ObjectVersionData(
            fed_version_id=fed_version_id,
            data=data,
            schema=schema,
            user=_parse_user_ref(_get_dict(version.get('user'))),
            utc_datetime=_get_utc_datetime(version.get('utc_datetime'), default=None),
            import_notes=import_notes
        ))

    result = ObjectData(
        fed_object_id=fed_object_id,
        component_id=component.id,
        versions=parsed_versions,
        action=_parse_action_ref(_get_dict(object_data.get('action'))),
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
            result['comments'].append(parse_comment(comment))

    files = _get_list(object_data.get('files'))
    if files is not None:
        for file in files:
            result['files'].append(parse_file(file))

    assignments = _get_list(object_data.get('object_location_assignments'))
    if assignments is not None:
        for assignment in assignments:
            result['object_location_assignments'].append(parse_object_location_assignment(assignment))

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
        component: Component
) -> Object:
    return import_object(parse_object(object_data, component), component)


def shared_object_preprocessor(
        object_id: int,
        policy: typing.Dict[str, typing.Any],
        refs: typing.List[typing.Tuple[str, int]],
        markdown_images: typing.Dict[str, str],
        *,
        sharing_user_id: typing.Optional[int] = None
) -> SharedObjectData:
    result = SharedObjectData(
        object_id=object_id,
        versions=[],
        component_uuid=flask.current_app.config['FEDERATION_UUID'],
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
    object = get_object(object_id)
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
                    id=ola.id,
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
                entry_preprocessor(version_data, refs, markdown_images)
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
            schema=version_schema,
            data=version_data,
            user=version_user,
            utc_datetime=version.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') if version.utc_datetime else None
        ))
    return result


def entry_preprocessor(
        data: typing.Any,
        refs: typing.List[typing.Tuple[str, int]],
        markdown_images: typing.Dict[str, str]
) -> None:
    if type(data) is list:
        for entry in data:
            entry_preprocessor(entry, refs, markdown_images)
    elif type(data) is dict:
        if '_type' not in data.keys():
            for key in data:
                entry_preprocessor(data[key], refs, markdown_images)
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
                if data.get('component_uuid') is None:
                    data['component_uuid'] = flask.current_app.config['FEDERATION_UUID']

            if data['_type'] == 'text' and data.get('is_markdown'):
                if isinstance(data.get('text'), str):
                    markdown_as_html = markdown_to_html.markdown_to_safe_html(data['text'])
                    for file_name in find_referenced_markdown_images(markdown_as_html):
                        markdown_image_b = get_markdown_image(file_name, None)
                        data['text'] = data['text'].replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                        if markdown_image_b is not None and file_name not in markdown_images:
                            markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')
                elif isinstance(data.get('text'), dict):
                    for lang in data['text'].keys():
                        markdown_as_html = markdown_to_html.markdown_to_safe_html(data['text'][lang])
                        for file_name in find_referenced_markdown_images(markdown_as_html):
                            markdown_image_b = get_markdown_image(file_name, None)
                            data['text'][lang] = data['text'][lang].replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
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
