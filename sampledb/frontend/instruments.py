# coding: utf-8
"""

"""

import json
import os

import itsdangerous
import flask
import flask_login
from flask_wtf import FlaskForm
from wtforms import StringField, SelectMultipleField, BooleanField, MultipleFileField
from wtforms.validators import Length, DataRequired

from . import frontend
from ..logic.instruments import get_instruments, get_instrument, create_instrument, update_instrument, set_instrument_responsible_users
from ..logic.instrument_log_entries import get_instrument_log_entries, create_instrument_log_entry, get_instrument_log_file_attachment, create_instrument_log_file_attachment, create_instrument_log_object_attachment, get_instrument_log_object_attachments, get_instrument_log_categories, InstrumentLogCategoryTheme, create_instrument_log_category, update_instrument_log_category, delete_instrument_log_category
from ..logic.actions import ActionType
from ..logic.errors import InstrumentDoesNotExistError, InstrumentLogFileAttachmentDoesNotExistError, ObjectDoesNotExistError, UserDoesNotExistError
from ..logic.favorites import get_user_favorite_instrument_ids
from ..logic.users import get_users, get_user
from ..logic.objects import get_object
from ..logic.object_permissions import Permissions, get_objects_with_permissions
from .users.forms import ToggleFavoriteInstrumentForm
from .utils import check_current_user_is_not_readonly, markdown_to_safe_html, generate_qrcode

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class InstrumentLogEntryForm(FlaskForm):
    content = StringField()
    files = MultipleFileField()
    objects = SelectMultipleField()
    categories = SelectMultipleField()


@frontend.route('/instruments/')
@flask_login.login_required
def instruments():
    all_instruments = get_instruments()
    instruments = []
    for instrument in all_instruments:
        if instrument.is_hidden and not flask_login.current_user.is_admin and flask_login.current_user not in instrument.responsible_users:
            continue
        instruments.append(instrument)
    user_favorite_instrument_ids = get_user_favorite_instrument_ids(flask_login.current_user.id)
    # Sort by: favorite / not favorite, instrument name
    instruments.sort(key=lambda instrument: (
        0 if instrument.id in user_favorite_instrument_ids else 1,
        instrument.name.lower()
    ))
    toggle_favorite_instrument_form = ToggleFavoriteInstrumentForm()
    return flask.render_template(
        'instruments/instruments.html',
        instruments=instruments,
        user_favorite_instrument_ids=user_favorite_instrument_ids,
        toggle_favorite_instrument_form=toggle_favorite_instrument_form
    )


@frontend.route('/instruments/<int:instrument_id>', methods=['GET', 'POST'])
@flask_login.login_required
def instrument(instrument_id):
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    is_instrument_responsible_user = any(
        responsible_user.id == flask_login.current_user.id
        for responsible_user in instrument.responsible_users
    )
    if is_instrument_responsible_user or instrument.users_can_view_log_entries:
        instrument_log_entries = get_instrument_log_entries(instrument_id)
        attached_object_ids = set()
        for log_entry in instrument_log_entries:
            for object_attachment in get_instrument_log_object_attachments(log_entry.id):
                attached_object_ids.add(object_attachment.object_id)
        attached_objects = get_objects_with_permissions(flask_login.current_user.id, permissions=Permissions.READ, object_ids=attached_object_ids)
        attached_object_names = {
            object.id: object.data.get('name', {}).get('text', 'Unnamed Object')
            for object in attached_objects
        }
    else:
        instrument_log_entries = None
        attached_object_names = {}
    if is_instrument_responsible_user or instrument.users_can_create_log_entries:
        serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='instrument-log-mobile-upload')
        token = serializer.dumps([flask_login.current_user.id, instrument_id])
        mobile_upload_url = flask.url_for('.instrument_log_mobile_file_upload', instrument_id=instrument_id, token=token, _external=True)
        mobile_upload_qrcode = generate_qrcode(mobile_upload_url, should_cache=False)
    else:
        mobile_upload_url = None
        mobile_upload_qrcode = None
    instrument_log_entry_form = InstrumentLogEntryForm()
    instrument_log_entry_form.objects.choices = [
        (str(object.id), "{} (#{})".format(object.data.get('name', {}).get('text', 'Unnamed Object'), object.id))
        for object in get_objects_with_permissions(user_id=flask_login.current_user.id, permissions=Permissions.READ)
    ]
    instrument_log_categories = get_instrument_log_categories(instrument_id)
    instrument_log_entry_form.categories.choices = [
        (str(category.id), category.title)
        for category in instrument_log_categories
    ]
    if instrument_log_entry_form.validate_on_submit():
        check_current_user_is_not_readonly()
        if is_instrument_responsible_user or instrument.users_can_create_log_entries:
            log_entry_content = instrument_log_entry_form.content.data
            log_entry_has_files = any(file_storage.filename for file_storage in instrument_log_entry_form.files.data)
            object_ids = []
            for object_id in instrument_log_entry_form.objects.data:
                try:
                    object_ids.append(get_object(int(object_id)).id)
                except ObjectDoesNotExistError:
                    continue
                except ValueError:
                    continue
            log_entry_has_objects = bool(object_ids)
            if log_entry_content or log_entry_has_files or log_entry_has_objects:
                log_entry = create_instrument_log_entry(
                    instrument_id=instrument_id,
                    user_id=flask_login.current_user.id,
                    content=instrument_log_entry_form.content.data,
                    category_ids=[
                        int(category_id) for category_id in instrument_log_entry_form.categories.data
                    ]
                )
                for file_storage in instrument_log_entry_form.files.data:
                    if file_storage.filename:
                        file_name = file_storage.filename
                        content = file_storage.stream.read()
                        create_instrument_log_file_attachment(log_entry.id, file_name, content)
                for object_id in instrument_log_entry_form.objects.data:
                    try:
                        create_instrument_log_object_attachment(log_entry.id, int(object_id))
                    except ObjectDoesNotExistError:
                        continue
                flask.flash('You have created a new instrument log entry.', 'success')
                return flask.redirect(flask.url_for(
                    '.instrument',
                    instrument_id=instrument_id,
                    _anchor=f'log_entry-{log_entry.id}'
                ))
            else:
                flask.flash('Please enter a log entry text, upload a file or select an object to create a log entry.', 'error')
                return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
        else:
            flask.flash('You cannot create a log entry for this instrument.', 'error')
            return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
    return flask.render_template(
        'instruments/instrument.html',
        instrument=instrument,
        instrument_log_entries=instrument_log_entries,
        instrument_log_categories=instrument_log_categories,
        attached_object_names=attached_object_names,
        is_instrument_responsible_user=is_instrument_responsible_user,
        instrument_log_entry_form=instrument_log_entry_form,
        mobile_upload_url=mobile_upload_url,
        mobile_upload_qrcode=mobile_upload_qrcode,
        ActionType=ActionType
    )


class InstrumentForm(FlaskForm):
    name = StringField(validators=[Length(min=1, max=100)])
    description = StringField()
    instrument_responsible_users = SelectMultipleField()
    is_markdown = BooleanField(default=None)
    notes = StringField()
    notes_are_markdown = BooleanField(default=None)
    users_can_create_log_entries = BooleanField(default=False)
    users_can_view_log_entries = BooleanField(default=False)
    categories = StringField(validators=[DataRequired()])
    create_log_entry_default = BooleanField(default=False)
    is_hidden = BooleanField(default=False)


@frontend.route('/instruments/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_instrument():
    if not flask_login.current_user.is_admin:
        return flask.abort(401)
    check_current_user_is_not_readonly()
    instrument_form = InstrumentForm()
    instrument_form.instrument_responsible_users.choices = [
        (str(user.id), user.name)
        for user in get_users()
    ]
    if instrument_form.validate_on_submit():
        if instrument_form.is_markdown.data:
            description_as_html = markdown_to_safe_html(instrument_form.description.data)
        else:
            description_as_html = None
        if instrument_form.notes_are_markdown.data:
            notes_as_html = markdown_to_safe_html(instrument_form.notes.data)
        else:
            notes_as_html = None
        instrument = create_instrument(
            instrument_form.name.data,
            instrument_form.description.data,
            description_as_html=description_as_html,
            notes=instrument_form.notes.data,
            notes_as_html=notes_as_html,
            users_can_create_log_entries=instrument_form.users_can_create_log_entries.data,
            users_can_view_log_entries=instrument_form.users_can_view_log_entries.data,
            create_log_entry_default=instrument_form.create_log_entry_default.data,
            is_hidden=instrument_form.is_hidden.data
        )
        flask.flash('The instrument was created successfully.', 'success')
        instrument_responsible_user_ids = [
            int(user_id)
            for user_id in instrument_form.instrument_responsible_users.data
        ]
        set_instrument_responsible_users(instrument.id, instrument_responsible_user_ids)
        try:
            category_data = json.loads(instrument_form.categories.data)
        except Exception:
            pass
        else:
            themes_by_name = {
                theme.name.lower(): theme
                for theme in list(InstrumentLogCategoryTheme)
            }
            category_keys = {'id', 'title', 'theme'}
            if not isinstance(category_data, list):
                category_data = ()
            for category in category_data:
                # skip any invalid entries
                if not isinstance(category, dict):
                    continue
                if set(category.keys()) != category_keys:
                    continue
                if not all(isinstance(category[key], str) for key in category_keys):
                    continue
                category_title = category['title'].strip()
                if not category_title:
                    continue
                if len(category_title) > 100:
                    continue
                try:
                    category_id = int(category['id'])
                except ValueError:
                    continue
                category_theme = themes_by_name.get(category['theme'], InstrumentLogCategoryTheme.GRAY)
                if category_id < 0:
                    create_instrument_log_category(
                        instrument.id,
                        category['title'],
                        category_theme
                    )
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument.id))
    return flask.render_template(
        'instruments/instrument_form.html',
        submit_text='Create Instrument',
        instrument_log_category_themes=sorted(InstrumentLogCategoryTheme, key=lambda t: t.value),
        instrument_form=instrument_form
    )


@frontend.route('/instruments/<int:instrument_id>/edit', methods=['GET', 'POST'])
@flask_login.login_required
def edit_instrument(instrument_id):
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    check_current_user_is_not_readonly()
    if not flask_login.current_user.is_admin and flask_login.current_user not in instrument.responsible_users:
        return flask.abort(403)
    instrument_form = InstrumentForm()
    instrument_form.name.default = instrument.name
    instrument_form.description.default = instrument.description
    instrument_form.notes.default = instrument.notes
    instrument_form.instrument_responsible_users.choices = [
        (str(user.id), user.name)
        for user in get_users()
    ]
    instrument_form.instrument_responsible_users.default = [
        str(user.id)
        for user in instrument.responsible_users
    ]

    if not instrument_form.is_submitted():
        instrument_form.is_markdown.data = (instrument.description_as_html is not None)
        instrument_form.notes_are_markdown.data = (instrument.notes_as_html is not None)
        instrument_form.users_can_create_log_entries.data = instrument.users_can_create_log_entries
        instrument_form.users_can_view_log_entries.data = instrument.users_can_view_log_entries
        instrument_form.create_log_entry_default.data = instrument.create_log_entry_default
        instrument_form.is_hidden.data = instrument.is_hidden
    if instrument_form.validate_on_submit():
        if instrument_form.is_markdown.data:
            description_as_html = markdown_to_safe_html(instrument_form.description.data)
        else:
            description_as_html = None
        if instrument_form.notes_are_markdown.data:
            notes_as_html = markdown_to_safe_html(instrument_form.notes.data)
        else:
            notes_as_html = None
        update_instrument(
            instrument.id,
            instrument_form.name.data,
            instrument_form.description.data,
            description_as_html=description_as_html,
            notes=instrument_form.notes.data,
            notes_as_html=notes_as_html,
            users_can_create_log_entries=instrument_form.users_can_create_log_entries.data,
            users_can_view_log_entries=instrument_form.users_can_view_log_entries.data,
            create_log_entry_default=instrument_form.create_log_entry_default.data,
            is_hidden=instrument_form.is_hidden.data
        )
        flask.flash('The instrument was updated successfully.', 'success')
        instrument_responsible_user_ids = [
            int(user_id)
            for user_id in instrument_form.instrument_responsible_users.data
        ]
        set_instrument_responsible_users(instrument.id, instrument_responsible_user_ids)
        try:
            category_data = json.loads(instrument_form.categories.data)
        except Exception:
            pass
        else:
            themes_by_name = {
                theme.name.lower(): theme
                for theme in list(InstrumentLogCategoryTheme)
            }
            category_keys = {'id', 'title', 'theme'}
            if not isinstance(category_data, list):
                category_data = ()
            existing_category_ids = {
                category.id
                for category in get_instrument_log_categories(instrument_id)
            }
            valid_category_ids = set()
            for category in category_data:
                # skip any invalid entries
                if not isinstance(category, dict):
                    continue
                if set(category.keys()) != category_keys:
                    continue
                if not all(isinstance(category[key], str) for key in category_keys):
                    continue
                category_title = category['title'].strip()
                if not category_title:
                    continue
                if len(category_title) > 100:
                    continue
                try:
                    category_id = int(category['id'])
                except ValueError:
                    continue
                category_theme = themes_by_name.get(category['theme'], InstrumentLogCategoryTheme.GRAY)
                if category_id < 0:
                    new_category = create_instrument_log_category(
                        instrument.id,
                        category['title'],
                        category_theme
                    )
                    valid_category_ids.add(new_category.id)
                elif category_id in existing_category_ids:
                    update_instrument_log_category(
                        category_id,
                        category['title'],
                        category_theme
                    )
                    valid_category_ids.add(category_id)
            for category in get_instrument_log_categories(instrument_id):
                if category.id not in valid_category_ids:
                    delete_instrument_log_category(category.id)
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument.id))
    return flask.render_template(
        'instruments/instrument_form.html',
        submit_text='Update Instrument',
        instrument_log_category_themes=sorted(InstrumentLogCategoryTheme, key=lambda t: t.value),
        instrument_log_categories=get_instrument_log_categories(instrument.id),
        instrument_form=instrument_form
    )


@frontend.route('/instruments/<int:instrument_id>/log/<int:log_entry_id>/file_attachments/<int:file_attachment_id>')
@flask_login.login_required
def instrument_log_file_attachment(instrument_id, log_entry_id, file_attachment_id):
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    if not instrument.users_can_view_log_entries and flask_login.current_user not in instrument.responsible_users:
        return flask.abort(403)
    try:
        file_attachment = get_instrument_log_file_attachment(file_attachment_id)
    except InstrumentLogFileAttachmentDoesNotExistError:
        return flask.abort(404)
    file_extension = os.path.splitext(file_attachment.file_name)[1]
    download = 'preview' not in flask.request.args
    mime_type = flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, '')
    if not mime_type:
        download = True
    if download:
        return flask.Response(
            file_attachment.content,
            200,
            headers={
                'Content-Disposition': f'attachment; filename="{file_attachment.file_name}"'
            }
        )
    else:
        return flask.Response(
            file_attachment.content,
            200,
            headers={
                'Content-Type': mime_type
            }
        )


@frontend.route('/instruments/<int:instrument_id>/log/mobile_upload/<token>', methods=['GET'])
def instrument_log_mobile_file_upload(instrument_id: int, token: str):
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='instrument-log-mobile-upload')
    try:
        user_id, instrument_id = serializer.loads(token, max_age=15 * 60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    try:
        user = get_user(user_id)
    except UserDoesNotExistError:
        return flask.abort(403)
    if not instrument.users_can_create_log_entries and user not in instrument.responsible_users:
        return flask.abort(403)
    if user.is_readonly:
        return flask.abort(403)
    return flask.render_template('mobile_upload.html', user_id=get_user(user_id), instrument=instrument)


@frontend.route('/instruments/<int:instrument_id>/log/mobile_upload/<token>', methods=['POST'])
def post_instrument_log_mobile_file_upload(instrument_id: int, token: str):
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='instrument-log-mobile-upload')
    try:
        user_id, instrument_id = serializer.loads(token, max_age=15 * 60)
    except itsdangerous.BadSignature:
        return flask.abort(400)
    try:
        user = get_user(user_id)
    except UserDoesNotExistError:
        return flask.abort(403)
    if not instrument.users_can_create_log_entries and user not in instrument.responsible_users:
        return flask.abort(403)
    if user.is_readonly:
        return flask.abort(403)
    files = flask.request.files.getlist('file_input')
    if not files:
        return flask.redirect(
            flask.url_for(
                '.instrument_log_mobile_file_upload',
                instrument_id=instrument_id,
                token=token
            )
        )
    if files:
        category_ids = []
        log_entry = create_instrument_log_entry(
            instrument_id=instrument_id,
            user_id=user_id,
            content='',
            category_ids=category_ids
        )
        for file_storage in files:
            create_instrument_log_file_attachment(
                instrument_log_entry_id=log_entry.id,
                file_name=file_storage.filename,
                content=file_storage.stream.read()
            )
    return flask.render_template('mobile_upload_success.html')
