# coding: utf-8
"""

"""

import datetime
import json
import os
import typing

import itsdangerous
import flask
import flask_login
import wtforms
import werkzeug
from flask_babel import _
from flask_wtf import FlaskForm
import pytz
from wtforms import StringField, SelectMultipleField, BooleanField, MultipleFileField, IntegerField, SelectField
from wtforms.validators import DataRequired, ValidationError, InputRequired

from . import frontend
from .objects.permissions import get_object_if_current_user_has_read_permissions, get_fed_object_if_current_user_has_read_permissions
from .objects.view import get_project_if_it_exists
from .utils import get_user_if_exists
from ..logic.action_permissions import get_user_action_permissions
from ..logic.components import get_component
from ..logic.instruments import get_instrument, create_instrument, update_instrument, set_instrument_responsible_users, get_instruments, set_instrument_location, get_instrument_object_links, set_instrument_object
from ..logic.instrument_log_entries import get_instrument_log_entries, create_instrument_log_entry, get_instrument_log_file_attachment, create_instrument_log_file_attachment, create_instrument_log_object_attachment, get_instrument_log_categories, create_instrument_log_category, update_instrument_log_category, delete_instrument_log_category, update_instrument_log_entry, hide_instrument_log_file_attachment, hide_instrument_log_object_attachment, get_instrument_log_entry, get_instrument_log_object_attachment
from ..logic.instrument_translations import get_instrument_translations_for_instrument, set_instrument_translation, delete_instrument_translation
from ..logic.languages import get_languages, get_language, Language, get_user_language
from ..logic.actions import get_actions, get_action
from ..logic.action_types import ActionType, get_action_types, get_action_type
from ..logic.errors import InstrumentDoesNotExistError, InstrumentLogFileAttachmentDoesNotExistError, ObjectDoesNotExistError, UserDoesNotExistError, InstrumentLogEntryDoesNotExistError, InstrumentLogObjectAttachmentDoesNotExistError, InstrumentObjectLinkAlreadyExistsError
from ..logic.favorites import get_user_favorite_instrument_ids, get_user_favorite_action_ids
from ..logic.markdown_images import mark_referenced_markdown_images_as_permanent
from ..logic.users import get_users, get_user
from ..logic.objects import get_object
from ..logic.object_permissions import get_object_info_with_permissions, get_user_object_permissions
from ..logic.settings import get_user_settings, set_user_settings
from ..logic.shares import get_shares_for_object
from ..logic.locations import get_location, get_object_location_assignment
from .users.forms import ToggleFavoriteInstrumentForm
from .utils import check_current_user_is_not_readonly, generate_qrcode, get_locations_form_data, parse_filter_id_params, build_modified_url
from ..utils import FlaskResponseT
from ..logic.utils import get_translated_text
from ..logic.markdown_to_html import markdown_to_safe_html
from ..logic.topics import set_instrument_topics, get_topics, get_topic
from .validators import MultipleObjectIdValidator

from ..models.permissions import Permissions
from ..models.instrument_log_entries import InstrumentLogCategoryTheme

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

INSTRUMENT_LIST_FILTER_PARAMETERS = (
    'instrument_list_filters',
    'topic_ids'
)


class MultipleIntegerField(SelectMultipleField):  # type: ignore[misc]
    def pre_validate(self, form: wtforms.Form) -> None:
        if self.data:
            for d in self.data:
                try:
                    int(d)
                except ValueError:
                    raise ValidationError("Invalid value")


class InstrumentLogEntryForm(FlaskForm):
    content = StringField()
    content_is_markdown = BooleanField()
    files = MultipleFileField()
    objects = SelectMultipleField(validators=[MultipleObjectIdValidator(Permissions.READ)], validate_choice=False)
    categories = SelectMultipleField()
    log_entry_id = IntegerField()
    existing_files = MultipleIntegerField()
    existing_objects = MultipleIntegerField()
    has_event_utc_datetime = BooleanField()
    event_utc_datetime = StringField()

    def validate_event_utc_datetime(form, field: wtforms.BooleanField) -> None:
        if field.data:
            try:
                language = get_user_language(flask_login.current_user)
                parsed_datetime = datetime.datetime.strptime(field.data, language.datetime_format_datetime)
                # convert datetime to utc
                local_datetime = pytz.timezone(flask_login.current_user.timezone or 'UTC').localize(parsed_datetime)
                utc_datetime = local_datetime.astimezone(pytz.utc)
                if abs(utc_datetime.year - datetime.date.today().year) > 1000:
                    raise ValueError()
                field.data = utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                raise ValidationError("Invalid datetime")
        else:
            field.data = None


class InstrumentLogOrderForm(FlaskForm):
    ascending = BooleanField()
    attribute = StringField(validators=[DataRequired()])

    def validate_attribute(form, field: wtforms.StringField) -> None:
        if field.data not in ('datetime', 'username'):
            raise ValidationError("invalid log order attribute")


class ObjectLinkForm(FlaskForm):
    object_id = IntegerField(validators=[InputRequired()])


def _parse_instrument_list_filters(
        params: werkzeug.datastructures.MultiDict[str, str],
        valid_topic_ids: typing.List[int]
) -> typing.Tuple[
    bool,
    typing.Optional[typing.List[int]],
]:
    FALLBACK_RESULT = False, None
    success, filter_topic_ids = parse_filter_id_params(
        params=params,
        param_aliases=['topic_ids'],
        valid_ids=valid_topic_ids,
        id_map={},
        multi_params_error='',
        parse_error=_('Unable to parse topic IDs.'),
        invalid_id_error=_('Invalid topic ID.')
    )
    if not success:
        return FALLBACK_RESULT

    return (
        True,
        filter_topic_ids,
    )


@frontend.route('/instruments/')
@flask_login.login_required
def instruments() -> FlaskResponseT:
    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        return flask.abort(404)
    all_instruments = get_instruments()
    instruments = []
    user_has_admin_permissions = flask_login.current_user.has_admin_permissions
    for instrument in all_instruments:
        if instrument.is_hidden and not user_has_admin_permissions and flask_login.current_user not in instrument.responsible_users:
            continue
        instruments.append(instrument)
    user_favorite_instrument_ids = get_user_favorite_instrument_ids(flask_login.current_user.id)

    topics = get_topics()
    valid_topic_ids = [topic.id for topic in topics]

    if 'instrument_list_filters' in flask.request.args or any(any(flask.request.args.getlist(param)) for param in INSTRUMENT_LIST_FILTER_PARAMETERS):
        (
            success,
            filter_topic_ids,
        ) = _parse_instrument_list_filters(
            params=flask.request.args,
            valid_topic_ids=valid_topic_ids
        )
        if not success:
            return flask.abort(400)
    else:
        filter_topic_ids = get_user_settings(user_id=flask_login.current_user.id)['DEFAULT_INSTRUMENT_LIST_FILTERS'].get('filter_topic_ids', [])

    if filter_topic_ids is None or flask.current_app.config['DISABLE_TOPICS']:
        filter_topic_ids = []

    if filter_topic_ids:
        instruments = [
            instrument
            for instrument in instruments
            if any(topic in [topic.id for topic in instrument.topics] for topic in filter_topic_ids)
        ]

    filter_topic_infos = []
    if filter_topic_ids:
        for topic_id in filter_topic_ids:
            topic = get_topic(topic_id)
            filter_topic_infos.append({
                'name': get_translated_text(topic.name, default=_('Unnamed Topic')),
                'url': flask.url_for('.topic', topic_id=topic_id)
            })

    # Sort by: favorite / not favorite, instrument name
    instruments.sort(key=lambda instrument: (
        0 if instrument.id in user_favorite_instrument_ids else 1,
        get_translated_text(instrument.name).lower()
    ))
    toggle_favorite_instrument_form = ToggleFavoriteInstrumentForm()
    return flask.render_template(
        'instruments/instruments.html',
        instruments=instruments,
        user_favorite_instrument_ids=user_favorite_instrument_ids,
        toggle_favorite_instrument_form=toggle_favorite_instrument_form,
        get_user=get_user,
        get_component=get_component,
        topics=topics,
        filter_topic_infos=filter_topic_infos,
        filter_topic_ids=filter_topic_ids,
    )


@frontend.route('/instruments/', methods=['POST'])
@flask_login.login_required
def save_instrument_list_defaults() -> FlaskResponseT:
    if 'save_default_instrument_filters' in flask.request.form:
        topics = get_topics()
        valid_topic_ids = [topic.id for topic in topics]
        success, filter_topic_ids = _parse_instrument_list_filters(
            params=flask.request.form,
            valid_topic_ids=valid_topic_ids
        )
        if not success:
            return flask.abort(400)
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_INSTRUMENT_LIST_FILTERS': {
                    'filter_topic_ids': filter_topic_ids,
                }
            }
        )
        return flask.redirect(build_modified_url('.instruments', blocked_parameters=INSTRUMENT_LIST_FILTER_PARAMETERS))
    if 'clear_default_instrument_filters' in flask.request.form:
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_INSTRUMENT_LIST_FILTERS': {}
            }
        )
        return flask.redirect(build_modified_url('.instruments', blocked_parameters=INSTRUMENT_LIST_FILTER_PARAMETERS))
    return flask.abort(400)


@frontend.route('/instruments/<int:instrument_id>', methods=['GET', 'POST'])
@flask_login.login_required
def instrument(instrument_id: int) -> FlaskResponseT:
    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        return flask.abort(404)
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    user_language = get_user_language(flask_login.current_user)

    is_instrument_responsible_user = any(
        responsible_user.id == flask_login.current_user.id
        for responsible_user in instrument.responsible_users
    )
    already_linked_object_ids = []
    linkable_action_ids = []
    if is_instrument_responsible_user and not flask_login.current_user.is_readonly:
        object_link_form = ObjectLinkForm()
        if instrument.object_id is None:
            already_linked_object_ids = [link[1] for link in get_instrument_object_links()]
            for action_type in get_action_types():
                if action_type.enable_instrument_link:
                    linkable_action_ids.extend([
                        action.id
                        for action in get_actions(action_type_id=action_type.id)
                    ])
    else:
        object_link_form = None
    user_favorite_action_ids = get_user_favorite_action_ids(flask_login.current_user.id)

    template_kwargs = {
        "get_user": get_user_if_exists,
        "get_component": get_component,
        "user_favorite_action_ids": user_favorite_action_ids,
    }
    linked_object = None
    show_object_title = False
    if instrument.object_id is not None:
        linked_object_permissions = get_user_object_permissions(object_id=instrument.object_id, user_id=flask_login.current_user.id)
        if Permissions.READ in linked_object_permissions:
            linked_object = get_object(instrument.object_id)
            if linked_object.data and linked_object.schema:
                show_object_title = get_user_settings(flask_login.current_user.id)['SHOW_OBJECT_TITLE']
                # various getters used by object view
                template_kwargs.update({
                    "get_object": get_object,
                    "get_object_if_current_user_has_read_permissions": get_object_if_current_user_has_read_permissions,
                    "get_fed_object_if_current_user_has_read_permissions": get_fed_object_if_current_user_has_read_permissions,
                    "get_location": get_location,
                    "get_object_location_assignment": get_object_location_assignment,
                    "get_project": get_project_if_it_exists,
                    "get_action_type": get_action_type,
                    "get_shares_for_object": get_shares_for_object,
                })

    if is_instrument_responsible_user or instrument.users_can_view_log_entries:
        instrument_log_entries = get_instrument_log_entries(instrument_id)
        attached_object_ids = set()
        for log_entry in instrument_log_entries:
            for object_attachment in log_entry.object_attachments:
                attached_object_ids.add(object_attachment.object_id)
        attached_object_infos = get_object_info_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ,
            object_ids=list(attached_object_ids)
        )
        attached_object_names = {
            object_info.object_id: get_translated_text(object_info.name_json)
            for object_info in attached_object_infos
        }
        instrument_log_user_ids = {
            log_entry.user_id
            for log_entry in instrument_log_entries
        }
        instrument_log_users = [
            get_user(user_id)
            for user_id in instrument_log_user_ids
        ]
        instrument_log_users.sort(key=lambda user: (user.name, user.id))
    else:
        instrument_log_entries = None
        instrument_log_users = []
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
    instrument_log_entry_form.objects.choices = []
    instrument_log_categories = get_instrument_log_categories(instrument_id)
    instrument_log_entry_form.categories.choices = [
        (str(category.id), category.title)
        for category in instrument_log_categories
    ]
    instrument_log_entry_form.event_utc_datetime.format = user_language.datetime_format_datetime
    instrument_log_entry_form.event_utc_datetime.format_moment = user_language.datetime_format_moment
    if instrument_log_entry_form.validate_on_submit():
        check_current_user_is_not_readonly()
        if 'action_edit_content' in flask.request.form:
            if is_instrument_responsible_user or instrument.users_can_view_log_entries:
                try:
                    log_entry_id = int(instrument_log_entry_form.log_entry_id.data)
                    log_entry = get_instrument_log_entry(log_entry_id)
                except ValueError:
                    return flask.abort(400)
                except InstrumentLogEntryDoesNotExistError:
                    return flask.abort(400)
                if instrument_log_entry_form.content_is_markdown.data:
                    log_entry_html = markdown_to_safe_html(instrument_log_entry_form.content.data)
                    mark_referenced_markdown_images_as_permanent(log_entry_html)
                if instrument_log_entry_form.has_event_utc_datetime.data:
                    event_utc_datetime = instrument_log_entry_form.event_utc_datetime.data
                else:
                    event_utc_datetime = None
                update_instrument_log_entry(
                    log_entry_id=log_entry_id,
                    content=instrument_log_entry_form.content.data,
                    category_ids=[
                        int(category_id) for category_id in instrument_log_entry_form.categories.data
                    ],
                    content_is_markdown=instrument_log_entry_form.content_is_markdown.data,
                    event_utc_datetime=event_utc_datetime
                )
                for file_storage in instrument_log_entry_form.files.data:
                    if file_storage.filename:
                        file_name = file_storage.filename
                        content = file_storage.stream.read()
                        create_instrument_log_file_attachment(log_entry.id, file_name, content)
                previously_attached_object_ids = {
                    object_attachment.object_id: object_attachment
                    for object_attachment in log_entry.object_attachments
                }
                for object_id in instrument_log_entry_form.objects.data:
                    if int(object_id) in previously_attached_object_ids:
                        object_attachment = previously_attached_object_ids[int(object_id)]
                        if object_attachment.is_hidden:
                            hide_instrument_log_object_attachment(object_attachment.id, set_hidden=False)
                        continue
                    try:
                        create_instrument_log_object_attachment(log_entry.id, int(object_id))
                    except ObjectDoesNotExistError:
                        continue
                if instrument_log_entry_form.existing_files.data:
                    for file_attachment_id in instrument_log_entry_form.existing_files.data:
                        file_attachment_id = int(file_attachment_id)
                        try:
                            file_attachment = get_instrument_log_file_attachment(file_attachment_id)
                            if file_attachment.log_entry_id == log_entry_id:
                                hide_instrument_log_file_attachment(file_attachment_id)
                        except InstrumentLogFileAttachmentDoesNotExistError:
                            continue
                if instrument_log_entry_form.existing_objects.data:
                    for object_attachment_id in instrument_log_entry_form.existing_objects.data:
                        object_attachment_id = int(object_attachment_id)
                        try:
                            object_attachment = get_instrument_log_object_attachment(object_attachment_id)
                            if object_attachment.log_entry_id == log_entry_id:
                                hide_instrument_log_object_attachment(object_attachment_id)
                        except InstrumentLogObjectAttachmentDoesNotExistError:
                            continue
                flask.flash(_('You have successfully updated the instrument log entry.'), 'success')
                return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
            else:
                return flask.abort(400)
        elif is_instrument_responsible_user or instrument.users_can_create_log_entries:
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
                if instrument_log_entry_form.content_is_markdown.data:
                    log_entry_html = markdown_to_safe_html(instrument_log_entry_form.content.data)
                    mark_referenced_markdown_images_as_permanent(log_entry_html)
                if instrument_log_entry_form.has_event_utc_datetime.data:
                    event_utc_datetime = instrument_log_entry_form.event_utc_datetime.data
                else:
                    event_utc_datetime = None
                log_entry = create_instrument_log_entry(
                    instrument_id=instrument_id,
                    user_id=flask_login.current_user.id,
                    content=instrument_log_entry_form.content.data,
                    category_ids=[
                        int(category_id) for category_id in instrument_log_entry_form.categories.data
                    ],
                    content_is_markdown=instrument_log_entry_form.content_is_markdown.data,
                    event_utc_datetime=event_utc_datetime
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
                flask.flash(_('You have created a new instrument log entry.'), 'success')
                return flask.redirect(flask.url_for(
                    '.instrument',
                    instrument_id=instrument_id,
                    _anchor=f'log_entry-{log_entry.id}'
                ))
            else:
                flask.flash(_('Please enter a log entry text, upload a file or select an object to create a log entry.'), 'error')
                return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
        else:
            flask.flash(_('You cannot create a log entry for this instrument.'), 'error')
            return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
    elif instrument_log_entry_form.event_utc_datetime.errors:
        flask.flash(_("Please enter a valid event datetime."), 'error')
    user_settings = get_user_settings(flask_login.current_user.id)
    instrument_log_order_ascending = user_settings['INSTRUMENT_LOG_ORDER_ASCENDING']
    instrument_log_order_attribute = user_settings['INSTRUMENT_LOG_ORDER_ATTRIBUTE']
    if instrument_log_entries is not None:
        if instrument_log_order_attribute == 'datetime':
            instrument_log_entries.sort(
                key=lambda entry: entry.versions[-1].event_utc_datetime or entry.versions[0].utc_datetime,
                reverse=not instrument_log_order_ascending
            )
        elif instrument_log_order_attribute == 'username':
            instrument_log_entries.sort(
                key=lambda entry: (entry.author.name, entry.author.id),
                reverse=not instrument_log_order_ascending
            )

    instrument_actions = [
        action
        for action in get_actions(instrument_id=instrument.id)
        if Permissions.READ in get_user_action_permissions(action.id, flask_login.current_user.id) and (not action.is_hidden or flask_login.current_user.is_admin)
    ]
    instrument_actions.sort(key=lambda action: (action.id not in user_favorite_action_ids, get_translated_text(action.name), action.id))
    instrument_is_favorite = instrument.id in get_user_favorite_instrument_ids(flask_login.current_user.id)
    return flask.render_template(
        'instruments/instrument.html',
        instrument=instrument,
        instrument_is_favorite=instrument_is_favorite,
        instrument_actions=instrument_actions,
        instrument_log_entries=instrument_log_entries,
        instrument_log_users=instrument_log_users,
        instrument_log_categories=instrument_log_categories,
        attached_object_names=attached_object_names,
        is_instrument_responsible_user=is_instrument_responsible_user,
        instrument_log_entry_form=instrument_log_entry_form,
        instrument_log_order_form=InstrumentLogOrderForm(),
        mobile_upload_url=mobile_upload_url,
        mobile_upload_qrcode=mobile_upload_qrcode,
        instrument_log_order_ascending=instrument_log_order_ascending,
        instrument_log_order_attribute=instrument_log_order_attribute,
        linked_object=linked_object,
        object_link_form=object_link_form,
        linkable_action_ids=linkable_action_ids,
        already_linked_object_ids=already_linked_object_ids,
        show_object_title=show_object_title,
        languages=get_languages(),
        ActionType=ActionType,
        **template_kwargs
    )


class InstrumentForm(FlaskForm):
    instrument_responsible_users = SelectMultipleField()
    is_markdown = BooleanField(default=False)
    short_description_is_markdown = BooleanField(default=False)
    notes_is_markdown = BooleanField(default=False)
    translations = StringField(validators=[DataRequired()])
    categories = StringField(validators=[DataRequired()])
    users_can_create_log_entries = BooleanField(default=False)
    users_can_view_log_entries = BooleanField(default=False)
    create_log_entry_default = BooleanField(default=False)
    is_hidden = BooleanField(default=False)
    location = SelectField()
    show_linked_object_data = BooleanField(default=True)
    topics = SelectMultipleField()


@frontend.route('/instruments/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_instrument() -> FlaskResponseT:
    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        return flask.abort(404)
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    check_current_user_is_not_readonly()

    allowed_language_ids = [
        language.id
        for language in get_languages(only_enabled_for_input=True)
    ]

    instrument_form = InstrumentForm()
    instrument_form.instrument_responsible_users.choices = [
        (str(user.id), user)
        for user in get_users()
        if user.fed_id is None and (not user.is_hidden or (flask_login.current_user.is_admin and flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN']))
    ]
    instrument_form.topics.choices = [
        (str(topic.id), topic)
        for topic in get_topics()
    ]
    topic_ids_str = flask.request.args.get('topic_ids')
    if topic_ids_str is not None:
        valid_topic_id_strs = [
            topic_id_str
            for topic_id_str, topic in instrument_form.topics.choices
        ]
        instrument_form.topics.default = [
            topic_id_str
            for topic_id_str in topic_ids_str.split(',')
            if topic_id_str in valid_topic_id_strs
        ]
    all_choices, choices = get_locations_form_data(filter=lambda location: location.type is not None and location.type.enable_instruments)
    instrument_form.location.choices = choices
    instrument_form.location.all_choices = all_choices
    instrument_form.location.default = '-1'
    if not instrument_form.is_submitted():
        instrument_form.location.data = instrument_form.location.default

    if instrument_form.validate_on_submit():

        try:
            translation_data = json.loads(instrument_form.translations.data)
        except Exception:
            pass
        else:
            translation_keys = {'id', 'language_id', 'name', 'description',
                                'short_description', 'notes'}
            if not isinstance(translation_data, list):
                translation_data = ()
            for translation in translation_data:
                if not isinstance(translation, dict):
                    continue
                if set(translation.keys()) != translation_keys:
                    continue

                language_id = int(translation['language_id'])
                name = translation['name'].strip()

                if language_id == Language.ENGLISH:
                    try:
                        if len(name) < 1 or len(name) > 100:
                            flask.flash(_('Please enter an instrument name.'), 'error')
                            return flask.render_template('instruments/instrument_form.html',
                                                         submit_text='Create Instrument',
                                                         cancel_url=flask.url_for('.instruments'),
                                                         instrument_log_category_themes=sorted(InstrumentLogCategoryTheme, key=lambda t: typing.cast(int, t.value)),
                                                         ENGLISH=get_language(Language.ENGLISH),
                                                         languages=get_languages(only_enabled_for_input=True),
                                                         instrument_form=instrument_form
                                                         )
                    except Exception:
                        flask.flash(_('Please enter an instrument name.'), 'error')
                        return flask.render_template('instruments/instrument_form.html',
                                                     submit_text='Create Instrument',
                                                     cancel_url=flask.url_for('.instruments'),
                                                     instrument_log_category_themes=sorted(InstrumentLogCategoryTheme, key=lambda t: typing.cast(int, t.value)),
                                                     ENGLISH=get_language(Language.ENGLISH),
                                                     languages=get_languages(only_enabled_for_input=True),
                                                     instrument_form=instrument_form
                                                     )
            instrument = create_instrument(
                description_is_markdown=instrument_form.is_markdown.data,
                notes_is_markdown=instrument_form.notes_is_markdown.data,
                short_description_is_markdown=instrument_form.short_description_is_markdown.data,
                users_can_create_log_entries=instrument_form.users_can_create_log_entries.data,
                users_can_view_log_entries=instrument_form.users_can_view_log_entries.data,
                create_log_entry_default=instrument_form.create_log_entry_default.data,
                is_hidden=instrument_form.is_hidden.data,
                show_linked_object_data=instrument_form.show_linked_object_data.data,
            )

            for translation in translation_data:
                language_id = int(translation['language_id'])
                name = translation['name'].strip()
                description = translation['description'].strip()
                short_description = translation['short_description'].strip()
                notes = translation['notes'].strip()

                if language_id not in allowed_language_ids:
                    continue

                if instrument_form.is_markdown.data:
                    description_as_html = markdown_to_safe_html(description, anchor_prefix="instrument-description")
                    mark_referenced_markdown_images_as_permanent(description_as_html)
                if instrument_form.notes_is_markdown.data:
                    notes_as_html = markdown_to_safe_html(notes, anchor_prefix="instrument-notes")
                    mark_referenced_markdown_images_as_permanent(notes_as_html)
                if instrument_form.short_description_is_markdown.data:
                    short_description_as_html = markdown_to_safe_html(short_description, anchor_prefix="instrument-short-description")
                    mark_referenced_markdown_images_as_permanent(short_description_as_html)

                set_instrument_translation(
                    instrument_id=instrument.id,
                    language_id=language_id,
                    name=name,
                    description=description,
                    short_description=short_description,
                    notes=notes
                )

        flask.flash(_('The instrument was created successfully.'), 'success')
        instrument_responsible_user_ids = [
            int(user_id)
            for user_id in instrument_form.instrument_responsible_users.data
        ]
        set_instrument_responsible_users(instrument.id, instrument_responsible_user_ids)
        if not flask.current_app.config['DISABLE_TOPICS']:
            topic_ids = [
                int(topic_id)
                for topic_id in instrument_form.topics.data
            ]
            set_instrument_topics(instrument.id, topic_ids)

        if instrument_form.location.data is not None and instrument_form.location.data != '-1':
            set_instrument_location(instrument.id, int(instrument_form.location.data))

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
        cancel_url=flask.url_for('.instruments'),
        instrument_log_category_themes=sorted(InstrumentLogCategoryTheme, key=lambda t: typing.cast(int, t.value)),
        ENGLISH=get_language(Language.ENGLISH),
        languages=get_languages(only_enabled_for_input=True),
        instrument_form=instrument_form,
        instrument_translations={}
    )


@frontend.route('/instruments/<int:instrument_id>/edit', methods=['GET', 'POST'])
@flask_login.login_required
def edit_instrument(instrument_id: int) -> FlaskResponseT:
    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        return flask.abort(404)
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    if instrument.component_id is not None:
        flask.flash(_('Editing imported instruments is not yet supported.'), 'error')
        return flask.abort(403)
    check_current_user_is_not_readonly()
    if not flask_login.current_user.is_admin and flask_login.current_user not in instrument.responsible_users:
        return flask.abort(403)

    allowed_language_ids = [
        language.id
        for language in get_languages(only_enabled_for_input=True)
    ]

    instrument_form = InstrumentForm()

    instrument_form.instrument_responsible_users.choices = [
        (str(user.id), user)
        for user in get_users()
        if user in instrument.responsible_users or (user.fed_id is None and (not user.is_hidden or (flask_login.current_user.is_admin and flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN'])))
    ]
    instrument_form.instrument_responsible_users.default = [
        str(user.id)
        for user in instrument.responsible_users
    ]
    instrument_form.topics.choices = [
        (str(topic.id), topic)
        for topic in get_topics()
    ]
    instrument_form.topics.default = [
        str(topic.id)
        for topic in instrument.topics
    ]
    all_choices, choices = get_locations_form_data(filter=lambda location: location.type is not None and location.type.enable_instruments)
    instrument_form.location.choices = choices
    instrument_form.location.all_choices = all_choices

    if instrument.location_id is not None:
        instrument_form.location.default = str(instrument.location_id)
    else:
        instrument_form.location.default = '-1'

    if not instrument_form.is_submitted():
        instrument_form.is_markdown.data = instrument.description_is_markdown
        instrument_form.short_description_is_markdown.data = instrument.short_description_is_markdown
        instrument_form.notes_is_markdown.data = instrument.notes_is_markdown
        instrument_form.users_can_create_log_entries.data = instrument.users_can_create_log_entries
        instrument_form.users_can_view_log_entries.data = instrument.users_can_view_log_entries
        instrument_form.create_log_entry_default.data = instrument.create_log_entry_default
        instrument_form.is_hidden.data = instrument.is_hidden
        instrument_form.location.data = instrument_form.location.default
        instrument_form.show_linked_object_data.data = instrument.show_linked_object_data
    location_is_invalid = instrument_form.location.data not in {
        location_id_str
        for location_id_str, location_name in choices
    }
    if instrument_form.validate_on_submit():
        update_instrument(
            instrument_id=instrument.id,
            description_is_markdown=instrument_form.is_markdown.data,
            short_description_is_markdown=instrument_form.short_description_is_markdown.data,
            notes_is_markdown=instrument_form.notes_is_markdown.data,
            users_can_create_log_entries=instrument_form.users_can_create_log_entries.data,
            users_can_view_log_entries=instrument_form.users_can_view_log_entries.data,
            create_log_entry_default=instrument_form.create_log_entry_default.data,
            is_hidden=instrument_form.is_hidden.data,
            show_linked_object_data=instrument_form.show_linked_object_data.data
        )
        instrument_responsible_user_ids = [
            int(user_id)
            for user_id in instrument_form.instrument_responsible_users.data
        ]
        set_instrument_responsible_users(instrument.id, instrument_responsible_user_ids)
        if not flask.current_app.config['DISABLE_TOPICS']:
            topic_ids = [
                int(topic_id)
                for topic_id in instrument_form.topics.data
            ]
            set_instrument_topics(instrument.id, topic_ids)

        if instrument_form.location.data is not None and instrument_form.location.data != '-1':
            set_instrument_location(instrument.id, int(instrument_form.location.data))
        else:
            set_instrument_location(instrument.id, None)

        # translations
        try:
            translation_data = json.loads(instrument_form.translations.data)
        except Exception:
            pass
        else:
            translation_keys = {'language_id', 'name', 'description',
                                'short_description', 'notes'}

            if not isinstance(translation_data, list):
                translation_data = ()

            valid_translations = set()
            for translation in translation_data:
                if not isinstance(translation, dict):
                    continue
                if set(translation.keys()) != translation_keys:
                    continue
                language_id = int(translation['language_id'])
                name = translation['name'].strip()
                description = translation['description'].strip()
                short_description = translation['short_description']
                notes = translation['notes'].strip()

                if language_id not in allowed_language_ids:
                    continue

                if language_id == Language.ENGLISH:
                    error = False
                    if not isinstance(name, str) or not isinstance(description, str)\
                            or not isinstance(short_description, str) or not isinstance(notes, str):
                        error = True
                    if len(name) < 1 or len(name) > 100:
                        error = True
                    if error:
                        flask.flash(_('Please enter an english instrument name.'), 'error')
                        instrument_translations_list = get_instrument_translations_for_instrument(instrument.id)
                        instrument_language_ids = [
                            translation.language_id
                            for translation in instrument_translations_list

                        ]
                        instrument_translations = {
                            instrument_translation.language_id: instrument_translation
                            for instrument_translation in instrument_translations_list
                        }
                        ENGLISH = get_language(Language.ENGLISH)
                        return flask.render_template(
                            'instruments/instrument_form.html',
                            submit_text=_('Save'),
                            cancel_url=flask.url_for('.instrument', instrument_id=instrument_id),
                            instrument_log_category_themes=sorted(
                                InstrumentLogCategoryTheme,
                                key=lambda t: int(t.value)
                            ),
                            instrument_translations=instrument_translations,
                            instrument_language_ids=instrument_language_ids,
                            ENGLISH=ENGLISH,
                            instrument_log_categories=get_instrument_log_categories(instrument.id),
                            languages=get_languages(only_enabled_for_input=True),
                            instrument_form=instrument_form
                        )

                if len(name + description + short_description + notes) == 0:
                    continue

                if instrument_form.is_markdown.data:
                    description_as_html = markdown_to_safe_html(description, anchor_prefix='instrument-description')
                    mark_referenced_markdown_images_as_permanent(description_as_html)

                if instrument_form.short_description_is_markdown.data:
                    short_description_as_html = markdown_to_safe_html(short_description, anchor_prefix='instrument-short-description')
                    mark_referenced_markdown_images_as_permanent(short_description_as_html)
                if instrument_form.notes_is_markdown.data:
                    notes_as_html = markdown_to_safe_html(notes, anchor_prefix='instrument-notes')
                    mark_referenced_markdown_images_as_permanent(notes_as_html)

                new_translation = set_instrument_translation(
                    instrument_id=instrument.id,
                    language_id=language_id,
                    name=name,
                    description=description,
                    notes=notes,
                    short_description=short_description,
                )
                valid_translations.add((new_translation.instrument_id, new_translation.language_id))

            for translation in get_instrument_translations_for_instrument(instrument_id):
                if (translation.instrument_id, translation.language_id) not in valid_translations:
                    delete_instrument_translation(
                        instrument_id=translation.instrument_id,
                        language_id=translation.language_id
                    )

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
        flask.flash(_('The instrument was updated successfully.'), 'success')
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument.id))

    instrument_translations_list = get_instrument_translations_for_instrument(instrument.id)
    instrument_language_ids = [translation.language_id for translation in instrument_translations_list]
    instrument_translations = {
        instrument_translation.language_id: instrument_translation
        for instrument_translation in instrument_translations_list
    }
    english = get_language(Language.ENGLISH)
    return flask.render_template(
        'instruments/instrument_form.html',
        submit_text=_('Save'),
        cancel_url=flask.url_for('.instrument', instrument_id=instrument_id),
        instrument_log_category_themes=sorted(InstrumentLogCategoryTheme, key=lambda t: int(t.value)),
        instrument_translations=instrument_translations,
        instrument_language_ids=instrument_language_ids,
        ENGLISH=english,
        instrument_log_categories=get_instrument_log_categories(instrument.id),
        languages=get_languages(only_enabled_for_input=True),
        instrument_form=instrument_form,
        location_is_invalid=location_is_invalid
    )


@frontend.route('/instruments/<int:instrument_id>/log/<int:log_entry_id>/file_attachments/<int:file_attachment_id>')
@flask_login.login_required
def instrument_log_file_attachment(instrument_id: int, log_entry_id: int, file_attachment_id: int) -> FlaskResponseT:
    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        return flask.abort(404)
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
    return_preview = 'preview' in flask.request.args
    return_thumbnail = 'thumbnail' in flask.request.args

    if return_thumbnail:
        if file_attachment.image_info:
            return flask.Response(
                file_attachment.image_info.thumbnail_content,
                200,
                headers={
                    'Content-Type': file_attachment.image_info.thumbnail_mime_type
                }
            )
        else:
            return_preview = True
    if return_preview:
        file_extension = os.path.splitext(file_attachment.file_name)[1]
        mime_type = flask.current_app.config.get('MIME_TYPES', {}).get(file_extension, '')
        if mime_type:
            return flask.Response(
                file_attachment.content,
                200,
                headers={
                    'Content-Type': mime_type
                }
            )
    return flask.Response(
        file_attachment.content,
        200,
        headers={
            'Content-Disposition': f'attachment; filename="{file_attachment.file_name}"'
        }
    )


@frontend.route('/instruments/<int:instrument_id>/log/mobile_upload/<token>', methods=['GET'])
def instrument_log_mobile_file_upload(instrument_id: int, token: str) -> FlaskResponseT:
    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        return flask.abort(404)
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
def post_instrument_log_mobile_file_upload(instrument_id: int, token: str) -> FlaskResponseT:
    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        return flask.abort(404)
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
        log_entry = create_instrument_log_entry(
            instrument_id=instrument_id,
            user_id=user_id,
            content='',
            category_ids=[]
        )
        for file_storage in files:
            create_instrument_log_file_attachment(
                instrument_log_entry_id=log_entry.id,
                file_name=file_storage.filename or '',
                content=file_storage.stream.read()
            )
    return flask.render_template('mobile_upload_success.html')


@frontend.route('/users/me/settings/instrument_log_order', methods=['POST'])
@flask_login.login_required
def set_instrument_log_order() -> FlaskResponseT:
    form = InstrumentLogOrderForm()
    if not form.validate_on_submit():
        return flask.abort(400)
    ascending = form.ascending.data
    attribute = form.attribute.data
    set_user_settings(flask_login.current_user.id, {
        'INSTRUMENT_LOG_ORDER_ASCENDING': ascending,
        'INSTRUMENT_LOG_ORDER_ATTRIBUTE': attribute
    })
    return "", 200


@frontend.route('/instruments/<int:instrument_id>/link_object', methods=['GET', 'POST'])
@flask_login.login_required
def instrument_link_object(instrument_id: int) -> FlaskResponseT:
    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        return flask.abort(404)
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)

    is_instrument_responsible_user = any(
        responsible_user.id == flask_login.current_user.id
        for responsible_user in instrument.responsible_users
    )
    if not is_instrument_responsible_user:
        return flask.abort(403)
    check_current_user_is_not_readonly()
    object_link_form = ObjectLinkForm()
    if not object_link_form.validate_on_submit():
        flask.flash(_("Missing or invalid object ID."), 'error')
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
    object_id = object_link_form.object_id.data
    try:
        if Permissions.GRANT not in get_user_object_permissions(object_id, flask_login.current_user.id) and not flask_login.current_user.has_admin_permissions:
            flask.flash(_("You do not have GRANT permissions for this object."), 'error')
            return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
        object = get_object(object_id)
        object_is_valid = False
        if object.action_id is not None:
            action = get_action(object.action_id)
            if action.type_id is not None:
                action_type = get_action_type(action.type_id)
                object_is_valid = action_type.enable_instrument_link
        if not object_is_valid:
            flask.flash(_("This object cannot be linked to an instrument."), 'error')
            return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
        set_instrument_object(instrument_id, object_id)
    except ObjectDoesNotExistError:
        flask.flash(_("Object does not exist."), 'error')
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
    except InstrumentObjectLinkAlreadyExistsError:
        flask.flash(_("The instrument is already linked to an object or the object is already linked to an instrument."), 'error')
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
    flask.flash(_("Successfully linked the object to the instrument."), 'success')
    return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))


@frontend.route('/instruments/<int:instrument_id>/unlink_object', methods=['GET', 'POST'])
@flask_login.login_required
def instrument_unlink_object(instrument_id: int) -> FlaskResponseT:
    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        return flask.abort(404)
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)

    is_instrument_responsible_user = any(
        responsible_user.id == flask_login.current_user.id
        for responsible_user in instrument.responsible_users
    )
    if not is_instrument_responsible_user:
        return flask.abort(403)
    check_current_user_is_not_readonly()
    object_link_form = ObjectLinkForm()
    if not object_link_form.validate_on_submit():
        flask.flash(_("Missing or invalid object ID."), 'error')
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
    object_id = object_link_form.object_id.data
    if instrument.object_id != object_id:
        flask.flash(_('This instrument is not linked to this object.'), 'error')
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
    set_instrument_object(instrument_id=instrument_id, object_id=None)
    flask.flash(_("Successfully unlinked the object from the instrument."), 'success')
    return flask.redirect(flask.url_for('.instrument', instrument_id=instrument_id))
