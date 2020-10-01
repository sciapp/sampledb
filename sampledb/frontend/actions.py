# coding: utf-8
"""

"""

import json
import typing

import flask
import flask_login
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SelectField, IntegerField
from wtforms.validators import InputRequired, Length, ValidationError
import pygments
import pygments.lexers.data
import pygments.formatters

from . import frontend
from .. import models
from ..logic.actions import Action, create_action, get_action, get_actions, update_action, get_action_type
from ..logic.action_permissions import Permissions, action_is_public, get_user_action_permissions, set_action_public
from ..logic.favorites import get_user_favorite_action_ids
from ..logic.instruments import get_instrument, get_user_instruments
from ..logic import errors, users
from ..logic.schemas.validate_schema import validate_schema
from ..logic.settings import get_user_settings
from .users.forms import ToggleFavoriteActionForm
from .utils import check_current_user_is_not_readonly, markdown_to_safe_html

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class ActionForm(FlaskForm):
    name = StringField(validators=[Length(min=1, max=100)])
    description = StringField()
    type = IntegerField()
    instrument = SelectField()
    schema = StringField(validators=[InputRequired()])
    is_public = BooleanField()
    is_user_specific = BooleanField(default=True)
    is_markdown = BooleanField(default=None)
    is_hidden = BooleanField(default=None)

    def validate_type(form, field):
        try:
            action_type_id = int(field.data)
        except ValueError:
            raise ValidationError("Invalid action type")
        try:
            action_type = get_action_type(action_type_id)
        except errors.ActionTypeDoesNotExistError:
            raise ValidationError("Unknown action type")
        if action_type.admin_only and not flask_login.current_user.is_admin:
            raise ValidationError("Actions with this type can only be created by administrators")


@frontend.route('/actions/')
@flask_login.login_required
def actions():
    action_type_id = flask.request.args.get('t', None)
    action_type = None
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
            action_type = get_action_type(action_type_id)
        except errors.ActionTypeDoesNotExistError:
            # fall back to all objects
            action_type_id = None
    user_id = flask.request.args.get('user_id', None)
    if user_id is not None:
        try:
            user_id = int(user_id)
        except ValueError:
            user_id = None
            flask.flash('Invalid user ID.', 'error')
    if user_id is not None:
        try:
            users.get_user(user_id)
        except errors.UserDoesNotExistError:
            user_id = None
            flask.flash('Invalid user ID.', 'error')
    actions = []
    action_permissions = {}
    for action in get_actions(action_type_id=action_type_id):
        if user_id is not None and action.user_id != user_id:
            continue
        if action.is_hidden and not flask_login.current_user.is_admin and user_id != flask_login.current_user.id:
            continue
        permissions = get_user_action_permissions(user_id=flask_login.current_user.id, action_id=action.id)
        if Permissions.READ in permissions:
            actions.append(action)
            action_permissions[action.id] = permissions
    user_favorite_action_ids = get_user_favorite_action_ids(flask_login.current_user.id)
    # Sort by: favorite / not favorite, instrument name (independent actions first), action name
    actions.sort(key=lambda action: (
        0 if action.id in user_favorite_action_ids else 1,
        action.user.name.lower() if action.user else '',
        action.instrument.name.lower() if action.instrument else '',
        action.name.lower()
    ))
    toggle_favorite_action_form = ToggleFavoriteActionForm()
    return flask.render_template(
        'actions/actions.html',
        actions=actions,
        action_type=action_type,
        action_permissions=action_permissions, Permissions=Permissions,
        user_favorite_action_ids=user_favorite_action_ids,
        toggle_favorite_action_form=toggle_favorite_action_form
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
    mode = flask.request.args.get('mode', None)
    if mode == 'edit':
        check_current_user_is_not_readonly()
        if not may_edit:
            return flask.abort(403)
        return show_action_form(action)
    return flask.render_template(
        'actions/action.html',
        action=action,
        may_edit=may_edit,
        is_public=action_is_public(action_id)
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
                flask.flash('Insufficient permissions to use the requested previous action.', 'error')
                previous_action = None
        except errors.ActionDoesNotExistError:
            flask.flash('The requested previous action does not exist.', 'error')
        else:
            if previous_action.type.admin_only and not flask_login.current_user.is_admin:
                flask.flash('Only administrators can create actions of this type.', 'error')
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
    if action is not None:
        schema_json = json.dumps(action.schema, indent=2)
        submit_text = "Save"
    elif previous_action is not None:
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
    may_change_public = action is None or action.user_id is not None
    may_set_user_specific = action is None and flask_login.current_user.is_admin
    schema = None
    pygments_output = None
    error_message = None
    action_form = ActionForm()
    if action is not None:
        if action.instrument_id:
            action_form.instrument.choices = [
                (str(action.instrument_id), get_instrument(action.instrument_id).name)
            ]
            action_form.instrument.data = str(action.instrument_id)
        else:
            action_form.instrument.choices = [('-1', '-')]
            action_form.instrument.data = str(-1)
        action_form.type.data = action.type.id
        if action_form.name.data is None:
            action_form.is_public.data = None
    else:
        user_instrument_ids = get_user_instruments(flask_login.current_user.id, exclude_hidden=True)
        action_form.instrument.choices = [('-1', '-')] + [
            (str(instrument_id), get_instrument(instrument_id).name)
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

    if action is not None:
        if action_form.name.data is None:
            action_form.name.data = action.name
        if action_form.description.data is None:
            action_form.description.data = action.description
        if not action_form.is_submitted():
            action_form.is_markdown.data = (action.description_as_html is not None)
            action_form.is_hidden.data = action.is_hidden
        if action_form.type.data is None:
            action_form.type.data = action.type.id
        if action_form.is_public.data is None:
            action_form.is_public.data = action_is_public(action.id)
    elif previous_action is not None:
        if action_form.name.data is None:
            action_form.name.data = previous_action.name
        if action_form.description.data is None:
            action_form.description.data = previous_action.description
        if not action_form.is_submitted():
            action_form.is_markdown.data = (previous_action.description_as_html is not None)
            action_form.is_hidden.data = False
        if action_form.type.data is None:
            action_form.type.data = previous_action.type.id
        if action_form.is_public.data is None:
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
        name = action_form.name.data
        description = action_form.description.data
        if action_form.is_markdown.data:
            description_as_html = markdown_to_safe_html(description)
        else:
            description_as_html = None

        instrument_id = action_form.instrument.data
        is_public = action_form.is_public.data
        is_hidden = action_form.is_hidden.data
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
                action_type_id,
                name,
                description,
                schema,
                instrument_id,
                user_id,
                description_as_html=description_as_html,
                is_hidden=is_hidden
            )
            flask.flash('The action was created successfully.', 'success')
            if may_change_public and is_public:
                set_action_public(action.id, True)
        else:
            update_action(
                action.id,
                name,
                description,
                schema,
                description_as_html=description_as_html,
                is_hidden=is_hidden
            )
            flask.flash('The action was updated successfully.', 'success')
            if may_change_public and is_public is not None:
                set_action_public(action.id, is_public)
        return flask.redirect(flask.url_for('.action', action_id=action.id))

    sample_action_type = get_action_type(models.ActionType.SAMPLE_CREATION)
    measurement_action_type = get_action_type(models.ActionType.MEASUREMENT)

    use_schema_editor = get_user_settings(flask_login.current_user.id)["USE_SCHEMA_EDITOR"]
    return flask.render_template(
        'actions/action_form.html',
        action_form=action_form,
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
        may_change_public=may_change_public
    )
