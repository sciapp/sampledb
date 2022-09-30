import base64

import flask

from .utils import _get_id, _get_uuid, _get_str, _get_dict, _get_list, _get_utc_datetime, _get_permissions
from .users import _parse_user_ref, _get_or_create_user_id
from .actions import _parse_action_ref, _get_or_create_action_id, schema_entry_preprocessor, _parse_schema
from .comments import import_comment, parse_comment
from .files import import_file, parse_file
from .object_location_assignments import import_object_location_assignment, parse_object_location_assignment
from ..files import get_files_for_object
from ..markdown_images import find_referenced_markdown_images, get_markdown_image
from ..object_permissions import set_user_object_permissions, set_group_object_permissions, set_project_object_permissions, set_object_permissions_for_all_users, object_permissions
from ..schemas import validate_schema, validate
from ..actions import get_action
from ..comments import get_comments_for_object
from ..components import get_component_by_uuid, get_component
from ..groups import get_group
from ..locations import get_location, get_object_location_assignments
from ..objects import get_fed_object, get_object, update_object_version, insert_fed_object_version, get_object_versions
from ..projects import get_project
from ..users import get_user
from .. import errors, fed_logs, languages, markdown_to_html
from ...models import Permissions
from ...models.file_log import FileLogEntry, FileLogEntryType


def import_object(object_data, component):
    action_id = _get_or_create_action_id(object_data['action'])
    for version in object_data['versions']:
        try:
            object = get_fed_object(object_data['fed_object_id'], component.id, version['fed_version_id'])
        except errors.ObjectDoesNotExistError:
            object = None
        except errors.ObjectVersionDoesNotExistError:
            object = None

        user_id = _get_or_create_user_id(version['user'])

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
                allow_disabled_languages=True
            )
            fed_logs.import_object(object.id, component.id)
        elif object.schema != version['schema'] or object.data != version['data'] or object.user_id != user_id or object.action_id != action_id or object.utc_datetime != version['utc_datetime']:
            object = update_object_version(
                object_id=object.object_id,
                version_id=object.version_id,
                data=version['data'],
                schema=version['schema'],
                user_id=user_id,
                action_id=action_id,
                utc_datetime=version['utc_datetime'],
                allow_disabled_languages=True
            )
            fed_logs.update_object(object.id, component.id)

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

    return object


def parse_object(object_data, component):
    fed_object_id = _get_id(object_data.get('object_id'))
    versions = _get_list(object_data.get('versions'), mandatory=True)
    parsed_versions = []
    for version in versions:
        fed_version_id = _get_id(version.get('version_id'), mandatory=True, min=0)
        data = _get_dict(version.get('data'))
        if data is not None:
            parse_entry(data, component)
        schema = _get_dict(version.get('schema'))
        _parse_schema(schema)
        try:
            if schema is not None:
                validate_schema(schema, strict=True)
                if data is not None:
                    validate(data, schema, allow_disabled_languages=True, strict=False)
        except errors.ValidationError:
            raise errors.InvalidDataExportError('Invalid data or schema in version {} of object #{} @ {}'.format(fed_version_id, fed_object_id, component.uuid))
        parsed_versions.append({
            'fed_version_id': fed_version_id,
            'data': data,
            'schema': schema,
            'user': _parse_user_ref(_get_dict(version.get('user'))),
            'utc_datetime': _get_utc_datetime(version.get('utc_datetime'), default=None),
        })

    result = {
        'fed_object_id': fed_object_id,
        'component_id': component.id,
        'versions': parsed_versions,
        'action': _parse_action_ref(_get_dict(object_data.get('action'))),
        'comments': [],
        'files': [],
        'object_location_assignments': [],
        'permissions': {'users': {}, 'groups': {}, 'projects': {}, 'all_users': Permissions.NONE}
    }

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
                    get_user(user_id)
                except errors.UserDoesNotExistError:
                    continue
                try:
                    result['permissions']['users'][user_id] = Permissions.from_name(permission)
                except ValueError:
                    raise errors.InvalidDataExportError('Unknown permission "{}"'.format(permission))
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
                    raise errors.InvalidDataExportError('Unknown permission "{}"'.format(permission))
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
                    raise errors.InvalidDataExportError('Unknown permission "{}"'.format(permission))
        all_users = _get_str(permissions.get('all_users'))
        if all_users is not None:
            permission = all_users
            try:
                result['permissions']['all_users'] = Permissions.from_name(permission)
            except ValueError:
                raise errors.InvalidDataExportError('Unknown permission "{}"'.format(permission))
    return result


def parse_import_object(object_data, component):
    return import_object(parse_object(object_data, component), component)


def shared_object_preprocessor(object_id, policy, refs, markdown_images):
    result = {
        'object_id': object_id,
        'versions': [],
        'component_uuid': flask.current_app.config['FEDERATION_UUID'],
        'action': None,
        'comments': [], 'object_location_assignments': [], 'files': [],
        'policy': policy
    }
    object = get_object(object_id)
    object_versions = get_object_versions(object_id)
    if 'access' in policy:
        if 'action' in policy['access'] and policy['access']['action']:
            if ('actions', object.action_id) not in refs:
                refs.append(('actions', object.action_id))
            action = get_action(object.action_id)
            if action.component_id is not None:
                comp = action.component
                result['action'] = {
                    'action_id': action.fed_id,
                    'component_uuid': comp.uuid
                }
            else:
                result['action'] = {
                    'action_id': action.id,
                    'component_uuid': flask.current_app.config['FEDERATION_UUID']
                }
        if 'comments' in policy['access'] and policy['access']['comments']:
            comments = get_comments_for_object(object_id)
            result['comments'] = []
            for comment in comments:
                if comment.component_id is None:
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
                res_comment['utc_datetime'] = comment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                if 'users' in policy['access'] and policy['access']['users']:
                    if ('users', comment.user_id) not in refs:
                        refs.append(('users', comment.user_id))
                    user = get_user(comment.user_id)
                    if user.fed_id is not None:
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
                result['comments'].append(res_comment)
        if 'files' in policy['access'] and policy['access']['files']:
            files = get_files_for_object(object_id)
            result['files'] = []
            for file in files:
                if file.storage != 'url':
                    continue
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
                res_file['utc_datetime'] = file.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                if 'users' in policy['access'] and policy['access']['users']:
                    if ('users', file.user_id) not in refs:
                        refs.append(('users', file.user_id))
                    user = get_user(file.user_id)
                    if user.fed_id is not None:
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
                        'utc_datetime': log_entry.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
                    }
                    if ('users', log_entry.user_id) not in refs:
                        refs.append(('users', log_entry.user_id))
                    user = get_user(file.user_id)
                    if user.fed_id is not None:
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
                    res_file['data'] = file.data
                result['files'].append(res_file)
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
                    if location.component is not None:
                        comp = location.component
                        loc = {
                            'location_id': location.fed_id,
                            'component_uuid': comp.uuid
                        }
                    else:
                        loc = {
                            'location_id': location.id,
                            'component_uuid': flask.current_app.config['FEDERATION_UUID']
                        }
                else:
                    loc = None
                if ola.responsible_user_id is not None:
                    responsible_user = get_user(ola.responsible_user_id)
                    if responsible_user.component_id is not None:
                        comp = responsible_user.component
                        r_user = {
                            'user_id': responsible_user.fed_id,
                            'component_uuid': comp.uuid
                        }
                    else:
                        r_user = {
                            'user_id': responsible_user.id,
                            'component_uuid': flask.current_app.config['FEDERATION_UUID']
                        }
                else:
                    r_user = None
                ola_user = get_user(ola.user_id)
                if ola_user.component_id is not None:
                    comp = ola_user.component
                    c_user = {
                        'user_id': ola_user.fed_id,
                        'component_uuid': comp.uuid
                    }
                else:
                    c_user = {
                        'user_id': ola_user.id,
                        'component_uuid': flask.current_app.config['FEDERATION_UUID']
                    }
                if ola.component_id is None:
                    component_uuid = flask.current_app.config['FEDERATION_UUID']
                else:
                    comp = get_component(ola.component_id)
                    component_uuid = comp.uuid
                result['object_location_assignments'].append({
                    'id': ola.id,
                    'component_uuid': component_uuid,
                    'location': loc,
                    'responsible_user': r_user,
                    'user': c_user,
                    'description': ola.description,
                    'utc_datetime': ola.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'confirmed': ola.confirmed,
                })
    for version in object_versions:
        result['versions'].append({
            'version_id': version.version_id, 'schema': None, 'data': None, 'user': None,
            'utc_datetime': version.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
        })
        if 'access' in policy:
            if 'data' not in policy['access'] or ('data' in policy['access'] and policy['access']['data']):
                result['versions'][-1]['data'] = version.data.copy()
                result['versions'][-1]['schema'] = version.schema.copy()
                entry_preprocessor(result['versions'][-1]['data'], refs, markdown_images)
                schema_entry_preprocessor(result['versions'][-1]['schema'], refs)
            if 'users' in policy['access'] and policy['access']['users']:
                if ('users', version.user_id) not in refs:
                    refs.append(('users', version.user_id))
                user = get_user(version.user_id)
                if user.component_id is not None:
                    comp = user.component
                    result['versions'][-1]['user'] = {
                        'user_id': user.fed_id,
                        'component_uuid': comp.uuid
                    }
                else:
                    result['versions'][-1]['user'] = {
                        'user_id': user.id,
                        'component_uuid': flask.current_app.config['FEDERATION_UUID']
                    }
        else:
            result['versions'][-1]['data'] = object.data.copy()
            result['versions'][-1]['schema'] = object.schema.copy()
            entry_preprocessor(result['versions'][-1]['data'], refs, markdown_images)
            schema_entry_preprocessor(result['versions'][-1]['schema'], refs)
        if 'modification' in policy:
            modification = policy['modification']
            if 'insert' in modification:
                if 'data' in modification['insert']:
                    for key in modification['insert']['data']:
                        result['versions'][-1]['data'][key] = modification['insert']['data'][key]
                if 'schema' in modification['insert']:
                    for key in modification['insert']['schema']:
                        result['versions'][-1]['schema']['properties'][key] = modification['insert']['schema'][key]

            if 'update' in modification:
                if 'data' in modification['update']:
                    for key in modification['update']['data']:
                        if key not in result['versions'][-1]['data']:
                            pass
                        for k in modification['update']['data'][key]:
                            result['versions'][-1]['data'][key][k] = modification['update']['data'][key][k]
                if 'schema' in modification['update']:
                    for key in modification['update']['schema']:
                        if key not in result['versions'][-1]['schema']['properties']:
                            pass
                        result['versions'][-1]['schema']['properties'][key] = {}
                        for k in modification['update']['schema'][key]:
                            result['versions'][-1]['schema']['properties'][key][k] = modification['update']['schema'][key][k]
    return result


def entry_preprocessor(data, refs, markdown_images):
    if type(data) == list:
        for entry in data:
            entry_preprocessor(entry, refs, markdown_images)
    elif type(data) == dict:
        if '_type' not in data.keys():
            for key in data:
                entry_preprocessor(data[key], refs, markdown_images)
        else:
            if data['_type'] in ['sample', 'object_reference', 'measurement']:
                if data.get('component_uuid') is None or data.get('component_uuid') == flask.current_app.config['FEDERATION_UUID']:
                    o = get_object(data['object_id'])
                    if o.component_id is not None:
                        c = get_component(o.component_id)
                        data['object_id'] = o.fed_object_id
                        data['component_uuid'] = c.uuid
                    else:
                        data['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
            if data['_type'] == 'user':
                if data.get('component_uuid') is None or data.get('component_uuid') == flask.current_app.config['FEDERATION_UUID']:
                    try:
                        u = get_user(data.get('user_id'))
                        if u.component_id is not None:
                            c = get_component(u.component_id)
                            data['user_id'] = u.fed_id
                            data['component_uuid'] = c.uuid
                        else:
                            data['component_uuid'] = flask.current_app.config['FEDERATION_UUID']
                    except errors.UserDoesNotExistError:
                        pass

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


def parse_entry(entry_data, component):
    if type(entry_data) == list:
        for entry in entry_data:
            parse_entry(entry, component)
    elif type(entry_data) == dict:
        if '_type' not in entry_data.keys():
            for key in entry_data:
                parse_entry(entry_data[key], component)
        else:
            if entry_data.get('_type') == 'user':
                user_id = _get_id(entry_data.get('user_id'), mandatory=False)
                if user_id is None:
                    return
                data_component_uuid = _get_uuid(entry_data.get('component_uuid'))
                if data_component_uuid == flask.current_app.config['FEDERATION_UUID']:
                    try:
                        user = get_user(user_id)
                    except errors.UserDoesNotExistError:
                        raise errors.InvalidDataExportError('Local user #{} does not exist'.format(user_id))
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
                data_component_uuid = _get_uuid(entry_data.get('component_uuid'), mandatory=False)
                if data_component_uuid == flask.current_app.config['FEDERATION_UUID']:
                    try:
                        obj = get_object(data_obj_id)
                    except errors.ObjectDoesNotExistError:
                        raise errors.InvalidDataExportError('Local object #{} does not exist'.format(data_obj_id))
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
            all_lang_codes = [lang.lang_code for lang in languages.get_languages()]

            if entry_data.get('_type') == 'text':
                if entry_data.get('text') and isinstance(entry_data.get('text'), dict):
                    for lang_code in list(entry_data.get('text').keys()):
                        if lang_code not in all_lang_codes:
                            del entry_data['text'][lang_code]
