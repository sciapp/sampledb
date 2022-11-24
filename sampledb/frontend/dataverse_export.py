# coding: utf-8
"""

"""


import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, SelectMultipleField
from wtforms.validators import InputRequired

from . import frontend
from .. import logic
from .. utils import object_permissions_required, Permissions

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
def dataverse_export(object_id):
    dataverse_export_status = logic.dataverse_export.get_dataverse_export_state(object_id)
    existing_dataverse_url = logic.dataverse_export.get_dataverse_url(object_id)

    if dataverse_export_status:
        if dataverse_export_status == logic.dataverse_export.DataverseExportStatus.TASK_CREATED:
            flask.flash(_('The object is currently being exported.'), 'info')
            return flask.redirect(flask.url_for('.object', object_id=object_id))
        elif dataverse_export_status == logic.dataverse_export.DataverseExportStatus.EXPORT_FINISHED and existing_dataverse_url:
            return flask.render_template(
                'objects/dataverse_export_already_exported.html',
                object_id=object_id,
                dataverse_url=existing_dataverse_url
            )

    server_url = flask.current_app.config['DATAVERSE_URL']
    if not server_url:
        return flask.abort(404)

    object = logic.objects.get_object(object_id)
    if object.component_id is not None:
        flask.flash(_('Exporting imported objects is not supported.', 'error'))
        return flask.redirect(flask.url_for('.object', object_id=object_id))

    dataverse_export_form = DataverseExportForm()

    user_id = flask_login.current_user.id
    api_token = logic.dataverse_export.get_user_valid_api_token(server_url, user_id)
    had_invalid_api_token = False
    dataverse_api_token_form = DataverseAPITokenForm()
    if not api_token:
        if dataverse_api_token_form.validate_on_submit():
            api_token = dataverse_api_token_form.api_token.data.strip()
            api_token_valid = logic.dataverse_export.is_api_token_valid(server_url, api_token)
            if api_token_valid:
                if dataverse_api_token_form.store_api_token.data:
                    logic.settings.set_user_settings(user_id, {'DATAVERSE_API_TOKEN': api_token})
                else:
                    dataverse_export_form.api_token.data = api_token
            else:
                had_invalid_api_token = True
                api_token = None
        elif dataverse_export_form.validate_on_submit():
            api_token = dataverse_export_form.api_token.data.strip()
            api_token_valid = logic.dataverse_export.is_api_token_valid(server_url, api_token)
            if not api_token_valid:
                had_invalid_api_token = True
                api_token = None
    if not api_token:
        return flask.render_template(
            'objects/dataverse_export_api_token.html',
            object_id=object_id,
            dataverse_api_token_form=dataverse_api_token_form,
            had_invalid_api_token=had_invalid_api_token
        )

    properties = [
        (metadata, path)
        for metadata, path in logic.dataverse_export.flatten_metadata(object.data)
        if not ('_type' in metadata and metadata['_type'] == 'tags')
    ]

    root_dataverses = flask.current_app.config['DATAVERSE_ROOT_IDS'].split(',')
    dataverses = []
    for dataverse in root_dataverses:
        dataverse_info = logic.dataverse_export.get_dataverse_info(server_url, api_token, dataverse)
        if dataverse_info is not None:
            dataverses.append((0, dataverse_info))
            dataverses += logic.dataverse_export.list_dataverses(server_url, api_token, dataverse)

    candidate_dataverses = dataverses
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
        (str(file.id), file.data['original_file_name'])
        for file in logic.files.get_files_for_object(object_id)
        if file.data.get('storage') in {'local', 'database'}
    ]

    tags = set()
    for property in object.data.values():
        if '_type' in property and property['_type'] == 'tags':
            for tag in property['tags']:
                tags.add(tag)
    tags = list(tags)
    tags.sort()

    dataverse_export_form.tags.choices = [
        (tag, tag)
        for tag in tags
    ]

    export_properties = [
        ['name']
    ]
    for metadata, path in properties:
        if 'property,' + ','.join(map(str, path)) in flask.request.form:
            export_properties.append(path)
    if dataverse_export_form.validate_on_submit():
        file_id_whitelist = set()
        for file_id in dataverse_export_form.files.data:
            try:
                file_id = int(file_id)
            except ValueError:
                continue
            file_id_whitelist.add(file_id)
        file_id_whitelist = list(file_id_whitelist)
        file_id_whitelist.sort()
        tag_whitelist = set()
        for tag in dataverse_export_form.tags.data:
            if tag in tags:
                tag_whitelist.add(tag)
        tag_whitelist = list(tag_whitelist)
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
            return flask.redirect(flask.url_for(".dataverse_export_loading", task_id=task.id))
        else:
            success, export_result = task_status_or_result
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
        get_title_for_property=lambda path: logic.dataverse_export.get_title_for_property(path, object.schema),
        get_property_export_default=lambda path: logic.dataverse_export.get_property_export_default(path, object.schema),
        dataverse_export_form=dataverse_export_form
    )


@frontend.route("/objects/<int:task_id>/dataverse_export_loading/", methods=['GET'])
def dataverse_export_loading(task_id):
    task_result = logic.background_tasks.get_background_task_result(task_id, False)
    if task_result:
        if task_result["status"].is_final():
            if task_result["status"] == logic.background_tasks.core.BackgroundTaskStatus.DONE:
                return flask.redirect(task_result["result"])
            else:
                return flask.render_template('objects/dataverse_export_loading.html', polling=False, error_message=task_result['result'])
        else:
            return flask.render_template('objects/dataverse_export_loading.html', task_id=task_id, polling=True), 202
    else:
        return flask.abort(404)


@frontend.route("/objects/<int:task_id>/dataverse_export_status/", methods=['GET'])
def dataverse_export_status(task_id):
    task_result = logic.background_tasks.get_background_task_result(task_id, False)
    if task_result:
        if task_result["status"].is_final():
            if task_result["status"] == logic.background_tasks.core.BackgroundTaskStatus.DONE:
                return {"dataverse_url": task_result["result"]}
            else:
                return {
                    "url": flask.url_for(".dataverse_export_loading", task_id=task_id),
                    "error_message": task_result["result"]
                }, 406

        else:
            return {}, 202
    else:
        return {
            "url": flask.url_for(".dataverse_export_loading", task_id=task_id),
            "error_message": "task_id not found"
        }, 404
