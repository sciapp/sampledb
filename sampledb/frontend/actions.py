# coding: utf-8
"""

"""

import json
import typing

import flask
import flask_login
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SelectField, IntegerField, FieldList, FormField
from wtforms.validators import InputRequired, ValidationError, DataRequired
import pygments
import pygments.lexers.data
import pygments.formatters

from . import frontend
from .. import models
from ..logic.action_permissions import Permissions, action_is_public, get_user_action_permissions, set_action_public, get_action_permissions_for_groups, get_action_permissions_for_projects, get_action_permissions_for_users, set_project_action_permissions, set_group_action_permissions, set_user_action_permissions, get_sorted_actions_for_user
from ..logic.actions import Action, create_action, get_action, update_action, get_action_type
from ..logic.action_translations import get_action_translations_for_action, set_action_translation, delete_action_translation, get_action_translation_for_action_in_language
from ..logic.action_type_translations import get_action_type_translation_for_action_type_in_language, \
    get_action_types_with_translations_in_language, get_action_type_with_translation_in_language

from ..logic.languages import get_languages, get_language, Language
from ..logic.favorites import get_user_favorite_action_ids
from ..logic.instruments import get_user_instruments
from ..logic.instrument_translations import get_instrument_translation_for_instrument_in_language
from ..logic.markdown_images import mark_referenced_markdown_images_as_permanent
from ..logic import errors, users, languages
from ..logic.schemas.validate_schema import validate_schema
from ..logic.settings import get_user_settings
from ..logic.users import get_users, get_user
from ..logic.groups import get_groups, get_group
from ..logic.projects import get_projects, get_project, get_project_id_hierarchy_list
from .users.forms import ToggleFavoriteActionForm
from .utils import check_current_user_is_not_readonly
from ..logic.markdown_to_html import markdown_to_safe_html
from flask_babel import _

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class ActionForm(FlaskForm):
    type = IntegerField()
    instrument = SelectField()
    schema = StringField(validators=[InputRequired()])
    is_public = BooleanField()
    is_user_specific = BooleanField(default=True)
    is_markdown = BooleanField(default=None)
    is_hidden = BooleanField(default=None)
    short_description_is_markdown = BooleanField(default=None)
    translations = StringField(validators=[DataRequired()])

    def validate_type(form, field):
        try:
            action_type_id = int(field.data)
        except ValueError:
            raise ValidationError(_("Invalid action type"))
        try:
            action_type = get_action_type(action_type_id)
        except errors.ActionTypeDoesNotExistError:
            raise ValidationError(_("Unknown action type"))
        if action_type.admin_only and not flask_login.current_user.is_admin:
            raise ValidationError(_("Actions with this type can only be created or edited by administrators"))


class ActionUserPermissionsForm(FlaskForm):
    user_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ActionGroupPermissionsForm(FlaskForm):
    group_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ActionProjectPermissionsForm(FlaskForm):
    project_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ActionPermissionsForm(FlaskForm):
    public_permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ)],
        validators=[InputRequired()]
    )
    user_permissions = FieldList(FormField(ActionUserPermissionsForm), min_entries=0)
    group_permissions = FieldList(FormField(ActionGroupPermissionsForm), min_entries=0)
    project_permissions = FieldList(FormField(ActionProjectPermissionsForm), min_entries=0)


@frontend.route('/actions/')
@flask_login.login_required
def actions():
    action_type_id = flask.request.args.get('t', None)
    action_type = None
    user_language_id = languages.get_user_language(flask_login.current_user).id

    if action_type_id is not None:
        try:
            action_type_id = int(action_type_id)
        except ValueError:
            # ensure old links still function
            action_type_id = {
                'samples': models.ActionType.SAMPLE_CREATION,
                'measurements': models.ActionType.MEASUREMENT,
                'simulations': models.ActionType.SIMULATION
            }.get(action_type_id, None)
        try:
            action_type = get_action_type_with_translation_in_language(
                action_type_id=action_type_id,
                language_id=user_language_id
            )
        except errors.ActionTypeDoesNotExistError:
            # fall back to all objects
            action_type_id = None
    user_id = flask.request.args.get('user_id', None)
    if user_id is not None:
        try:
            user_id = int(user_id)
        except ValueError:
            user_id = None
            flask.flash(_('Invalid user ID.'), 'error')
    if user_id is not None:
        try:
            users.get_user(user_id)
        except errors.UserDoesNotExistError:
            user_id = None
            flask.flash(_('Invalid user ID.'), 'error')
    actions = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id,
        action_type_id=action_type_id,
        owner_id=user_id,
    )
    user_favorite_action_ids = get_user_favorite_action_ids(flask_login.current_user.id)
    toggle_favorite_action_form = ToggleFavoriteActionForm()
    return flask.render_template(
        'actions/actions.html',
        actions=actions,
        action_type=action_type,
        action_permissions=action_permissions, Permissions=Permissions,
        user_favorite_action_ids=user_favorite_action_ids,
        toggle_favorite_action_form=toggle_favorite_action_form,
    )


@frontend.route('/actions/<int:action_id>', methods=['GET', 'POST'])
@flask_login.login_required
def action(action_id):
    try:
        action = get_action(action_id)
    except errors.ActionDoesNotExistError:
        return flask.abort(404)
    permissions = get_user_action_permissions(action_id, flask_login.current_user.id)
    if Permissions.READ not in permissions:
        return flask.abort(403)
    may_edit = Permissions.WRITE in permissions

    translations = get_action_translations_for_action(action.id, use_fallback=True)

    user_language_id = languages.get_user_language(flask_login.current_user).id

    if action.type.admin_only and not flask_login.current_user.is_admin:
        may_edit = False
    may_grant = Permissions.GRANT in permissions
    mode = flask.request.args.get('mode', None)
    if mode == 'edit':
        check_current_user_is_not_readonly()
        if not may_edit:
            return flask.abort(403)
        return show_action_form(action)

    title = translations[0].name

    single_translation = get_action_translation_for_action_in_language(action_id, language_id=user_language_id, use_fallback=True)
    if action.instrument_id:
        instrument_translation = get_instrument_translation_for_instrument_in_language(action.instrument_id, user_language_id, use_fallback=True)
        setattr(single_translation, 'instrument_translation', instrument_translation)
    action_type_translation = get_action_type_translation_for_action_type_in_language(action.type_id, user_language_id, use_fallback=True)
    setattr(single_translation, 'action_type_translation', action_type_translation)
    return flask.render_template(
        'actions/action.html',
        action=action,
        title=title,
        may_edit=may_edit,
        may_grant=may_grant,
        is_public=action_is_public(action_id),
        single_translation=single_translation
    )


@frontend.route('/actions/new/', methods=['GET', 'POST'])
@flask_login.login_required
def new_action():
    check_current_user_is_not_readonly()
    action_type_id = flask.request.args.get('action_type_id')
    if action_type_id is not None:
        try:
            action_type_id = int(action_type_id)
        except ValueError:
            action_type_id = None
    previous_action = None
    previous_action_id = flask.request.args.get('previous_action_id', None)
    if previous_action_id is not None:
        try:
            previous_action_id = int(previous_action_id)
        except ValueError:
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
            if previous_action.type.admin_only and not flask_login.current_user.is_admin:
                flask.flash(_('Only administrators can create actions of this type.'), 'error')
                return flask.redirect(flask.url_for('.action', action_id=previous_action_id))
    return show_action_form(None, previous_action, action_type_id)


def _get_lines_for_path(schema: dict, path: typing.List[str]) -> typing.Optional[typing.Set[int]]:
    schema_entry = schema
    parent = None
    key = None
    for property in path:
        if property == '[?]' and 'items' in schema_entry and isinstance(schema_entry['items'], dict):
            parent = schema_entry
            key = 'items'
            schema_entry = parent[key]
        elif 'properties' in schema_entry and property in schema_entry['properties'] and isinstance(schema_entry['properties'][property], dict):
            parent = schema_entry['properties']
            key = property
            schema_entry = parent[key]
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

    new_error_lines = set()
    for i in reversed(error_lines):
        if i in skip_lines:
            new_error_lines = {i - 1 for i in new_error_lines}
        else:
            new_error_lines.add(i + 1)
            new_error_lines.add(i)
            new_error_lines.add(i - 1)
    return new_error_lines


def show_action_form(action: typing.Optional[Action] = None, previous_action: typing.Optional[Action] = None, action_type_id: typing.Optional[int] = None):
    user_language_id = languages.get_user_language(flask_login.current_user).id
    action_translations = []
    load_translations = False

    allowed_language_ids = [
        language.id
        for language in get_languages(only_enabled_for_input=True)
    ]

    if action is not None:
        action_translations = get_action_translations_for_action(action.id, use_fallback=True)
        load_translations = True
        schema_json = json.dumps(action.schema, indent=2)
        submit_text = "Save"
    elif previous_action is not None:
        action_translations = get_action_translations_for_action(previous_action.id, use_fallback=True)
        load_translations = True
        schema_json = json.dumps(previous_action.schema, indent=2)
        submit_text = "Create"
    else:
        schema_json = json.dumps({
            'title': '',
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Name',
                    'type': 'text'
                }
            },
            'required': ['name']
        }, indent=2)
        submit_text = "Create"
    may_set_user_specific = action is None and flask_login.current_user.is_admin
    schema = None
    pygments_output = None
    error_message = None
    action_form = ActionForm()

    sample_action_type = get_action_type_with_translation_in_language(
        action_type_id=models.ActionType.SAMPLE_CREATION,
        language_id=user_language_id
    )
    measurement_action_type = get_action_type_with_translation_in_language(
        action_type_id=models.ActionType.MEASUREMENT,
        language_id=user_language_id
    )
    english = get_language(Language.ENGLISH)
    action_language_ids = [translation.language_id for translation in action_translations]
    action_translations = {
        action_translation.language_id: action_translation
        for action_translation in action_translations
    }

    use_schema_editor = get_user_settings(flask_login.current_user.id)["USE_SCHEMA_EDITOR"]
    if action is not None:
        if action.instrument_id:
            action_form.instrument.choices = [
                (str(action.instrument_id), get_instrument_translation_for_instrument_in_language(action.instrument_id, user_language_id, use_fallback=True).name)
            ]
            action_form.instrument.data = str(action.instrument_id)
        else:
            action_form.instrument.choices = [('-1', '-')]
            action_form.instrument.data = str(-1)
        action_form.type.data = action.type.id
    else:
        user_instrument_ids = get_user_instruments(flask_login.current_user.id, exclude_hidden=True)
        action_form.instrument.choices = [('-1', '-')] + [
            (str(instrument_id), get_instrument_translation_for_instrument_in_language(instrument_id, user_language_id, use_fallback=True).name)
            for instrument_id in user_instrument_ids
        ]
        if action_form.instrument.data is None or action_form.instrument.data == str(None):
            if previous_action is not None and previous_action.instrument_id in user_instrument_ids:
                action_form.instrument.data = str(previous_action.instrument_id)
            else:
                action_form.instrument.data = '-1'

    form_is_valid = False
    if not action_form.is_submitted():
        action_form.type.data = action_type_id
    elif action_form.validate_on_submit():
        form_is_valid = True
        action_type_id = action_form.type.data
    else:
        action_type_id = None

    if not action_form.is_submitted():
        if action is not None:
            action_form.is_hidden.data = action.is_hidden
            action_form.is_markdown.data = action.description_is_markdown
            action_form.short_description_is_markdown.data = action.short_description_is_markdown
            action_form.type.data = action.type.id
            action_form.is_public.data = action_is_public(action.id)
        elif previous_action is not None:
            action_form.is_hidden.data = False
            action_form.is_markdown.data = previous_action.description_is_markdown
            action_form.short_description_is_markdown.data = previous_action.short_description_is_markdown
            action_form.type.data = previous_action.type.id
            action_form.is_public.data = action_is_public(previous_action.id)

    if action_form.schema.data:
        schema_json = action_form.schema.data
    else:
        action_form.schema.data = schema_json
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
                error_message = "Failed to parse as JSON: {}".format(e.msg)
            except Exception as e:
                error_lines = all_lines
                error_message = "Failed to parse as JSON: {}".format(str(e))
        if schema is not None:
            try:
                validate_schema(schema)
            except errors.ValidationError as e:
                error_message = e.message
                if not e.paths:
                    error_lines = all_lines
                else:
                    schema_json = json.dumps(schema, indent=2)
                    all_lines = set(range(1, 1 + len(schema_json)))
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
                error_message = "Unknown errror: {}".format(str(e))
        lexer = pygments.lexers.data.JsonLexer()
        formatter = pygments.formatters.HtmlFormatter(cssclass='pygments', hl_lines=list(error_lines))
        pygments_output = pygments.highlight(schema_json, lexer, formatter)
    if schema is not None and error_message is None and form_is_valid:
        # First block for validation
        try:
            translation_data = json.loads(action_form.translations.data)
        except Exception:
            flask.flash(_("Something went wrong"), 'error')
            return flask.render_template(
                'actions/action_form.html',
                action_form=action_form,
                action_translations=action_translations,
                action_language_ids=action_language_ids,
                action_types_with_translations=get_action_types_with_translations_in_language(user_language_id),
                pygments_output=pygments_output,
                error_message=error_message,
                schema_json=schema_json,
                submit_text=submit_text,
                sample_action_type=sample_action_type,
                measurement_action_type=measurement_action_type,
                use_schema_editor=use_schema_editor,
                may_change_type=action is None,
                may_change_instrument=action is None,
                may_set_user_specific=may_set_user_specific,
                languages=get_languages(only_enabled_for_input=True),
                load_translations=load_translations,
                ENGLISH=english
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
                            action_form=action_form,
                            action_translations=action_translations,
                            action_language_ids=action_language_ids,
                            action_types_with_translations=get_action_types_with_translations_in_language(user_language_id),
                            pygments_output=pygments_output,
                            error_message=error_message,
                            schema_json=schema_json,
                            submit_text=submit_text,
                            sample_action_type=sample_action_type,
                            measurement_action_type=measurement_action_type,
                            use_schema_editor=use_schema_editor,
                            may_change_type=action is None,
                            may_change_instrument=action is None,
                            may_set_user_specific=may_set_user_specific,
                            languages=get_languages(only_enabled_for_input=True),
                            load_translations=load_translations,
                            ENGLISH=english
                        )

        instrument_id = action_form.instrument.data
        is_public = action_form.is_public.data
        is_hidden = action_form.is_hidden.data
        is_markdown = action_form.is_markdown.data
        short_description_is_markdown = action_form.short_description_is_markdown.data

        try:
            instrument_id = int(instrument_id)
        except ValueError:
            instrument_id = None
        if instrument_id < 0:
            instrument_id = None
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
                short_description_is_markdown=short_description_is_markdown
            )
            if is_public:
                set_action_public(action.id, True)
        else:
            update_action(
                action_id=action.id,
                schema=schema,
                is_hidden=is_hidden,
                description_is_markdown=is_markdown,
                short_description_is_markdown=short_description_is_markdown
            )
            set_action_public(action.id, is_public)

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
                translation['language'] = languages.get_language(translation['language_id'])
                action_translations[translation['language_id']] = translation
                if translation['language_id'] not in action_translations:
                    action_language_ids.append(translation['language_id'])
            if action_language_ids:
                load_translations = True
        except Exception:
            pass
    return flask.render_template(
        'actions/action_form.html',
        action_form=action_form,
        action_translations=action_translations,
        action_language_ids=action_language_ids,
        action_types_with_translations=get_action_types_with_translations_in_language(user_language_id),
        pygments_output=pygments_output,
        error_message=error_message,
        schema_json=schema_json,
        submit_text=submit_text,
        sample_action_type=sample_action_type,
        measurement_action_type=measurement_action_type,
        use_schema_editor=use_schema_editor,
        may_change_type=action is None,
        may_change_instrument=action is None,
        may_set_user_specific=may_set_user_specific,
        languages=get_languages(only_enabled_for_input=True),
        load_translations=load_translations,
        ENGLISH=english
    )


@frontend.route('/actions/<int:action_id>/permissions', methods=['GET', 'POST'])
@flask_login.login_required
def action_permissions(action_id):
    try:
        action = get_action(action_id)
    except errors.ActionDoesNotExistError:
        return flask.abort(404)
    permissions = get_user_action_permissions(action_id, flask_login.current_user.id)
    if Permissions.READ not in permissions:
        return flask.abort(403)
    user_may_edit = Permissions.GRANT in permissions
    public_permissions = Permissions.READ if action_is_public(action_id) else Permissions.NONE
    user_permissions = get_action_permissions_for_users(
        action_id=action.id,
        include_instrument_responsible_users=False,
        include_groups=False,
        include_projects=False
    )
    group_permissions = get_action_permissions_for_groups(
        action_id=action.id,
        include_projects=False
    )
    project_permissions = get_action_permissions_for_projects(
        action_id=action.id
    )
    if user_may_edit:
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
        permissions_form = ActionPermissionsForm(
            public_permissions=public_permissions.name.lower(),
            user_permissions=user_permission_form_data,
            group_permissions=group_permission_form_data,
            project_permissions=project_permission_form_data
        )
        users = get_users(exclude_hidden=True)
        users = [user for user in users if user.id not in user_permissions]
        add_user_permissions_form = ActionUserPermissionsForm()
        groups = get_groups()
        groups = [group for group in groups if group.id not in group_permissions]
        add_group_permissions_form = ActionGroupPermissionsForm()
        projects = get_projects()
        projects_by_id = {
            project.id: project
            for project in projects
        }
        projects = [project for project in projects if project.id not in project_permissions]

        if not flask.current_app.config['DISABLE_SUBPROJECTS']:
            project_id_hierarchy_list = get_project_id_hierarchy_list(list(projects_by_id))
            project_id_hierarchy_list = [
                (level, project_id, project_id not in project_permissions)
                for level, project_id in project_id_hierarchy_list
            ]
        else:
            project_id_hierarchy_list = [
                (0, project.id, project.id not in project_permissions)
                for project in sorted(projects, key=lambda project: project.id)
            ]
        add_project_permissions_form = ActionProjectPermissionsForm()
    else:
        permissions_form = None
        users = None
        add_user_permissions_form = None
        groups = None
        add_group_permissions_form = None
        projects = None
        add_project_permissions_form = None
        projects_by_id = None
        project_id_hierarchy_list = None

    if flask.request.method.lower() == 'post':
        if not user_may_edit:
            flask.flash(_('You need GRANT permissions to edit the permissions for this action.'), 'error')
            return flask.redirect(flask.url_for('.action_permissions', action_id=action.id))
        if 'add_user_permissions' in flask.request.form and add_user_permissions_form.validate_on_submit():
            user_id = add_user_permissions_form.user_id.data
            permissions = Permissions.from_name(add_user_permissions_form.permissions.data)
            if permissions == Permissions.NONE or user_id in user_permissions:
                flask.flash(_('Failed to update action permissions.'), 'error')
                return flask.redirect(flask.url_for('.action_permissions', action_id=action.id))
            set_user_action_permissions(action.id, user_id, permissions)
            flask.flash(_('Successfully updated action permissions.'), 'success')
            return flask.redirect(flask.url_for('.action_permissions', action_id=action.id))
        if 'add_group_permissions' in flask.request.form and add_group_permissions_form.validate_on_submit():
            group_id = add_group_permissions_form.group_id.data
            permissions = Permissions.from_name(add_group_permissions_form.permissions.data)
            if permissions == Permissions.NONE or group_id in group_permissions:
                flask.flash(_('Failed to update action permissions.'), 'error')
                return flask.redirect(flask.url_for('.action_permissions', action_id=action.id))
            set_group_action_permissions(action.id, group_id, permissions)
            flask.flash(_('Successfully updated action permissions.'), 'success')
            return flask.redirect(flask.url_for('.action_permissions', action_id=action.id))
        if 'add_project_permissions' in flask.request.form and add_project_permissions_form.validate_on_submit():
            project_id = add_project_permissions_form.project_id.data
            permissions = Permissions.from_name(add_project_permissions_form.permissions.data)
            if permissions == Permissions.NONE or project_id in project_permissions:
                flask.flash(_('Failed to update action permissions.'), 'error')
                return flask.redirect(flask.url_for('.action_permissions', action_id=action.id))
            set_project_action_permissions(action.id, project_id, permissions)
            flask.flash(_('Successfully updated action permissions.'), 'success')
            return flask.redirect(flask.url_for('.action_permissions', action_id=action.id))
        if 'edit_permissions' in flask.request.form and permissions_form.validate_on_submit():
            set_action_public(action_id, permissions_form.public_permissions.data == 'read')
            for user_permissions_data in permissions_form.user_permissions.data:
                user_id = user_permissions_data['user_id']
                try:
                    get_user(user_id)
                except errors.UserDoesNotExistError:
                    continue
                permissions = Permissions.from_name(user_permissions_data['permissions'])
                set_user_action_permissions(
                    action_id=action.id,
                    user_id=user_id,
                    permissions=permissions
                )
            for group_permissions_data in permissions_form.group_permissions.data:
                group_id = group_permissions_data['group_id']
                try:
                    get_group(group_id)
                except errors.GroupDoesNotExistError:
                    continue
                permissions = Permissions.from_name(group_permissions_data['permissions'])
                set_group_action_permissions(
                    action_id=action.id,
                    group_id=group_id,
                    permissions=permissions
                )
            for project_permissions_data in permissions_form.project_permissions.data:
                project_id = project_permissions_data['project_id']
                try:
                    get_project(project_id)
                except errors.ProjectDoesNotExistError:
                    continue
                permissions = Permissions.from_name(project_permissions_data['permissions'])
                set_project_action_permissions(
                    action_id=action.id,
                    project_id=project_id,
                    permissions=permissions
                )
            flask.flash(_("Successfully updated action permissions."), 'success')
            return flask.redirect(flask.url_for('.action_permissions', action_id=action.id))
        flask.flash(_('Failed to update action permissions.'), 'error')
        return flask.redirect(flask.url_for('.action_permissions', action_id=action.id))

    return flask.render_template(
        'actions/action_permissions.html',
        user_may_edit=user_may_edit,
        action=action,
        instrument=action.instrument,
        Permissions=Permissions,
        project_permissions=project_permissions,
        group_permissions=group_permissions,
        user_permissions=user_permissions,
        public_permissions=public_permissions,
        form=permissions_form,
        users=users,
        add_user_permissions_form=add_user_permissions_form,
        groups=groups,
        add_group_permissions_form=add_group_permissions_form,
        projects=projects,
        add_project_permissions_form=add_project_permissions_form,
        projects_by_id=projects_by_id,
        project_id_hierarchy_list=project_id_hierarchy_list,
        get_user=get_user,
        get_group=get_group,
        get_project=get_project,
    )
