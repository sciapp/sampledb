# coding: utf-8
"""

"""

import base64
import datetime
from io import BytesIO
import json
import os
import flask
import flask_login
import itsdangerous
import werkzeug.utils
import qrcode
import qrcode.image.svg

from . import frontend
from .. import logic
from ..logic import user_log, object_log, comments
from ..logic.actions import ActionType, get_action
from ..logic.permissions import Permissions, get_user_object_permissions, object_is_public, get_object_permissions_for_users, set_object_public, set_user_object_permissions, set_group_object_permissions, set_project_object_permissions, get_objects_with_permissions, get_object_permissions_for_groups, get_object_permissions_for_projects
from ..logic.datatypes import JSONEncoder
from ..logic.users import get_user, get_users
from ..logic.schemas import validate, generate_placeholder
from ..logic.object_search import generate_filter_func
from ..logic.groups import get_group, get_user_groups
from ..logic.objects import create_object, update_object, get_object, get_object_versions
from ..logic.object_log import ObjectLogEntryType
from ..logic.projects import get_project, get_user_projects
from ..logic.files import FileLogEntryType
from ..logic.errors import GroupDoesNotExistError, ObjectDoesNotExistError, UserDoesNotExistError, ActionDoesNotExistError, ValidationError, ProjectDoesNotExistError
from .objects_forms import ObjectPermissionsForm, ObjectForm, ObjectVersionRestoreForm, ObjectUserPermissionsForm, CommentForm, ObjectGroupPermissionsForm, ObjectProjectPermissionsForm, FileForm, FileInformationForm, FileHidingForm
from ..utils import object_permissions_required
from .utils import jinja_filter
from .object_form_parser import parse_form_data

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/objects/')
@flask_login.login_required
def objects():
    try:
        action_id = int(flask.request.args.get('action', ''))
    except ValueError:
        action_id = None
    if action_id is not None:
        action = get_action(action_id)
        action_type = action.type
    else:
        action = None
        action_type = flask.request.args.get('t', '')
        action_type = {
            'samples': ActionType.SAMPLE_CREATION,
            'measurements': ActionType.MEASUREMENT,
            'simulations': ActionType.SIMULATION
        }.get(action_type, None)
    query_string = flask.request.args.get('q', '')
    filter_func = generate_filter_func(query_string)
    objects = get_objects_with_permissions(
        user_id=flask_login.current_user.id,
        permissions=Permissions.READ,
        filter_func=filter_func,
        action_id=action_id,
        action_type=action_type
    )

    for i, obj in enumerate(objects):
        if obj.version_id == 0:
            original_object = obj
        else:
            original_object = get_object(object_id=obj.object_id, version_id=0)
        objects[i] = {
            'object_id': obj.object_id,
            'version_id': obj.version_id,
            'created_by': get_user(original_object.user_id),
            'created_at': original_object.utc_datetime.strftime('%Y-%m-%d'),
            'modified_by': get_user(obj.user_id),
            'last_modified_at': obj.utc_datetime.strftime('%Y-%m-%d'),
            'data': obj.data,
            'schema': obj.schema,
            'action': get_action(obj.action_id),
            'display_properties': {}
        }

    # TODO: select display_properties? nested display_properties? find common properties? use searched for properties?
    display_properties = []
    display_property_titles = {}
    sample_ids = set()
    if action is not None:
        action_schema = action.schema
        display_properties = action_schema.get('displayProperties', [])
        for property_name in display_properties:
            display_property_titles[property_name] = action_schema['properties'][property_name]['title']

    for obj in objects:
        for property_name in display_properties:
            if property_name not in obj['data'] or '_type' not in obj['data'][property_name] or property_name not in obj['schema']['properties']:
                obj['display_properties'][property_name] = None
                continue
            obj['display_properties'][property_name] = (obj['data'][property_name], obj['schema']['properties'][property_name])
            if obj['schema']['properties'][property_name]['type'] == 'sample':
                sample_ids.add(obj['data'][property_name]['object_id'])

    objects.sort(key=lambda obj: obj['object_id'])
    samples = {
        sample_id: get_object(object_id=sample_id)
        for sample_id in sample_ids
    }
    if action_id is None:
        show_action = True
    else:
        show_action = False
    return flask.render_template('objects/objects.html', objects=objects, display_properties=display_properties, display_property_titles=display_property_titles, search_query=query_string, action_id=action_id, action_type=action_type, ActionType=ActionType, samples=samples, show_action=show_action)


@jinja_filter
def to_datatype(obj):
    return json.loads(json.dumps(obj), object_hook=JSONEncoder.object_hook)


def get_sub_data_and_schema(data, schema, id_prefix):
    sub_data = data
    sub_schema = schema
    try:
        for key in id_prefix.split('__'):
            if sub_schema['type'] == 'array':
                key = int(key)
                sub_schema = sub_schema['items']
            elif sub_schema['type'] == 'object':
                sub_schema = sub_schema['properties'][key]
            else:
                raise ValueError('invalid type')
            sub_data = sub_data[key]
        if sub_schema['type'] != 'array':
            raise ValueError('invalid type')
    except (ValueError, KeyError, IndexError, TypeError):
        # TODO: error handling/logging?
        raise ValueError('invalid action')
    return sub_data, sub_schema


def apply_action_to_form_data(action, form_data):
    new_form_data = form_data
    action_id_prefix, action_index, action_type = action[len('action_'):].rsplit('__', 2)
    if action_type == 'delete':
        deleted_item_index = int(action_index)
        parent_id_prefix = action_id_prefix
        new_form_data = {}
        for name in form_data:
            if not name.startswith(parent_id_prefix):
                new_form_data[name] = form_data[name]
            else:
                item_index, id_suffix = name[len(parent_id_prefix)+2:].split('__', 1)
                item_index = int(item_index)
                if item_index < deleted_item_index:
                    new_form_data[name] = form_data[name]
                if item_index > deleted_item_index:
                    new_name = parent_id_prefix + '__' + str(item_index-1) + '__' + id_suffix
                    new_form_data[new_name] = form_data[name]
    return new_form_data


def apply_action_to_data(action, data, schema):
    action_id_prefix, action_index, action_type = action[len('action_'):].rsplit('__', 2)
    if action_type not in ('add', 'delete', 'addcolumn', 'deletecolumn'):
        raise ValueError('invalid action')
    sub_data, sub_schema = get_sub_data_and_schema(data, schema, action_id_prefix.split('__', 1)[1])
    if action_type in ('addcolumn', 'deletecolumn') and (sub_schema["style"] != "table" or sub_schema["items"]["type"] != "array"):
        raise ValueError('invalid action')
    num_existing_items = len(sub_data)
    if action_type == 'add':
        if 'maxItems' not in sub_schema or num_existing_items < sub_schema["maxItems"]:
            sub_data.append(generate_placeholder(sub_schema["items"]))
    elif action_type == 'delete':
        action_index = int(action_index)
        if ('minItems' not in sub_schema or num_existing_items > sub_schema["minItems"]) and action_index < num_existing_items:
            del sub_data[action_index]
    elif action_type == 'addcolumn':
        for row in sub_data:
            row.append(generate_placeholder(sub_schema["items"]["items"]))
    elif action_type == 'deletecolumn':
        for row in sub_data:
            del row[-1]


def show_object_form(object, action):
    if object is None:
        data = generate_placeholder(action.schema)
    else:
        data = object.data
    # TODO: update schema
    # schema = get_action(object.action_id).schema
    if object is not None:
        schema = object.schema
    else:
        schema = action.schema
    action_id = action.id
    errors = []
    form_data = {}
    previous_actions = []
    serializer = itsdangerous.URLSafeSerializer(flask.current_app.config['SECRET_KEY'])
    form = ObjectForm()
    if flask.request.method != 'GET' and form.validate_on_submit():
        form_data = {k: v[0] for k, v in dict(flask.request.form).items()}

        if 'previous_actions' in flask.request.form:
            try:
                previous_actions = serializer.loads(flask.request.form['previous_actions'])
            except itsdangerous.BadData:
                flask.abort(400)

        if "action_submit" in form_data:
            object_data, errors = parse_form_data(dict(flask.request.form), schema)
            if object_data is not None  and not errors:
                try:
                    validate(object_data, schema)
                except ValidationError:
                    # TODO: proper logging
                    print('object schema validation failed')
                    # TODO: handle error
                    flask.abort(400)
                if object is None:
                    object = create_object(action_id=action.id, data=object_data, user_id=flask_login.current_user.id)
                    flask.flash('The object was created successfully.', 'success')
                else:
                    update_object(object_id=object.id, user_id=flask_login.current_user.id, data=object_data)
                    flask.flash('The object was updated successfully.', 'success')

                return flask.redirect(flask.url_for('.object', object_id=object.id))
        elif any(name.startswith('action_object__') and (name.endswith('__delete') or name.endswith('__add') or name.endswith('__addcolumn') or name.endswith('__deletecolumn')) for name in form_data):
            action = [name for name in form_data if name.startswith('action_')][0]
            previous_actions.append(action)

    if previous_actions:
        try:
            for action in previous_actions:
                apply_action_to_data(action, data, schema)
            form_data = apply_action_to_form_data(previous_actions[-1], form_data)
        except ValueError:
            flask.abort(400)

    # TODO: make this search more narrow
    samples = get_objects_with_permissions(
        user_id=flask_login.current_user.id,
        permissions=Permissions.READ,
        action_type=ActionType.SAMPLE_CREATION
    )
    if object is None:
        return flask.render_template('objects/forms/form_create.html', action_id=action_id, schema=schema, data=data, errors=errors, form_data=form_data, previous_actions=serializer.dumps(previous_actions), form=form, samples=samples, datetime=datetime)
    else:
        return flask.render_template('objects/forms/form_edit.html', schema=schema, data=data, object_id=object.object_id, errors=errors, form_data=form_data, previous_actions=serializer.dumps(previous_actions), form=form, samples=samples, datetime=datetime)


@frontend.route('/objects/<int:object_id>', methods=['GET', 'POST'])
@object_permissions_required(Permissions.READ)
def object(object_id):
    object = get_object(object_id=object_id)

    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    user_may_edit = Permissions.WRITE in user_permissions
    user_may_grant = Permissions.GRANT in user_permissions
    if not user_may_edit and flask.request.args.get('mode', '') == 'edit':
        return flask.abort(403)
    if flask.request.method == 'GET' and flask.request.args.get('mode', '') != 'edit':
        # TODO: make this search more narrow
        samples = get_objects_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ,
            action_type=ActionType.SAMPLE_CREATION
        )
        action = get_action(object.action_id)
        instrument = action.instrument
        object_type = {
            ActionType.SAMPLE_CREATION: "Sample",
            ActionType.MEASUREMENT: "Measurement",
            ActionType.SIMULATION: "Simulation"
        }.get(action.type, "Object")
        object_log_entries = object_log.get_object_log_entries(object_id=object_id, user_id=flask_login.current_user.id)

        if user_may_edit:
            serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
            token = serializer.dumps([flask_login.current_user.id, object_id])
            mobile_upload_url = flask.url_for('.mobile_file_upload', object_id=object_id, token=token, _external=True)
            image = qrcode.make(mobile_upload_url, image_factory=qrcode.image.svg.SvgPathFillImage)
            image_stream = BytesIO()
            image.save(image_stream)
            image_stream.seek(0)
            mobile_upload_qrcode = 'data:image/svg+xml;base64,' + base64.b64encode(image_stream.read()).decode('utf-8')
        else:
            mobile_upload_url = None
            mobile_upload_qrcode = None

        return flask.render_template(
            'objects/view/base.html',
            object_type=object_type,
            action=action,
            instrument=instrument,
            schema=object.schema,
            data=object.data,
            object_log_entries=object_log_entries,
            ObjectLogEntryType=ObjectLogEntryType,
            last_edit_datetime=object.utc_datetime,
            last_edit_user=get_user(object.user_id),
            object_id=object_id,
            user_may_edit=user_may_edit,
            user_may_comment=user_may_edit,
            comments=comments.get_comments_for_object(object_id),
            comment_form=CommentForm(),
            files=logic.files.get_files_for_object(object_id),
            file_source_instrument_exists=False,
            file_source_jupyterhub_exists=False,
            file_form=FileForm(),
            mobile_upload_url=mobile_upload_url,
            mobile_upload_qrcode=mobile_upload_qrcode,
            restore_form=None,
            version_id=object.version_id,
            user_may_grant=user_may_grant,
            samples=samples,
            FileLogEntryType=FileLogEntryType,
            file_information_form=FileInformationForm(),
            file_hiding_form=FileHidingForm()
        )

    return show_object_form(object, action=get_action(object.action_id))


@frontend.route('/objects/<int:object_id>/comments/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_comments(object_id):
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        content = comment_form.content.data
        comments.create_comment(object_id=object_id, user_id=flask_login.current_user.id, content=content)
        flask.flash('Successfully posted a comment.', 'success')
    else:
        flask.flash('Please enter a comment text.', 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/files/')
@flask_login.login_required
def existing_files_from_source():
    if 'file_source' not in flask.request.args:
        return flask.abort(400)
    file_source = flask.request.args['file_source']
    relative_path = flask.request.args.get('relative_path', '')
    while relative_path.startswith('/'):
        relative_path = relative_path[1:]
    try:
        return json.dumps(logic.files.get_existing_files_for_source(file_source, flask_login.current_user.id, relative_path, max_depth=2))
    except (logic.errors.InvalidFileSourceError, FileNotFoundError) as e:
        return flask.abort(404)


@frontend.route('/objects/<int:object_id>/files/<int:file_id>', methods=['GET'])
@object_permissions_required(Permissions.READ)
def object_file(object_id, file_id):
    file = logic.files.get_file_for_object(object_id, file_id)
    if file is None:
        return flask.abort(404)
    if file.is_hidden:
        return flask.abort(403)
    if 'preview' in flask.request.args:
        file_extension = os.path.splitext(file.original_file_name)[1]
        mime_type = flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, None)
        if mime_type is not None:
            return flask.send_file(file.open(), mimetype=mime_type, last_modified=file.utc_datetime)
    return flask.send_file(file.open(), as_attachment=True, attachment_filename=file.original_file_name, last_modified=file.utc_datetime)


@frontend.route('/objects/<int:object_id>/files/<int:file_id>', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def update_file_information(object_id, file_id):
    form = FileInformationForm()
    if not form.validate_on_submit():
        return flask.abort(400)
    title = form.title.data
    description = form.description.data
    try:
        logic.files.update_file_information(
            object_id=object_id,
            file_id=file_id,
            user_id=flask_login.current_user.id,
            title=title,
            description=description
        )
    except logic.errors.FileDoesNotExistError:
        return flask.abort(404)
    return flask.redirect(flask.url_for('.object', object_id=object_id, _anchor='file-{}'.format(file_id)))


@frontend.route('/objects/<int:object_id>/files/<int:file_id>/hide', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def hide_file(object_id, file_id):
    form = FileHidingForm()
    if not form.validate_on_submit():
        return flask.abort(400)
    reason = form.reason.data
    try:
        logic.files.hide_file(
            object_id=object_id,
            file_id=file_id,
            user_id=flask_login.current_user.id,
            reason=reason
        )
    except logic.errors.FileDoesNotExistError:
        return flask.abort(404)
    flask.flash('The file was hidden successfully.', 'success')
    return flask.redirect(flask.url_for('.object', object_id=object_id, _anchor='file-{}'.format(file_id)))


@frontend.route('/objects/<int:object_id>/files/mobile_upload/<token>', methods=['GET'])
def mobile_file_upload(object_id: int, token: str):
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
    try:
        user_id, object_id = serializer.loads(token, max_age=15*60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    return flask.render_template('mobile_upload.html', user_id=logic.users.get_user(user_id), object=logic.objects.get_object(object_id))


@frontend.route('/objects/<int:object_id>/files/mobile_upload/<token>', methods=['POST'])
def post_mobile_file_upload(object_id: int, token: str):
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='mobile-upload')
    try:
        user_id, object_id = serializer.loads(token, max_age=15*60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    files = flask.request.files.getlist('file_input')
    for file_storage in files:
        file_name = werkzeug.utils.secure_filename(file_storage.filename)
        logic.files.create_file(object_id, user_id, file_name, lambda stream: file_storage.save(dst=stream))
    return flask.render_template('mobile_upload_success.html', num_files=len(files))


@frontend.route('/objects/<int:object_id>/files/', methods=['POST'])
@object_permissions_required(Permissions.WRITE)
def post_object_files(object_id):
    file_form = FileForm()
    if file_form.validate_on_submit():
        file_source = file_form.file_source.data
        if file_source == 'local':
            files = flask.request.files.getlist(file_form.local_files.name)
            for file_storage in files:
                file_name = werkzeug.utils.secure_filename(file_storage.filename)
                logic.files.create_file(object_id, flask_login.current_user.id, file_name, lambda stream: file_storage.save(dst=stream))
            flask.flash('Successfully uploaded files.', 'success')
        elif file_source in logic.files.FILE_SOURCES.keys():
            file_names = file_form.file_names.data
            try:
                file_names = json.loads(file_names)
            except json.JSONDecodeError:
                flask.flash('Failed to upload files.', 'error')
                return flask.redirect(flask.url_for('.object', object_id=object_id))
            for file_name in file_names:
                try:
                    logic.files.copy_file(object_id, flask_login.current_user.id, file_source, file_name)
                except (FileNotFoundError, logic.errors.InvalidFileSourceError):
                    flask.flash('Failed to upload files.', 'error')
                    return flask.redirect(flask.url_for('.object', object_id=object_id))
            flask.flash('Successfully uploaded files.', 'success')
        else:
            flask.flash('Failed to upload files.', 'error')
    else:
        flask.flash('Failed to upload files.', 'error')
    return flask.redirect(flask.url_for('.object', object_id=object_id))


@frontend.route('/objects/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_object():
    action_id = flask.request.args.get('action_id', None)
    if action_id is None or action_id == '':
        # TODO: handle error
        return flask.abort(404)
    try:
        action = get_action(action_id)
    except ActionDoesNotExistError:
        return flask.abort(404)

    # TODO: check instrument permissions
    return show_object_form(None, action)


@frontend.route('/objects/<int:object_id>/versions/')
@object_permissions_required(Permissions.READ)
def object_versions(object_id):
    object = get_object(object_id=object_id)
    if object is None:
        return flask.abort(404)
    object_versions = get_object_versions(object_id=object_id)
    object_versions.sort(key=lambda object_version: -object_version.version_id)
    return flask.render_template('objects/object_versions.html', get_user=get_user, object=object, object_versions=object_versions)


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>')
@object_permissions_required(Permissions.READ)
def object_version(object_id, version_id):
    object = get_object(object_id=object_id, version_id=version_id)
    form = None
    user_permissions = get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id)
    if Permissions.WRITE in user_permissions:
        current_object = get_object(object_id=object_id)
        if current_object.version_id != version_id:
            form = ObjectVersionRestoreForm()
    user_may_grant = Permissions.GRANT in user_permissions
    action = get_action(object.action_id)
    instrument = action.instrument
    object_type = {
        ActionType.SAMPLE_CREATION: "Sample",
        ActionType.MEASUREMENT: "Measurement",
        ActionType.SIMULATION: "Simulation"
    }.get(action.type, "Object")
    return flask.render_template(
        'objects/view/base.html',
        is_archived=True,
        object_type=object_type,
        action=action,
        instrument=instrument,
        schema=object.schema,
        data=object.data,
        last_edit_datetime=object.utc_datetime,
        last_edit_user=get_user(object.user_id),
        object_id=object_id,
        version_id=version_id,
        restore_form=form,
        user_may_grant=user_may_grant
    )


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>/restore', methods=['GET', 'POST'])
@object_permissions_required(Permissions.WRITE)
def restore_object_version(object_id, version_id):
    if version_id < 0 or object_id < 0:
        return flask.abort(404)
    try:
        current_object = get_object(object_id=object_id)
    except ObjectDoesNotExistError:
        return flask.abort(404)
    if current_object.version_id <= version_id:
        return flask.abort(404)
    form = ObjectVersionRestoreForm()
    if form.validate_on_submit():
        logic.objects.restore_object_version(object_id=object_id, version_id=version_id, user_id=flask_login.current_user.id)
        return flask.redirect(flask.url_for('.object', object_id=object_id))
    return flask.render_template('objects/restore_object_version.html', object_id=object_id, version_id=version_id, restore_form=form)


@frontend.route('/objects/<int:object_id>/permissions')
@object_permissions_required(Permissions.READ)
def object_permissions(object_id):
    object = get_object(object_id)
    action = get_action(object.action_id)
    instrument = action.instrument
    user_permissions = get_object_permissions_for_users(object_id=object_id, include_instrument_responsible_users=False, include_groups=False, include_projects=False)
    group_permissions = get_object_permissions_for_groups(object_id=object_id, include_projects=False)
    project_permissions = get_object_permissions_for_projects(object_id=object_id)
    public_permissions = Permissions.READ if object_is_public(object_id) else Permissions.NONE
    if Permissions.GRANT in get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id):
        user_permission_form_data = []
        for user_id, permissions in user_permissions.items():
            if user_id is None:
                continue
            user_permission_form_data.append({'user_id': user_id, 'permissions': permissions.name.lower()})
        group_permission_form_data = []
        for group_id, permissions in group_permissions.items():
            if group_id is None:
                continue
            group_permission_form_data.append({'group_id': group_id, 'permissions': permissions.name.lower()})
        project_permission_form_data = []
        for project_id, permissions in project_permissions.items():
            if project_id is None:
                continue
            project_permission_form_data.append({'project_id': project_id, 'permissions': permissions.name.lower()})
        edit_user_permissions_form = ObjectPermissionsForm(public_permissions=public_permissions.name.lower(), user_permissions=user_permission_form_data, group_permissions=group_permission_form_data, project_permissions=project_permission_form_data)
        users = get_users()
        users = [user for user in users if user.id not in user_permissions]
        add_user_permissions_form = ObjectUserPermissionsForm()
        groups = get_user_groups(flask_login.current_user.id)
        groups = [group for group in groups if group.id not in group_permissions]
        add_group_permissions_form = ObjectGroupPermissionsForm()
        projects = get_user_projects(flask_login.current_user.id, include_groups=True)
        projects = [project for project in projects if project.id not in project_permissions]
        add_project_permissions_form = ObjectProjectPermissionsForm()
    else:
        edit_user_permissions_form = None
        add_user_permissions_form = None
        add_group_permissions_form = None
        add_project_permissions_form = None
        users = []
        groups = []
        projects = []
    return flask.render_template('objects/object_permissions.html', instrument=instrument, action=action, object=object, user_permissions=user_permissions, group_permissions=group_permissions, project_permissions=project_permissions, public_permissions=public_permissions, get_user=get_user, Permissions=Permissions, form=edit_user_permissions_form, users=users, groups=groups, projects=projects, add_user_permissions_form=add_user_permissions_form, add_group_permissions_form=add_group_permissions_form, get_group=get_group, add_project_permissions_form=add_project_permissions_form, get_project=get_project)


@frontend.route('/objects/<int:object_id>/permissions', methods=['POST'])
@object_permissions_required(Permissions.GRANT)
def update_object_permissions(object_id):
    edit_user_permissions_form = ObjectPermissionsForm()
    add_user_permissions_form = ObjectUserPermissionsForm()
    add_group_permissions_form = ObjectGroupPermissionsForm()
    add_project_permissions_form = ObjectProjectPermissionsForm()
    if 'edit_user_permissions' in flask.request.form and edit_user_permissions_form.validate_on_submit():
        set_object_public(object_id, edit_user_permissions_form.public_permissions.data == 'read')
        for user_permissions_data in edit_user_permissions_form.user_permissions.data:
            user_id = user_permissions_data['user_id']
            try:
                get_user(user_id)
            except UserDoesNotExistError:
                continue
            permissions = Permissions.from_name(user_permissions_data['permissions'])
            set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=permissions)
        for group_permissions_data in edit_user_permissions_form.group_permissions.data:
            group_id = group_permissions_data['group_id']
            try:
                get_group(group_id)
            except GroupDoesNotExistError:
                continue
            permissions = Permissions.from_name(group_permissions_data['permissions'])
            set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=permissions)
        for project_permissions_data in edit_user_permissions_form.project_permissions.data:
            project_id = project_permissions_data['project_id']
            try:
                get_project(project_id)
            except ProjectDoesNotExistError:
                continue
            permissions = Permissions.from_name(project_permissions_data['permissions'])
            set_project_object_permissions(object_id=object_id, project_id=project_id, permissions=permissions)
        user_log.edit_object_permissions(user_id=flask_login.current_user.id, object_id=object_id)
        flask.flash("Successfully updated object permissions.", 'success')
    elif 'add_user_permissions' in flask.request.form and add_user_permissions_form.validate_on_submit():
        user_id = add_user_permissions_form.user_id.data
        permissions = Permissions.from_name(add_user_permissions_form.permissions.data)
        object_permissions = get_object_permissions_for_users(object_id=object_id, include_instrument_responsible_users=False, include_groups=False, include_projects=False)
        assert permissions in [Permissions.READ, Permissions.WRITE, Permissions.GRANT]
        assert user_id not in object_permissions
        user_log.edit_object_permissions(user_id=flask_login.current_user.id, object_id=object_id)
        set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=permissions)
        flask.flash("Successfully updated object permissions.", 'success')
    elif 'add_group_permissions' in flask.request.form and add_group_permissions_form.validate_on_submit():
        group_id = add_group_permissions_form.group_id.data
        permissions = Permissions.from_name(add_group_permissions_form.permissions.data)
        object_permissions = get_object_permissions_for_groups(object_id=object_id)
        assert permissions in [Permissions.READ, Permissions.WRITE, Permissions.GRANT]
        assert group_id not in object_permissions
        user_log.edit_object_permissions(user_id=flask_login.current_user.id, object_id=object_id)
        set_group_object_permissions(object_id=object_id, group_id=group_id, permissions=permissions)
        flask.flash("Successfully updated object permissions.", 'success')
    elif 'add_project_permissions' in flask.request.form and add_project_permissions_form.validate_on_submit():
        project_id = add_project_permissions_form.project_id.data
        permissions = Permissions.from_name(add_project_permissions_form.permissions.data)
        object_permissions = get_object_permissions_for_projects(object_id=object_id)
        assert permissions in [Permissions.READ, Permissions.WRITE, Permissions.GRANT]
        assert project_id not in object_permissions
        user_log.edit_object_permissions(user_id=flask_login.current_user.id, object_id=object_id)
        set_project_object_permissions(object_id=object_id, project_id=project_id, permissions=permissions)
        flask.flash("Successfully updated object permissions.", 'success')
    else:
        flask.flash("A problem occurred while changing the object permissions. Please try again.", 'error')
    return flask.redirect(flask.url_for('.object_permissions', object_id=object_id))
