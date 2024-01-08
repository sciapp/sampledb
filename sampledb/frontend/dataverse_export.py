# coding: utf-8
"""

"""
import typing

import flask
import flask_login
import itsdangerous
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, SelectMultipleField
from wtforms.validators import InputRequired

from . import frontend
from .. import logic
from ..utils import object_permissions_required, FlaskResponseT
from ..models import Permissions, DataverseExportStatus, BackgroundTaskStatus

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class DataverseExportForm(FlaskForm):
    dataverse = SelectField(
        choices=[],
        validators=[InputRequired()]
    )
    files = SelectMultipleField()
    tags = SelectMultipleField()
    api_token = PasswordField()


class DataverseAPITokenForm(FlaskForm):
    api_token = PasswordField(validators=[InputRequired()])
    store_api_token = BooleanField()


@frontend.route('/objects/<int:object_id>/dataverse_export/', methods=['GET', 'POST'])
@object_permissions_required(Permissions.GRANT)
def dataverse_export(object_id: int) -> FlaskResponseT:
    dataverse_export_status = logic.dataverse_export.get_dataverse_export_state(object_id)
    existing_dataverse_url = logic.dataverse_export.get_dataverse_url(object_id)

    if dataverse_export_status:
        if dataverse_export_status == DataverseExportStatus.TASK_CREATED:
            flask.flash(_('The object is currently being exported.'), 'info')
            return flask.redirect(flask.url_for('.object', object_id=object_id))
        elif dataverse_export_status == DataverseExportStatus.EXPORT_FINISHED and existing_dataverse_url:
            return flask.render_template(
                'objects/dataverse_export_already_exported.html',
                object_id=object_id,
                dataverse_url=existing_dataverse_url
            )

    server_url = flask.current_app.config['DATAVERSE_URL']
    if not server_url:
        return flask.abort(404)

    object = logic.objects.get_object(object_id)
    if object.eln_import_id is not None:
        return flask.abort(403)
    if object.component_id is not None:
        flask.flash(_('Exporting imported objects is not supported.'), 'error')
        return flask.redirect(flask.url_for('.object', object_id=object_id))

    dataverse_export_form = DataverseExportForm()

    user_id = flask_login.current_user.id
    api_token = logic.dataverse_export.get_user_valid_api_token(server_url, user_id)
    had_invalid_api_token = False
    dataverse_api_token_form = DataverseAPITokenForm()
    if not api_token:
        if dataverse_api_token_form.validate_on_submit():
            form_api_token = dataverse_api_token_form.api_token.data.strip()
            api_token_valid = logic.dataverse_export.is_api_token_valid(server_url, form_api_token)
            if api_token_valid:
                api_token = form_api_token
                if dataverse_api_token_form.store_api_token.data:
                    logic.settings.set_user_settings(user_id, {'DATAVERSE_API_TOKEN': api_token})
                else:
                    dataverse_export_form.api_token.data = api_token
            else:
                had_invalid_api_token = True
                api_token = None
        elif dataverse_export_form.validate_on_submit():
            form_api_token = dataverse_export_form.api_token.data.strip()
            api_token_valid = logic.dataverse_export.is_api_token_valid(server_url, form_api_token)
            if api_token_valid:
                api_token = form_api_token
            else:
                had_invalid_api_token = True
                api_token = None
    if not api_token:
        return flask.render_template(
            'objects/dataverse_export_api_token.html',
            object_id=object_id,
            dataverse_api_token_form=dataverse_api_token_form,
            had_invalid_api_token=had_invalid_api_token
        )

    if object.data:
        properties = {
            tuple(whitelist_path): metadata
            for metadata, whitelist_path, title_path in logic.dataverse_export.flatten_metadata(object.data)
            if not ('_type' in metadata and metadata['_type'] == 'tags')
        }
    else:
        properties = {}

    root_dataverses = flask.current_app.config['DATAVERSE_ROOT_IDS'].split(',')
    candidate_dataverses = []
    for dataverse in root_dataverses:
        dataverse_info = logic.dataverse_export.get_dataverse_info(server_url, api_token, dataverse)
        if dataverse_info is not None:
            candidate_dataverses.append((0, dataverse_info))
            candidate_dataverses += logic.dataverse_export.list_dataverses(server_url, api_token, dataverse)

    dataverses = []
    for level, dataverse in candidate_dataverses:
        dataverses.append((
            level,
            dataverse,
            logic.dataverse_export.dataverse_has_required_metadata_blocks(server_url, api_token, dataverse['id'])
        ))

    dataverse_export_form.dataverse.choices = [
        (str(dataverse['id']), '\u00A0' * (2 * level) + dataverse['title'])
        for level, dataverse, enabled in dataverses
        if enabled
    ]
    if not dataverse_export_form.dataverse.choices:
        flask.flash(_('No suitable Dataverses available for export.'), 'error')

    dataverse_export_form.files.choices = [
        (str(file.id), file.original_file_name)
        for file in logic.files.get_files_for_object(object_id)
        if file.storage == 'database'
    ]

    if object.data:
        tags_set = set()
        for property in object.data.values():
            if '_type' in property and property['_type'] == 'tags':
                for tag in property['tags']:
                    tags_set.add(tag)
        tags = list(tags_set)
        tags.sort()
    else:
        tags = []

    dataverse_export_form.tags.choices = [
        (tag, tag)
        for tag in tags
    ]

    export_properties: typing.List[typing.List[typing.Union[int, str]]] = [
        ['name']
    ]
    for whitelist_path in properties:
        if 'property,' + ','.join(map(str, whitelist_path)) in flask.request.form:
            export_properties.append(list(whitelist_path))
    if dataverse_export_form.validate_on_submit():
        file_id_whitelist_set = set()
        for file_id in dataverse_export_form.files.data:
            try:
                file_id = int(file_id)
            except ValueError:
                continue
            file_id_whitelist_set.add(file_id)
        file_id_whitelist = list(file_id_whitelist_set)
        file_id_whitelist.sort()
        tag_whitelist_set = set()
        for tag in dataverse_export_form.tags.data:
            if tag in tags:
                tag_whitelist_set.add(tag)
        tag_whitelist = list(tag_whitelist_set)
        tag_whitelist.sort()
        dataverse = dataverse_export_form.dataverse.data
        task_status_or_result, task = logic.background_tasks.background_dataverse_export.post_dataverse_export_task(
            object_id=object_id,
            user_id=flask_login.current_user.id,
            server_url=server_url,
            api_token=api_token,
            dataverse=dataverse,
            property_whitelist=export_properties,
            file_id_whitelist=file_id_whitelist,
            tag_whitelist=tag_whitelist
        )
        if task:
            serializer = itsdangerous.URLSafeSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='dataverse-export-task')
            token = serializer.dumps((flask_login.current_user.id, task.id))
            return flask.redirect(flask.url_for(".dataverse_export_loading", task_id=task.id, token=token))
        else:
            success, export_result = typing.cast(typing.Tuple[bool, dict[str, typing.Any]], task_status_or_result)
            if success:
                return flask.redirect(export_result['url'])
            else:
                error_message = export_result['error_message']
                flask.flash(_('An error occurred while exporting the object: %(error)s', error=_(error_message, service_name=flask.current_app.config["SERVICE_NAME"], dataverse_name=flask.current_app.config["DATAVERSE_NAME"])), 'error')
                return flask.redirect(flask.url_for(".dataverse_export", object_id=object_id))

    return flask.render_template(
        "objects/dataverse_export.html",
        properties=properties,
        export_properties=export_properties,
        dataverses=dataverses,
        object_id=object_id,
        get_title_for_property=lambda path: logic.dataverse_export.get_title_for_property(path, object.schema) if object.schema else '?',
        get_property_export_default=lambda path: logic.dataverse_export.get_property_export_default(path, object.schema) if object.schema else False,
        dataverse_export_form=dataverse_export_form
    )


@frontend.route("/objects/<int:task_id>/dataverse_export_loading/", methods=['GET'])
@flask_login.login_required
def dataverse_export_loading(task_id: int) -> FlaskResponseT:
    serializer = itsdangerous.URLSafeSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='dataverse-export-task')
    token = flask.request.args.get('token', '')
    try:
        if serializer.loads(token) != [flask_login.current_user.id, task_id]:
            return flask.abort(403)
    except itsdangerous.BadData:
        return flask.abort(403)
    task_result = logic.background_tasks.get_background_task_result(task_id, False)
    if task_result:
        if task_result["status"].is_final():
            if task_result["status"] == BackgroundTaskStatus.DONE:
                return flask.redirect(task_result["result"])
            else:
                return flask.render_template('objects/dataverse_export_loading.html', polling=False, error_message=task_result['result'])
        else:
            return flask.render_template('objects/dataverse_export_loading.html', task_id=task_id, polling=True, token=token), 202
    else:
        return flask.abort(404)


@frontend.route("/objects/<int:task_id>/dataverse_export_status/", methods=['GET'])
@flask_login.login_required
def dataverse_export_status(task_id: int) -> FlaskResponseT:
    serializer = itsdangerous.URLSafeSerializer(secret_key=flask.current_app.config['SECRET_KEY'], salt='dataverse-export-task')
    token = flask.request.args.get('token', '')
    try:
        if serializer.loads(token) != [flask_login.current_user.id, task_id]:
            return flask.abort(403)
    except itsdangerous.BadData:
        return flask.abort(403)
    task_result = logic.background_tasks.get_background_task_result(task_id, False)
    if task_result:
        if task_result["status"].is_final():
            if task_result["status"] == BackgroundTaskStatus.DONE:
                return flask.jsonify({
                    "dataverse_url": task_result["result"]
                })
            else:
                return flask.jsonify({
                    "url": flask.url_for(".dataverse_export_loading", task_id=task_id, token=token),
                    "error_message": task_result["result"]
                }), 406

        else:
            return flask.jsonify({}), 202
    else:
        return flask.jsonify({
            "url": flask.url_for(".dataverse_export_loading", task_id=task_id, token=token),
            "error_message": "task_id not found"
        }), 404
