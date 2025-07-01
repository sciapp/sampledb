# coding: utf-8
"""

"""
import copy
import json
import typing

import flask
import flask_login
import werkzeug
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SelectField, IntegerField, SelectMultipleField
from wtforms.validators import InputRequired, ValidationError, DataRequired
from flask_babel import _, force_locale

from . import frontend
from .permission_forms import handle_permission_forms, set_up_permissions_forms
from .. import models
from ..logic.action_permissions import get_action_permissions_for_all_users, get_user_action_permissions, set_action_permissions_for_all_users, get_action_permissions_for_groups, get_action_permissions_for_projects, get_action_permissions_for_users, get_sorted_actions_for_user
from ..logic.actions import Action, create_action, get_action, update_action
from ..logic.action_types import get_action_type, get_action_types
from ..logic.action_translations import get_action_translations_for_action, set_action_translation, delete_action_translation
from ..logic.languages import get_languages, get_language, Language
from ..logic.components import get_component
from ..logic.favorites import get_user_favorite_action_ids, get_user_favorite_instrument_ids
from ..logic.instruments import get_user_instruments, get_instrument
from ..logic.markdown_images import mark_referenced_markdown_images_as_permanent
from ..logic import errors, users
from ..logic.schemas.validate_schema import validate_schema
from ..logic.schemas.templates import reverse_substitute_templates, find_invalid_template_paths
from ..logic.settings import get_user_setting, set_user_settings, get_user_settings
from ..logic.topics import get_topics, get_topic, set_action_topics
from ..logic.users import get_users, get_user
from ..logic.groups import get_group
from ..logic.projects import get_project
from .users.forms import ToggleFavoriteActionForm
from .utils import check_current_user_is_not_readonly, get_groups_form_data, parse_filter_id_params, build_modified_url
from ..utils import FlaskResponseT
from ..logic.markdown_to_html import markdown_to_safe_html
from ..logic.utils import get_translated_text
from .. import logic, babel
from ..models import Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

ACTION_LIST_FILTER_PARAMETERS = (
    'action_list_filters',
    'topic_ids'
)


class ActionForm(FlaskForm):
    type = IntegerField()
    instrument = SelectField()
    topics = SelectMultipleField()
    schema = StringField(validators=[InputRequired()])
    is_public = BooleanField()
    is_user_specific = BooleanField(default=True)
    is_markdown = BooleanField(default=None)
    is_hidden = BooleanField(default=None)
    short_description_is_markdown = BooleanField(default=None)
    translations = StringField(validators=[DataRequired()])
    usable_by = SelectField(choices=['with_permissions', 'admins', 'nobody'])
    objects_readable_by_all_users_by_default = BooleanField(default=None)
    use_json_editor = BooleanField(default=None)
    use_instrument_topics = BooleanField(default=None)

    def validate_type(form, field: IntegerField) -> None:
        try:
            action_type_id = int(field.data)
        except ValueError:
            raise ValidationError(_("Invalid action type"))
        try:
            action_type = get_action_type(action_type_id)
        except errors.ActionTypeDoesNotExistError:
            raise ValidationError(_("Unknown action type"))
        if action_type.admin_only and not flask_login.current_user.is_admin:
            raise ValidationError(_("Actions with this type can only be created or edited by administrators."))


def _parse_action_list_filters(
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


@frontend.route('/actions/')
@flask_login.login_required
def actions() -> FlaskResponseT:
    action_type_id_str = flask.request.args.get('t', None)
    action_type = None

    user_is_instrument_scientist = bool(get_user_instruments(flask_login.current_user.id, exclude_hidden=True))

    action_type_id: typing.Optional[int]
    if action_type_id_str is not None:
        try:
            action_type_id = int(action_type_id_str)
        except ValueError:
            # ensure old links still function
            action_type_id = {
                'samples': models.ActionType.SAMPLE_CREATION,
                'measurements': models.ActionType.MEASUREMENT,
                'simulations': models.ActionType.SIMULATION
            }.get(action_type_id_str)
        if action_type_id is not None:
            try:
                action_type = get_action_type(
                    action_type_id=action_type_id
                )
            except errors.ActionTypeDoesNotExistError:
                # fall back to all objects
                action_type_id = None
    else:
        action_type_id = None
    user_id_str = flask.request.args.get('user_id', None)
    if user_id_str is not None:
        try:
            user_id = int(user_id_str)
        except ValueError:
            user_id = None
            flask.flash(_('Invalid user ID.'), 'error')
    else:
        user_id = None
    if user_id is not None:
        try:
            users.check_user_exists(user_id)
        except errors.UserDoesNotExistError:
            user_id = None
            flask.flash(_('Invalid user ID.'), 'error')
    actions = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id,
        action_type_id=action_type_id,
        owner_id=user_id,
    )
    if action_type_id is None:
        # exclude actions of types that generally do not allow creating objects
        actions = [
            action
            for action in actions
            if action.schema is not None and action.type is not None and not action.type.disable_create_objects
        ]
    filter_usable_actions = 'can_create_objects' in flask.request.args
    if filter_usable_actions:
        # exclude actions that cannot be used to create objects by the current user
        actions = [
            action
            for action in actions
            if action.schema is not None and action.type is not None and not action.type.disable_create_objects and not action.disable_create_objects and not (action.admin_only and not flask_login.current_user.is_admin)
        ]

    topics = get_topics()
    valid_topic_ids = [topic.id for topic in topics]

    if 'action_list_filters' in flask.request.args or any(any(flask.request.args.getlist(param)) for param in ACTION_LIST_FILTER_PARAMETERS):
        (
            success,
            filter_topic_ids,
        ) = _parse_action_list_filters(
            params=flask.request.args,
            valid_topic_ids=valid_topic_ids
        )
        if not success:
            return flask.abort(400)
    else:
        filter_topic_ids = get_user_settings(user_id=flask_login.current_user.id)['DEFAULT_ACTION_LIST_FILTERS'].get('filter_topic_ids', [])

    if filter_topic_ids is None:
        filter_topic_ids = []

    if filter_topic_ids:
        actions = [
            action
            for action in actions
            if any(topic in [topic.id for topic in action.topics] for topic in filter_topic_ids)
        ]

    filter_topic_infos = []
    if filter_topic_ids:
        for topic_id in filter_topic_ids:
            topic = get_topic(topic_id)
            filter_topic_infos.append({
                'name': get_translated_text(topic.name, default=_('Unnamed Topic')),
                'url': flask.url_for('.topic', topic_id=topic_id)
            })

    user_favorite_action_ids = get_user_favorite_action_ids(flask_login.current_user.id)
    toggle_favorite_action_form = ToggleFavoriteActionForm()
    return flask.render_template(
        'actions/actions.html',
        actions=actions,
        action_type=action_type,
        action_permissions=action_permissions,
        user_is_instrument_scientist=user_is_instrument_scientist,
        Permissions=Permissions,
        user_favorite_action_ids=user_favorite_action_ids,
        toggle_favorite_action_form=toggle_favorite_action_form,
        get_user=get_user,
        get_component=get_component,
        topics=topics,
        filter_topic_infos=filter_topic_infos,
        filter_topic_ids=filter_topic_ids
    )


@frontend.route('/actions/', methods=['POST'])
@flask_login.login_required
def save_action_list_defaults() -> FlaskResponseT:
    if 'save_default_action_filters' in flask.request.form:
        topics = get_topics()
        valid_topic_ids = [topic.id for topic in topics]
        success, filter_topic_ids = _parse_action_list_filters(
            params=flask.request.form,
            valid_topic_ids=valid_topic_ids
        )
        if not success:
            return flask.abort(400)
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_ACTION_LIST_FILTERS': {
                    'filter_topic_ids': filter_topic_ids,
                }
            }
        )
        return flask.redirect(build_modified_url('.actions', blocked_parameters=ACTION_LIST_FILTER_PARAMETERS))
    if 'clear_default_action_filters' in flask.request.form:
        set_user_settings(
            user_id=flask_login.current_user.id,
            data={
                'DEFAULT_ACTION_LIST_FILTERS': {}
            }
        )
        return flask.redirect(build_modified_url('.actions', blocked_parameters=ACTION_LIST_FILTER_PARAMETERS))
    return flask.abort(400)


@frontend.route('/actions/<int:action_id>', methods=['GET', 'POST'])
@flask_login.login_required
def action(action_id: int) -> FlaskResponseT:
    try:
        action = get_action(action_id)
    except errors.ActionDoesNotExistError:
        return flask.abort(404)
    permissions = get_user_action_permissions(action_id, flask_login.current_user.id)
    if Permissions.READ not in permissions:
        return flask.abort(403)
    may_edit = Permissions.WRITE in permissions and action.fed_id is None

    if action.type is not None and action.type.admin_only and not flask_login.current_user.is_admin:
        may_edit = False
    may_grant = Permissions.GRANT in permissions
    mode = flask.request.args.get('mode', None)
    if mode == 'edit':
        action_schema = action.schema
        if action_schema:
            original_schema = copy.deepcopy(action_schema)
            try:
                reverse_substitute_templates(action_schema)
            except errors.ActionDoesNotExistError:
                action_schema = original_schema
                flask.flash(_('The used template does not exist anymore. Use the JSON editor to edit the existing action.'), 'error')
                if get_user_setting(flask_login.current_user.id, "USE_SCHEMA_EDITOR"):
                    flask.abort(400)
        check_current_user_is_not_readonly()
        if not may_edit:
            if action.fed_id is not None:
                flask.flash(_('Editing imported actions is not yet supported.'), 'error')
            return flask.abort(403)
        return show_action_form(action, action_schema=action_schema)

    action_is_favorite = action.id in get_user_favorite_action_ids(flask_login.current_user.id)
    return flask.render_template(
        'actions/action.html',
        action=action,
        action_is_favorite=action_is_favorite,
        may_edit=may_edit,
        may_grant=may_grant,
        is_public=Permissions.READ in get_action_permissions_for_all_users(action_id),
        get_user=get_user,
        get_component=get_component
    )


@frontend.route('/actions/new/', methods=['GET', 'POST'])
@flask_login.login_required
def new_action() -> FlaskResponseT:
    check_current_user_is_not_readonly()
    action_type_id_str = flask.request.args.get('action_type_id')
    if action_type_id_str is not None:
        try:
            action_type_id = int(action_type_id_str)
        except ValueError:
            action_type_id = None
    else:
        action_type_id = None
    topic_ids_str = flask.request.args.get('topic_ids')
    if topic_ids_str is not None:
        try:
            topic_ids = [int(topic_id_str) for topic_id_str in topic_ids_str.split(',')]
        except ValueError:
            topic_ids = None
    else:
        topic_ids = None
    instrument_id_str = flask.request.args.get('instrument_id', None)
    if instrument_id_str is not None:
        try:
            instrument_id = int(instrument_id_str)
        except ValueError:
            instrument_id = None
    else:
        instrument_id = None
    if instrument_id:
        try:
            user_instrument_ids = get_user_instruments(flask_login.current_user.id, exclude_hidden=True)
            if instrument_id in user_instrument_ids:
                instrument = get_instrument(instrument_id)
                if instrument.component_id is not None:
                    flask.flash(_('Using imported instruments to create actions is not supported.'), 'error')
                    instrument_id = None
            else:
                flask.flash(_('Insufficient permissions to use the requested instrument.'), 'error')
                instrument_id = None
        except errors.InstrumentDoesNotExistError:
            flask.flash(_('The requested instrument does not exist.'), 'error')
    previous_action = None
    previous_action_id_str = flask.request.args.get('previous_action_id', None)
    if previous_action_id_str is not None:
        try:
            previous_action_id = int(previous_action_id_str)
        except ValueError:
            previous_action_id = None
    else:
        previous_action_id = None
    if previous_action_id:
        try:
            permissions = get_user_action_permissions(previous_action_id, flask_login.current_user.id)
            if Permissions.READ in permissions:
                previous_action = get_action(previous_action_id)
            else:
                flask.flash(_('Insufficient permissions to use the requested action as a template.'), 'error')
                previous_action = None
        except errors.ActionDoesNotExistError:
            flask.flash(_('The requested action does not exist.'), 'error')
        else:
            if previous_action is not None:
                if previous_action.type is None or previous_action.schema is None:
                    previous_action = None
                elif previous_action.type.admin_only and not flask_login.current_user.is_admin:
                    flask.flash(_('Only administrators can create actions of this type.'), 'error')
                    return flask.redirect(flask.url_for('.action', action_id=previous_action_id))
    return show_action_form(None, previous_action, action_type_id, topic_ids=topic_ids, instrument_id=instrument_id)


def _get_lines_for_path(schema: typing.Dict[str, typing.Any], path: typing.List[str]) -> typing.Optional[typing.Set[int]]:
    schema_entry = schema
    parent = None
    key = None
    for property in path:
        if property == '[?]' and 'items' in schema_entry and isinstance(schema_entry['items'], dict):
            parent = schema_entry
            key = 'items'
            if parent is not None and key in parent:
                schema_entry = parent[key]
            else:
                return None
        elif 'properties' in schema_entry and property in schema_entry['properties'] and isinstance(schema_entry['properties'][property], dict):
            parent = schema_entry['properties']
            key = property
            if parent is not None and key in parent:
                schema_entry = parent[key]
            else:
                return None
        else:
            break
    if parent is None or key is None:
        return None

    parent[key] = {"INTERNAL_MARKER_START": None, "INTERNAL_MARKER_CONTENT": parent[key], "INTERNAL_MARKER_END": None}

    schema_json = json.dumps(schema, indent=2)
    in_error = False
    error_lines = []
    skip_lines = []
    schema_json_lines = schema_json.splitlines(keepends=False)
    for i, line in enumerate(schema_json_lines):
        if line.endswith('"INTERNAL_MARKER_START": null,'):
            skip_lines.append(i)
            skip_lines.append(i + 1)
            in_error = True
        if in_error:
            error_lines.append(i)
        if line.endswith('"INTERNAL_MARKER_END": null'):
            skip_lines.append(i - 1)
            skip_lines.append(i)
            in_error = False

    new_error_lines: typing.Set[int] = set()
    for i in reversed(error_lines):
        if i in skip_lines:
            new_error_lines = {i - 1 for i in new_error_lines}
        else:
            new_error_lines.add(i + 1)
            new_error_lines.add(i)
            new_error_lines.add(i - 1)
    return new_error_lines


def show_action_form(
        action: typing.Optional[Action] = None,
        previous_action: typing.Optional[Action] = None,
        action_type_id: typing.Optional[int] = None,
        action_schema: typing.Optional[typing.Dict[str, typing.Any]] = None,
        topic_ids: typing.Optional[typing.List[int]] = None,
        instrument_id: typing.Optional[int] = None,
) -> FlaskResponseT:
    action_translations = []
    load_translations = False

    languages = get_languages(only_enabled_for_input=True)
    allowed_language_ids = [
        language.id
        for language in languages
    ]
    tags_translations = {}
    hazards_translations = {}
    translation_lang_codes = [locale.language for locale in babel.list_translations()]
    for language in languages:
        if language.lang_code in translation_lang_codes:
            with force_locale(language.lang_code):
                tags_translations[language.lang_code] = _('Tags')
                hazards_translations[language.lang_code] = _('GHS Hazards')

    topics = get_topics()

    if action is not None:
        action_translations = get_action_translations_for_action(action.id, use_fallback=True)
        load_translations = True
        schema_json = json.dumps(action_schema, indent=2)
        submit_text = "Save"
    elif previous_action is not None:
        action_translations = get_action_translations_for_action(previous_action.id, use_fallback=True)
        load_translations = True
        schema_json = json.dumps(previous_action.schema, indent=2)
        submit_text = "Create"
    else:
        schema_json = json.dumps({
            'title': {
                'en': 'Object Information'
            },
            'type': 'object',
            'properties': {
                'name': {
                    'title': {
                        'en': 'Name'
                    },
                    'type': 'text'
                }
            },
            'required': ['name'],
            'propertyOrder': [
                'name'
            ]
        }, indent=2)
        submit_text = "Create"
    may_set_user_specific = action is None and flask_login.current_user.is_admin
    schema = None
    error_message = None
    action_form = ActionForm()
    instrument_is_fed = {}
    instrument_is_fav = {}

    sample_action_type = get_action_type(
        action_type_id=models.ActionType.SAMPLE_CREATION
    )
    measurement_action_type = get_action_type(
        action_type_id=models.ActionType.MEASUREMENT
    )
    english = get_language(Language.ENGLISH)
    action_language_ids = [translation.language_id for translation in action_translations]
    action_translations_by_id = {
        action_translation.language_id: action_translation
        for action_translation in action_translations
    }
    user_favorite_instrument_ids = get_user_favorite_instrument_ids(flask_login.current_user.id)
    action_form.topics.choices = [
        (str(topic.id), get_translated_text(topic.name))
        for topic in topics
    ]
    if not action_form.is_submitted():
        action_form.use_json_editor.data = get_user_setting(flask_login.current_user.id, "USE_SCHEMA_EDITOR")
        action_form.topics.data = []
    if action is not None:
        if action.instrument is not None:
            action_form.instrument.choices = [
                (str(action.instrument_id), get_translated_text(action.instrument.name, default=_('Unnamed Instrument')))
            ]
            instrument_is_fed[str(action.instrument_id)] = action.instrument.component_id is not None
            instrument_is_fav[str(action.instrument_id)] = action.instrument_id in user_favorite_instrument_ids
            action_form.instrument.data = str(action.instrument_id)
        else:
            action_form.instrument.choices = [('-1', '-')]
            action_form.instrument.data = str(-1)
        action_form.type.data = action.type_id
    else:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            action_form.instrument.choices = [('-1', '-')]
            action_form.instrument.data = '-1'
        else:
            user_instrument_ids = get_user_instruments(flask_login.current_user.id, exclude_hidden=True)
            for user_instrument_id in user_instrument_ids:
                instrument_is_fed[str(user_instrument_id)] = get_instrument(user_instrument_id).component_id is not None
                instrument_is_fav[str(user_instrument_id)] = user_instrument_id in user_favorite_instrument_ids
            user_instruments = [
                (str(instrument_id), get_translated_text(get_instrument(instrument_id).name, default=_('Unnamed Instrument')))
                for instrument_id in user_instrument_ids
            ]
            user_instruments.sort(key=lambda instrument_data: (
                not instrument_is_fav[instrument_data[0]],
                instrument_data[1]
            ))
            action_form.instrument.choices = [('-1', '-')] + user_instruments
            if action_form.instrument.data is None or action_form.instrument.data == str(None):
                if previous_action is not None and previous_action.instrument_id in user_instrument_ids:
                    action_form.instrument.data = str(previous_action.instrument_id)
                elif instrument_id is not None:
                    action_form.instrument.data = str(instrument_id)
                else:
                    action_form.instrument.data = '-1'
    form_is_valid = False
    if not action_form.is_submitted():
        action_form.type.data = action_type_id
        if topic_ids and not flask.current_app.config['DISABLE_TOPICS']:
            action_form.topics.data = [str(topic_id) for topic_id in topic_ids]
        else:
            action_form.topics.data = []
    elif action_form.validate_on_submit():
        form_is_valid = True
        action_type_id = action_form.type.data
    else:
        action_type_id = None
    if action_type_id is None:
        form_is_valid = False

    if not action_form.is_submitted():
        if action is not None:
            action_form.is_hidden.data = action.is_hidden
            action_form.is_markdown.data = action.description_is_markdown
            action_form.short_description_is_markdown.data = action.short_description_is_markdown
            action_form.type.data = action.type_id
            action_form.is_public.data = Permissions.READ in get_action_permissions_for_all_users(action.id)
            if action.disable_create_objects:
                action_form.usable_by.data = 'nobody'
            elif action.admin_only:
                action_form.usable_by.data = 'admins'
            else:
                action_form.usable_by.data = 'with_permissions'
            action_form.objects_readable_by_all_users_by_default.data = action.objects_readable_by_all_users_by_default
            action_form.topics.data = [str(topic.id) for topic in action.topics]
            action_form.use_instrument_topics.data = action.use_instrument_topics
        elif previous_action is not None:
            action_form.is_hidden.data = False
            action_form.is_markdown.data = previous_action.description_is_markdown
            action_form.short_description_is_markdown.data = previous_action.short_description_is_markdown
            action_form.type.data = previous_action.type_id
            action_form.is_public.data = Permissions.READ in get_action_permissions_for_all_users(previous_action.id)
            action_form.usable_by.data = 'with_permissions'
            action_form.objects_readable_by_all_users_by_default.data = previous_action.objects_readable_by_all_users_by_default
            action_form.topics.data = [str(topic.id) for topic in previous_action.topics]
            action_form.use_instrument_topics.data = False
            if not action_form.topics.data and previous_action.topics:
                action_form.topics.data = [str(topic.id) for topic in previous_action.topics]
        if flask.current_app.config['DISABLE_TOPICS']:
            action_form.topics.choices = []
            action_form.topics.data = []

    if action_form.schema.data:
        schema_json = action_form.schema.data
    else:
        action_form.schema.data = schema_json
    error_lines = None
    if schema_json:
        all_lines = set(range(1, 1 + len(schema_json.splitlines())))
        error_lines = set()
        if 'INTERNAL_MARKER' in schema_json:
            error_lines = all_lines
            error_message = "Failed to parse schema: Must not contain INTERNAL_MARKER"
        else:
            try:
                schema = json.loads(schema_json)
            except json.JSONDecodeError as e:
                error_lines = {e.lineno}
                error_message = f"Failed to parse as JSON: {e.msg}"
            except Exception as e:
                error_lines = all_lines
                error_message = f"Failed to parse as JSON: {str(e)}"
        if schema is not None:
            try:
                invalid_template_paths = find_invalid_template_paths(schema, flask_login.current_user.id)
                if invalid_template_paths:
                    raise errors.ValidationError('insufficient permissions for template action', invalid_template_paths[0])
                validate_schema(schema, invalid_template_action_ids=[] if action is None else [action.id], strict=True)
            except errors.ValidationError as e:
                error_message = e.message
                if not e.paths:
                    error_lines = all_lines
                else:
                    schema_json = json.dumps(schema, indent=2)
                    action_form.schema.data = schema_json
                    for path in e.paths:
                        new_error_lines = _get_lines_for_path(schema, path)
                        if new_error_lines is None:
                            error_lines = all_lines
                            break
                        else:
                            error_lines.update(new_error_lines)
                    else:
                        error_lines = {i + 1 for i in error_lines}
            except Exception as e:
                error_lines = all_lines
                error_message = _("Unknown error: ") + str(e)
    if schema is not None and error_message is None and form_is_valid:
        # First block for validation
        try:
            translation_data = json.loads(action_form.translations.data)
        except Exception:
            flask.flash(_("Something went wrong"), 'error')
            return flask.render_template(
                'actions/action_form.html',
                current_action=action,
                action_form=action_form,
                action_translations=action_translations_by_id,
                action_language_ids=action_language_ids,
                action_types=get_action_types(),
                error_message=error_message,
                schema_json=schema_json,
                submit_text=submit_text,
                sample_action_type=sample_action_type,
                measurement_action_type=measurement_action_type,
                may_change_type=action is None,
                may_change_instrument=action is None,
                may_set_user_specific=may_set_user_specific,
                languages=languages,
                tags_translations=tags_translations,
                hazards_translations=hazards_translations,
                load_translations=load_translations,
                ENGLISH=english,
                instrument_is_fed=instrument_is_fed,
                instrument_is_fav=instrument_is_fav,
                error_lines=list(error_lines or []),
            )
        else:
            translation_keys = {'language_id', 'name', 'description', 'short_description'}

            if not isinstance(translation_data, list):
                translation_data = ()

            for translation in translation_data:
                if not isinstance(translation, dict):
                    continue
                if set(translation.keys()) != translation_keys:
                    continue

                language_id = int(translation['language_id'])
                name = translation['name'].strip()
                description = translation['description'].strip()
                short_description = translation['short_description'].strip()

                if language_id == Language.ENGLISH:
                    error = False
                    if not isinstance(name, str) or not isinstance(description, str) \
                            or not isinstance(short_description, str):
                        flask.flash(_('Please input a name.'))
                        error = True
                    if len(name) < 1 or len(name) > 100:
                        error = True
                        flask.flash(_('Please input a name with a length between 1 and 100.'))
                    if error:
                        return flask.render_template(
                            'actions/action_form.html',
                            current_action=action,
                            action_form=action_form,
                            action_translations=action_translations_by_id,
                            action_language_ids=action_language_ids,
                            action_types=get_action_types(),
                            error_message=error_message,
                            schema_json=schema_json,
                            submit_text=submit_text,
                            sample_action_type=sample_action_type,
                            measurement_action_type=measurement_action_type,
                            may_change_type=action is None,
                            may_change_instrument=action is None,
                            may_set_user_specific=may_set_user_specific,
                            languages=languages,
                            tags_translations=tags_translations,
                            hazards_translations=hazards_translations,
                            load_translations=load_translations,
                            ENGLISH=english,
                            instrument_is_fed=instrument_is_fed,
                            instrument_is_fav=instrument_is_fav,
                            error_lines=list(error_lines or []),
                        )
        instrument_id_str = action_form.instrument.data
        topic_id_strs = action_form.topics.data
        is_public = action_form.is_public.data
        is_hidden = action_form.is_hidden.data
        is_markdown = action_form.is_markdown.data
        short_description_is_markdown = action_form.short_description_is_markdown.data
        admin_only = action_form.usable_by.data == 'admins'
        disable_create_objects = action_form.usable_by.data == 'nobody'
        objects_readable_by_all_users_by_default = action_form.objects_readable_by_all_users_by_default.data
        use_instrument_topics = action_form.use_instrument_topics.data

        if instrument_id_str is not None:
            try:
                instrument_id = int(instrument_id_str)
            except ValueError:
                instrument_id = None
            if instrument_id is not None and instrument_id < 0:
                instrument_id = None
        else:
            instrument_id = None

        try:
            topic_ids = [int(topic_id_str) for topic_id_str in topic_id_strs]
        except ValueError:
            topic_ids = []

        assert action_type_id is not None  # mypy does not infer this, but it is guaranteed by the code above
        if action is None:
            if action_form.is_user_specific.data or not may_set_user_specific:
                user_id = flask_login.current_user.id
            else:
                user_id = None
            action = create_action(
                action_type_id=action_type_id,
                schema=schema,
                instrument_id=instrument_id,
                user_id=user_id,
                is_hidden=is_hidden,
                description_is_markdown=is_markdown,
                short_description_is_markdown=short_description_is_markdown,
                admin_only=admin_only,
                disable_create_objects=disable_create_objects,
                objects_readable_by_all_users_by_default=objects_readable_by_all_users_by_default,
                use_instrument_topics=use_instrument_topics if instrument_id is not None else False
            )
        else:
            update_action(
                action_id=action.id,
                schema=schema,
                is_hidden=is_hidden,
                description_is_markdown=is_markdown,
                short_description_is_markdown=short_description_is_markdown,
                admin_only=admin_only,
                disable_create_objects=disable_create_objects,
                objects_readable_by_all_users_by_default=objects_readable_by_all_users_by_default,
                use_instrument_topics=use_instrument_topics if action.instrument_id is not None else False
            )
        if action.instrument_id is None or not use_instrument_topics:
            set_action_topics(action.id, topic_ids)
        set_action_permissions_for_all_users(action.id, Permissions.READ if is_public else Permissions.NONE)

        # After validation
        valid_translations = set()
        for translation in translation_data:
            if not isinstance(translation, dict):
                continue
            if set(translation.keys()) != translation_keys:
                continue

            language_id = int(translation['language_id'])
            name = translation['name'].strip()
            description = translation['description'].strip()
            short_description = translation['short_description'].strip()

            if language_id not in allowed_language_ids:
                continue

            if is_markdown:
                description_as_html = markdown_to_safe_html(description, anchor_prefix="instrument-description")
                mark_referenced_markdown_images_as_permanent(description_as_html)
            if short_description_is_markdown:
                short_description_as_html = markdown_to_safe_html(short_description,
                                                                  anchor_prefix="instrument-short-description")
                mark_referenced_markdown_images_as_permanent(short_description_as_html)

            new_translation = set_action_translation(
                language_id=language_id,
                action_id=action.id,
                name=name,
                description=description,
                short_description=short_description)
            valid_translations.add((new_translation.language_id, new_translation.action_id))

        for existing_translations in get_action_translations_for_action(action.id):
            if (existing_translations.language_id, existing_translations.action_id) not in valid_translations:
                delete_action_translation(
                    language_id=existing_translations.language_id,
                    action_id=existing_translations.action_id
                )

        flask.flash(_('The action was updated successfully.'), 'success')
        return flask.redirect(flask.url_for('.action', action_id=action.id))
    if action_form.translations.name in flask.request.form:
        # load translations from form
        try:
            translation_data = json.loads(action_form.translations.data)
            for translation in translation_data:
                translation['language_id'] = int(translation['language_id'])
                translation['language'] = get_language(translation['language_id'])
                action_translations_by_id[translation['language_id']] = translation
                if translation['language_id'] not in action_translations_by_id:
                    action_language_ids.append(translation['language_id'])
            if action_language_ids:
                load_translations = True
        except Exception:
            pass
    return flask.render_template(
        'actions/action_form.html',
        current_action=action,
        action_form=action_form,
        action_translations=action_translations_by_id,
        action_language_ids=action_language_ids,
        action_types=get_action_types(),
        error_message=error_message,
        schema_json=schema_json,
        submit_text=submit_text,
        sample_action_type=sample_action_type,
        measurement_action_type=measurement_action_type,
        may_change_type=action is None,
        may_change_instrument=action is None,
        may_set_user_specific=may_set_user_specific,
        languages=languages,
        tags_translations=tags_translations,
        hazards_translations=hazards_translations,
        load_translations=load_translations,
        ENGLISH=english,
        instrument_is_fed=instrument_is_fed,
        instrument_is_fav=instrument_is_fav,
        error_lines=list(error_lines or []),
    )


@frontend.route('/actions/<int:action_id>/permissions', methods=['GET', 'POST'])
@flask_login.login_required
def action_permissions(action_id: int) -> FlaskResponseT:
    try:
        action = get_action(action_id)
    except errors.ActionDoesNotExistError:
        return flask.abort(404)
    permissions = get_user_action_permissions(action_id, flask_login.current_user.id)
    if Permissions.READ not in permissions:
        return flask.abort(403)
    user_may_edit = Permissions.GRANT in permissions
    all_user_permissions = get_action_permissions_for_all_users(action_id=action.id)
    anonymous_user_permissions = Permissions.NONE
    user_permissions = get_action_permissions_for_users(
        action_id=action.id
    )
    if action.user_id is not None:
        # action owner has implicit GRANT permissions
        action_owner = get_user(action.user_id)
        if action_owner.is_readonly:
            user_permissions[action_owner.id] = Permissions.READ
        else:
            user_permissions[action_owner.id] = Permissions.GRANT
    group_permissions = get_action_permissions_for_groups(
        action_id=action.id
    )
    project_permissions = get_action_permissions_for_projects(
        action_id=action.id
    )
    if user_may_edit:
        (
            add_user_permissions_form,
            add_group_permissions_form,
            add_project_permissions_form,
            permissions_form
        ) = set_up_permissions_forms(
            resource_permissions=logic.action_permissions.action_permissions,
            resource_id=action_id,
            existing_all_user_permissions=all_user_permissions,
            existing_anonymous_user_permissions=anonymous_user_permissions,
            existing_user_permissions=user_permissions,
            existing_group_permissions=group_permissions,
            existing_project_permissions=project_permissions
        )

        users = get_users(exclude_hidden=not flask_login.current_user.is_admin or not flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN'], exclude_fed=True, exclude_eln_import=True)
        users = [user for user in users if user.id not in user_permissions]
        users.sort(key=lambda user: user.id)

        show_groups_form, groups_treepicker_info = get_groups_form_data(
            basic_group_filter=lambda group: group.id not in group_permissions
        )

        show_projects_form, projects_treepicker_info = get_groups_form_data(
            project_group_filter=lambda group: group.id not in project_permissions
        )
        if flask.request.method.lower() == 'post':
            if handle_permission_forms(
                    logic.action_permissions.action_permissions,
                    action_id,
                    add_user_permissions_form,
                    add_group_permissions_form,
                    add_project_permissions_form,
                    permissions_form,
                    user_permissions,
                    group_permissions,
                    project_permissions,
            ):
                flask.flash(_('Successfully updated action permissions.'), 'success')
            else:
                flask.flash(_('Failed to update action permissions.'), 'error')
            return flask.redirect(flask.url_for('.action_permissions', action_id=action_id))
    else:
        permissions_form = None
        users = None
        add_user_permissions_form = None
        add_group_permissions_form = None
        add_project_permissions_form = None
        show_groups_form = False
        groups_treepicker_info = None
        show_projects_form = False
        projects_treepicker_info = None
        if flask.request.method.lower() == 'post':
            flask.flash(_('You need GRANT permissions to edit the permissions for this action.'), 'error')
            return flask.redirect(flask.url_for('.action_permissions', action_id=action_id))

    return flask.render_template(
        'actions/action_permissions.html',
        user_may_edit=user_may_edit,
        action=action,
        instrument=action.instrument,
        Permissions=Permissions,
        project_permissions=project_permissions,
        group_permissions=group_permissions,
        user_permissions=user_permissions,
        all_user_permissions=all_user_permissions,
        permissions_form=permissions_form,
        users=users,
        add_user_permissions_form=add_user_permissions_form,
        add_group_permissions_form=add_group_permissions_form,
        add_project_permissions_form=add_project_permissions_form,
        show_groups_form=show_groups_form,
        groups_treepicker_info=groups_treepicker_info,
        show_projects_form=show_projects_form,
        projects_treepicker_info=projects_treepicker_info,
        get_user=get_user,
        get_group=get_group,
        get_project=get_project,
    )
