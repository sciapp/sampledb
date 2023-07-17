# coding: utf-8
"""

"""
import string
import typing

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, SelectMultipleField
from wtforms.validators import InputRequired

from . import frontend
from .. import logic
from ..utils import object_permissions_required, FlaskResponseT
from ..models import Permissions, SciCatExportType


class SciCatExportForm(FlaskForm):
    tags = SelectMultipleField()
    owner_group = SelectField(validators=[InputRequired()])
    access_groups = SelectMultipleField()
    instrument = SelectField(validators=[InputRequired()])
    sample = SelectField(validators=[InputRequired()])
    input_datasets = SelectMultipleField()
    api_token = PasswordField()


class SciCatAPITokenForm(FlaskForm):
    api_token = PasswordField(validators=[InputRequired()])
    store_api_token = BooleanField()


@frontend.route('/objects/<int:object_id>/scicat_export/', methods=['GET', 'POST'])
@object_permissions_required(Permissions.GRANT)
def scicat_export(object_id: int) -> FlaskResponseT:
    existing_scicat_url = logic.scicat_export.get_scicat_url(object_id)
    if existing_scicat_url:
        return flask.render_template(
            'objects/scicat_export_already_exported.html',
            object_id=object_id,
            scicat_url=existing_scicat_url
        )

    api_url = flask.current_app.config['SCICAT_API_URL']
    frontend_url = flask.current_app.config['SCICAT_FRONTEND_URL']
    if not api_url or not frontend_url:
        return flask.abort(404)

    object = logic.objects.get_object(object_id)
    if object.eln_import_id is not None:
        return flask.abort(403)
    if object.component_id is not None or object.data is None or object.schema is None:
        flask.flash(_('Exporting imported objects is not supported.'), 'error')
        return flask.redirect(flask.url_for('.object', object_id=object_id))

    if object.action_id is not None:
        action = logic.actions.get_action(object.action_id)
        object_export_type = action.type.scicat_export_type if action.type is not None else None
    else:
        object_export_type = None
    if object_export_type is None:
        flask.flash(_("The SciCat export type is not set for objects of this type."), 'error')
        return flask.redirect(flask.url_for('.object', object_id=object_id))

    try:
        scicat_export_form = SciCatExportForm()

        user_id = flask_login.current_user.id
        api_token = logic.scicat_export.get_user_valid_api_token(api_url, user_id)
        had_invalid_api_token = False
        scicat_api_token_form = SciCatAPITokenForm()

        if not api_token:
            if scicat_api_token_form.validate_on_submit():
                form_api_token = scicat_api_token_form.api_token.data.strip()
                api_token_valid = logic.scicat_export.is_api_token_valid(api_url, form_api_token)
                if api_token_valid:
                    api_token = form_api_token
                    if scicat_api_token_form.store_api_token.data:
                        logic.settings.set_user_settings(user_id, {'SCICAT_API_TOKEN': api_token})
                    else:
                        scicat_export_form.api_token.data = api_token
                else:
                    had_invalid_api_token = True
                    api_token = None
            elif scicat_export_form.validate_on_submit():
                form_api_token = scicat_export_form.api_token.data.strip()
                api_token_valid = logic.scicat_export.is_api_token_valid(api_url, form_api_token)
                if api_token_valid:
                    api_token = form_api_token
                else:
                    had_invalid_api_token = True
                    api_token = None

        if not api_token:
            return flask.render_template(
                'objects/scicat_export_api_token.html',
                object_id=object_id,
                scicat_api_token_form=scicat_api_token_form,
                had_invalid_api_token=had_invalid_api_token
            )

        user_groups = logic.scicat_export.get_user_groups(api_url, api_token)
        if user_groups:
            scicat_export_form.owner_group.choices = [
                (group_name, group_name)
                for group_name in user_groups
            ]
            scicat_export_form.access_groups.choices = scicat_export_form.owner_group.choices[:]
        else:
            scicat_export_form.owner_group.choices = [('-', '—')]
            scicat_export_form.access_groups.choices = []

        scicat_export_form.instrument.choices = [('-', '—')]
        if object_export_type == SciCatExportType.RAW_DATASET:
            instruments = logic.scicat_export.get_instruments(api_url, api_token)
            if instruments:
                scicat_export_form.instrument.choices += instruments

        properties = {
            tuple(whitelist_path): metadata
            for metadata, whitelist_path, title_path in logic.dataverse_export.flatten_metadata(object.data)
            if not ('_type' in metadata and metadata['_type'] == 'tags') and all(c in string.ascii_letters + string.digits + '_' for c in ''.join(map(str, title_path)))
        }

        if object_export_type in {SciCatExportType.RAW_DATASET, SciCatExportType.DERIVED_DATASET}:
            tags_set = set()
            for property in object.data.values():
                if '_type' in property and property['_type'] == 'tags':
                    for tag in property['tags']:
                        tags_set.add(tag)
            tags = list(tags_set)
            tags.sort()

            scicat_export_form.tags.choices = [
                (tag, tag)
                for tag in tags
            ]
        else:
            tags = []
            scicat_export_form.tags.choices = []

        scicat_export_form.sample.choices = [('-', '—')]
        if object_export_type == SciCatExportType.RAW_DATASET:
            exported_referenced_objects = logic.scicat_export.get_exported_referenced_objects(object.data, object.schema, user_id)
            exported_referenced_samples = {
                export
                for export in exported_referenced_objects
                if export.type == SciCatExportType.SAMPLE
            }
            for export in exported_referenced_samples:
                if Permissions.READ in logic.object_permissions.get_user_object_permissions(object_id=export.object_id, user_id=user_id):
                    object_name = logic.objects.get_object(export.object_id).name
                    if object_name:
                        if isinstance(object_name, dict) and 'en' in object_name:
                            object_name = object_name['en']
                        else:
                            object_name = str(object_name)
                else:
                    object_name = None
                if not object_name:
                    object_name = f"Object #{export.object_id}"
                scicat_export_form.sample.choices.append((export.scicat_pid, object_name))

        scicat_export_form.input_datasets.choices = []
        if object_export_type == SciCatExportType.DERIVED_DATASET:
            exported_referenced_objects = logic.scicat_export.get_exported_referenced_objects(object.data, object.schema, user_id)
            exported_referenced_datasets = {
                export
                for export in exported_referenced_objects
                if export.type in {SciCatExportType.RAW_DATASET, SciCatExportType.DERIVED_DATASET}
            }
            for export in exported_referenced_datasets:
                if Permissions.READ in logic.object_permissions.get_user_object_permissions(object_id=export.object_id, user_id=user_id):
                    object_name = logic.objects.get_object(export.object_id).name
                    if object_name:
                        if isinstance(object_name, dict) and 'en' in object_name:
                            object_name = object_name['en']
                        else:
                            object_name = str(object_name)
                else:
                    object_name = None
                if not object_name:
                    object_name = f"Object #{export.object_id}"
                scicat_export_form.input_datasets.choices.append(('PID/' + export.scicat_pid, object_name))

        property_whitelist: typing.List[typing.List[typing.Union[str, int]]] = [
            ['name']
        ]
        for whitelist_path in properties:
            if 'property,' + ','.join(map(str, whitelist_path)) in flask.request.form:
                property_whitelist.append(list(whitelist_path))

        if 'do_export' in flask.request.form and scicat_export_form.validate_on_submit():
            tag_whitelist_set = set()
            for tag in scicat_export_form.tags.data:
                if tag in tags:
                    tag_whitelist_set.add(tag)
            tag_whitelist = list(tag_whitelist_set)
            tag_whitelist.sort()
            scicat_url = logic.scicat_export.upload_object(
                object_id=object_id,
                user_id=flask_login.current_user.id,
                api_url=api_url,
                frontend_url=frontend_url,
                api_token=api_token,
                property_whitelist=property_whitelist,
                tag_whitelist=tag_whitelist,
                object_export_type=object_export_type,
                owner_group=scicat_export_form.owner_group.data,
                access_groups=scicat_export_form.access_groups.data if scicat_export_form.access_groups.data else None,
                instrument_pid=scicat_export_form.instrument.data if scicat_export_form.instrument.data != '-' else None,
                sample_pid=scicat_export_form.sample.data if scicat_export_form.sample.data != '-' else None,
                input_dataset_pids=scicat_export_form.input_datasets.data if scicat_export_form.input_datasets.data else None
            )
            if scicat_url is not None:
                return flask.redirect(scicat_url)
            flask.flash(_("An unknown error occurred while uploading the dataset."), 'error')

        return flask.render_template(
            "objects/scicat_export.html",
            properties=properties,
            export_properties=property_whitelist,
            object_id=object_id,
            get_title_for_property=lambda path: logic.dataverse_export.get_title_for_property(path, object.schema),
            get_property_export_default=lambda path: logic.scicat_export.get_property_export_default(path, object.schema),
            scicat_export_form=scicat_export_form
        )
    except logic.errors.SciCatNotReachableError:
        flask.flash(_("%(scicat_name)s is currently unreachable, please try again later.", scicat_name=flask.current_app.config['SCICAT_NAME']), 'error')
        return flask.redirect(flask.url_for('.object', object_id=object_id))
