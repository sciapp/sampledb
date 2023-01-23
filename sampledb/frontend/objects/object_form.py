# coding: utf-8
"""

"""
from copy import deepcopy
import datetime

import flask
import flask_login
import itsdangerous
from flask_babel import _

from ... import logic
from ... import models
from ...logic.actions import get_actions, get_action, get_action_type, get_action_types
from ...logic.action_permissions import get_sorted_actions_for_user
from ...logic.object_permissions import Permissions, get_user_object_permissions, get_objects_with_permissions
from ...logic.users import get_users
from ...logic.schemas import validate, generate_placeholder
from ...logic.objects import create_object, create_object_batch, update_object
from ...logic.languages import get_language, get_languages, Language
from ...logic.errors import ValidationError
from ...logic.components import get_component
from .forms import ObjectForm
from ..utils import default_format_datetime, custom_format_number
from .object_form_parser import parse_form_data
from ...logic.utils import get_translated_text
from .permissions import get_object_if_current_user_has_read_permissions


def show_object_form(object, action, previous_object=None, should_upgrade_schema=False, placeholder_data=None, possible_properties=None, passed_object_ids=None, show_selecting_modal=False, previous_actions=None):
    if object is None and previous_object is None:
        data = generate_placeholder(action.schema)
        if placeholder_data:
            for path, value in placeholder_data.items():
                try:
                    sub_data = data
                    for step in path[:-1]:
                        sub_data = sub_data[step]
                    sub_data[path[-1]] = value
                except Exception:
                    # Ignore invalid placeholder data
                    pass
    elif object is None and previous_object is not None:
        data = logic.schemas.copy_data(previous_object.data, previous_object.schema)
    else:
        data = object.data
    previous_object_schema = None
    mode = 'edit'
    if should_upgrade_schema and action.schema:
        mode = 'upgrade'
        assert object is not None
        schema = action.schema
        data, upgrade_warnings = logic.schemas.convert_to_schema(object.data, object.schema, action.schema)
        for upgrade_warning in upgrade_warnings:
            flask.flash(upgrade_warning, 'warning')
    elif object is not None:
        schema = object.schema
    elif previous_object is not None:
        schema = previous_object.schema
        previous_object_schema = schema
    else:
        schema = action.schema

    if action is not None and action.instrument is not None and flask_login.current_user in action.instrument.responsible_users:
        may_create_log_entry = True
        create_log_entry_default = action.instrument.create_log_entry_default
        instrument_log_categories = logic.instrument_log_entries.get_instrument_log_categories(action.instrument.id)
        if 'create_instrument_log_entry' in flask.request.form:
            category_ids = []
            for category_id in flask.request.form.getlist('instrument_log_categories'):
                try:
                    if int(category_id) in [category.id for category in instrument_log_categories]:
                        category_ids.append(int(category_id))
                except Exception:
                    pass
        else:
            category_ids = None
    else:
        instrument_log_categories = None
        category_ids = None
        create_log_entry_default = None
        may_create_log_entry = False

    permissions_for_group_id = None
    permissions_for_project_id = None
    copy_permissions_object_id = None
    if object is None:
        if flask.request.form.get('permissions_method') == 'copy_permissions':
            if flask.request.form.get('copy_permissions_object_id'):
                copy_permissions_object_id = flask.request.form.get('copy_permissions_object_id')
                try:
                    copy_permissions_object_id = int(copy_permissions_object_id)
                    if Permissions.READ not in get_user_object_permissions(copy_permissions_object_id, flask_login.current_user.id):
                        flask.flash(_("Unable to copy permissions. Default permissions will be applied."), 'error')
                        copy_permissions_object_id = None
                except Exception:
                    flask.flash(_("Unable to copy permissions. Default permissions will be applied."), 'error')
                    copy_permissions_object_id = None
            else:
                flask.flash(_("No object selected. Default permissions will be applied."), 'error')
                copy_permissions_object_id = None
        elif flask.request.form.get('permissions_method') == 'permissions_for_group':
            if flask.request.form.get('permissions_for_group_group_id'):
                permissions_for_group_id = flask.request.form.get('permissions_for_group_group_id')
                try:
                    permissions_for_group_id = int(permissions_for_group_id)
                    if flask_login.current_user.id not in logic.groups.get_group_member_ids(permissions_for_group_id):
                        flask.flash(_("Unable to grant permissions to basic group. Default permissions will be applied."), 'error')
                        permissions_for_group_id = None
                except Exception:
                    flask.flash(_("Unable to grant permissions to basic group. Default permissions will be applied."), 'error')
                    permissions_for_group_id = None
            else:
                flask.flash(_("No basic group selected. Default permissions will be applied."), 'error')
                permissions_for_group_id = None
        elif flask.request.form.get('permissions_method') == 'permissions_for_project':
            if flask.request.form.get('permissions_for_project_project_id'):
                permissions_for_project_id = flask.request.form.get('permissions_for_project_project_id')
                try:
                    permissions_for_project_id = int(permissions_for_project_id)
                    if flask_login.current_user.id not in logic.projects.get_project_member_user_ids_and_permissions(permissions_for_project_id, include_groups=True):
                        flask.flash(_("Unable to grant permissions to project group. Default permissions will be applied."), 'error')
                        permissions_for_project_id = None
                except Exception:
                    flask.flash(_("Unable to grant permissions to project group. Default permissions will be applied."), 'error')
                    permissions_for_project_id = None
            else:
                flask.flash(_("No project group selected. Default permissions will be applied."), 'error')
                permissions_for_project_id = None

    if previous_object is not None:
        action_id = previous_object.action_id
        previous_object_id = previous_object.id
        has_grant_for_previous_object = Permissions.GRANT in get_user_object_permissions(user_id=flask_login.current_user.id, object_id=previous_object_id)
    else:
        action_id = action.id
        previous_object_id = None
        has_grant_for_previous_object = False
    errors = {}
    form_data = {}
    if not previous_actions:
        override_previous_actions = False
        previous_actions = []
    else:
        override_previous_actions = True
    serializer = itsdangerous.URLSafeSerializer(flask.current_app.config['SECRET_KEY'])
    form = ObjectForm()
    if flask.request.method != 'GET' and form.validate_on_submit():
        raw_form_data = {key: flask.request.form.getlist(key) for key in flask.request.form}
        form_data = {k: v[0] for k, v in raw_form_data.items()}
        if 'input_num_batch_objects' in form_data:
            try:
                # The form allows notations like '1.2e1' for '12', however
                # Python can only parse these as floats
                num_objects_in_batch = float(form_data['input_num_batch_objects'])
                if num_objects_in_batch == int(num_objects_in_batch):
                    num_objects_in_batch = int(num_objects_in_batch)
                else:
                    raise ValueError()
                if num_objects_in_batch > flask.current_app.config['MAX_BATCH_SIZE'] or num_objects_in_batch <= 0:
                    if num_objects_in_batch <= 0:
                        raise ValueError()
                    form_data['input_num_batch_objects'] = str(num_objects_in_batch)
                    errors['input_num_batch_objects'] = _('The maximum number of objects in one batch is %(max_batch_size)s.', max_batch_size=flask.current_app.config['MAX_BATCH_SIZE'])
            except ValueError:
                errors['input_num_batch_objects'] = _('The number of objects in batch must be an positive integer.')
                num_objects_in_batch = None
            else:
                form_data['input_num_batch_objects'] = str(num_objects_in_batch)
        else:
            num_objects_in_batch = None

        if 'previous_actions' in flask.request.form:
            try:
                previous_actions = serializer.loads(flask.request.form['previous_actions'])
            except itsdangerous.BadData:
                flask.abort(400)

        if "action_submit" in form_data:
            # The object name might need the batch number to match the pattern
            if schema.get('batch', False) and num_objects_in_batch is not None:
                name_suffix_format = schema.get('batch_name_format', '{:d}')
                try:
                    name_suffix_format.format(1)
                except (ValueError, KeyError):
                    name_suffix_format = '{:d}'
                if name_suffix_format:
                    example_name_suffix = name_suffix_format.format(1)
                else:
                    example_name_suffix = ''
                if 'object__name__text' in form_data:
                    batch_base_name = form_data['object__name__text']
                    raw_form_data['object__name__text'] = [batch_base_name + example_name_suffix]
                else:
                    enabled_languages = form_data.get('object__name__text_languages', [])
                    if type(enabled_languages) is str:
                        enabled_languages = [enabled_languages]
                    if 'en' not in enabled_languages:
                        enabled_languages.append('en')
                    for language_code in enabled_languages:
                        batch_base_name = form_data.get('object__name__text_' + language_code, '')
                        raw_form_data['object__name__text_' + language_code] = [batch_base_name + example_name_suffix]
            else:
                batch_base_name = None
                name_suffix_format = None
            object_data, parsing_errors = parse_form_data(raw_form_data, schema)
            errors.update(parsing_errors)
            if form_data['action_submit'] == 'inline_edit' and errors:
                return flask.jsonify({
                    'errors': errors
                }), 400
            if object_data is not None and not errors:
                try:
                    validate(object_data, schema, strict=True)
                except ValidationError:
                    # TODO: proper logging
                    print('object schema validation failed')
                    # TODO: handle error
                    flask.abort(400)
                for markdown in logic.markdown_to_html.get_markdown_from_object_data(object_data):
                    markdown_as_html = logic.markdown_to_html.markdown_to_safe_html(markdown)
                    logic.markdown_images.mark_referenced_markdown_images_as_permanent(markdown_as_html)
                if object is None:
                    if schema.get('batch', False) and num_objects_in_batch is not None:
                        if 'name' in object_data and 'text' in object_data['name'] and name_suffix_format is not None and batch_base_name is not None:
                            data_sequence = []
                            for i in range(1, num_objects_in_batch + 1):
                                if name_suffix_format:
                                    name_suffix = name_suffix_format.format(i)
                                else:
                                    name_suffix = ''
                                object_data['name']['text'] = batch_base_name + name_suffix
                                data_sequence.append(deepcopy(object_data))
                        else:
                            data_sequence = [object_data] * num_objects_in_batch
                        objects = create_object_batch(
                            action_id=action.id,
                            data_sequence=data_sequence,
                            user_id=flask_login.current_user.id,
                            copy_permissions_object_id=copy_permissions_object_id,
                            permissions_for_group_id=permissions_for_group_id,
                            permissions_for_project_id=permissions_for_project_id
                        )
                        object_ids = [object.id for object in objects]
                        if category_ids is not None and not flask.current_app.config['DISABLE_INSTRUMENTS']:
                            log_entry = logic.instrument_log_entries.create_instrument_log_entry(
                                instrument_id=action.instrument.id,
                                user_id=flask_login.current_user.id,
                                content='',
                                category_ids=category_ids
                            )
                            for object_id in object_ids:
                                logic.instrument_log_entries.create_instrument_log_object_attachment(
                                    instrument_log_entry_id=log_entry.id,
                                    object_id=object_id
                                )
                        flask.flash(_('The objects were created successfully.'), 'success')
                        return flask.redirect(flask.url_for('.objects', ids=','.join([str(object_id) for object_id in object_ids])))
                    else:
                        object = create_object(
                            action_id=action.id,
                            data=object_data,
                            user_id=flask_login.current_user.id,
                            previous_object_id=previous_object_id,
                            schema=previous_object_schema,
                            copy_permissions_object_id=copy_permissions_object_id,
                            permissions_for_group_id=permissions_for_group_id,
                            permissions_for_project_id=permissions_for_project_id
                        )
                        if category_ids is not None and not flask.current_app.config['DISABLE_INSTRUMENTS']:
                            log_entry = logic.instrument_log_entries.create_instrument_log_entry(
                                instrument_id=action.instrument.id,
                                user_id=flask_login.current_user.id,
                                content='',
                                category_ids=category_ids
                            )
                            logic.instrument_log_entries.create_instrument_log_object_attachment(
                                instrument_log_entry_id=log_entry.id,
                                object_id=object.id
                            )
                        flask.flash(_('The object was created successfully.'), 'success')
                else:
                    if object_data != object.data or schema != object.schema:
                        update_object(object_id=object.id, user_id=flask_login.current_user.id, data=object_data, schema=schema)
                    flask.flash(_('The object was updated successfully.'), 'success')
                return flask.redirect(flask.url_for('.object', object_id=object.id))
        elif any(name.startswith('action_object__') and (name.endswith('__delete') or name.endswith('__add') or name.endswith('__addcolumn') or name.endswith('__deletecolumn')) for name in form_data):
            action = [name for name in form_data if name.startswith('action_')][0]
            previous_actions.append(action)

    if previous_actions and not override_previous_actions:
        try:
            for action in previous_actions:
                _apply_action_to_data(action, data, schema)
            form_data = _apply_action_to_form_data(previous_actions[-1], form_data)
        except ValueError:
            flask.abort(400)

    if not flask.current_app.config["LOAD_OBJECTS_IN_BACKGROUND"]:
        referencable_objects = get_objects_with_permissions(
            user_id=flask_login.current_user.id,
            permissions=Permissions.READ
        )
        if object is not None:
            referencable_objects = [
                referencable_object
                for referencable_object in referencable_objects
                if referencable_object.object_id != object.object_id
            ]

    else:
        referencable_objects = []
        existing_objects = []
    sorted_actions = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id
    )

    action_type_id_by_action_id = {}
    for action_type in get_action_types():
        for action in get_actions(action_type_id=action_type.id):
            if action_type.component_id is not None and action_type.fed_id < 0:
                action_type_id_by_action_id[action.id] = action_type.fed_id
            else:
                action_type_id_by_action_id[action.id] = action_type.id

    tags = [{'name': tag.name, 'uses': tag.uses} for tag in logic.tags.get_tags()]
    users = get_users(exclude_hidden=not flask_login.current_user.is_admin)

    english = get_language(Language.ENGLISH)

    if not schema:
        flask.flash(_('Creating objects with this action has been disabled.'), 'error')
        return flask.redirect(flask.url_for('.action', action_id=action_id))

    def insert_recipe_types(subschema):
        if subschema['type'] == 'object':
            if 'recipes' in subschema:
                for i, recipe in enumerate(subschema['recipes']):
                    for property in recipe['property_values']:
                        if subschema['properties'][property]['type'] == 'datetime':
                            subschema['recipes'][i]['property_values'][property] = {
                                'value': default_format_datetime(recipe['property_values'][property]['utc_datetime']) if
                                recipe['property_values'][property] is not None else None,
                                'type': subschema['properties'][property]['type']
                            }
                        elif subschema['properties'][property]['type'] == 'quantity':
                            subschema['recipes'][i]['property_values'][property] = {
                                'value': custom_format_number(
                                    recipe['property_values'][property]['magnitude_in_base_units']) if
                                recipe['property_values'][property] is not None else None,
                                'type': subschema['properties'][property]['type']
                            }
                        elif subschema['properties'][property]['type'] == 'text' and 'choices' in \
                                subschema['properties'][property]:
                            subschema['recipes'][i]['property_values'][property] = {
                                'value': recipe['property_values'][property]['text'] if recipe['property_values'][property] is not None else None,
                                'type': 'choice'
                            }
                        elif subschema['properties'][property]['type'] == 'text' and 'markdown' in \
                                subschema['properties'][property] and subschema['properties'][property]['markdown']:
                            subschema['recipes'][i]['property_values'][property] = {
                                'value': recipe['property_values'][property]['text'] if recipe['property_values'][property] is not None else None,
                                'type': 'markdown'
                            }
                        elif subschema['properties'][property]['type'] == 'text' and 'multiline' in \
                                subschema['properties'][property] and subschema['properties'][property]['multiline']:
                            subschema['recipes'][i]['property_values'][property] = {
                                'value': recipe['property_values'][property]['text'] if recipe['property_values'][property] is not None else None,
                                'type': 'multiline'
                            }
                        elif subschema['properties'][property]['type'] == 'text':
                            subschema['recipes'][i]['property_values'][property] = {
                                'value': recipe['property_values'][property]['text'] if recipe['property_values'][property] is not None else None,
                                'type': 'text'
                            }
                        elif subschema['properties'][property]['type'] == 'bool':
                            subschema['recipes'][i]['property_values'][property] = {
                                'value': recipe['property_values'][property]['value'],
                                'type': subschema['properties'][property]['type']
                            }
                        subschema['recipes'][i]['property_values'][property]['title'] = get_translated_text(
                            subschema['properties'][property]['title'])
                    subschema['recipes'][i]['name'] = get_translated_text(subschema['recipes'][i]['name'])
            for property in subschema['properties']:
                insert_recipe_types(subschema['properties'][property])
        elif subschema['type'] == 'array':
            insert_recipe_types(subschema['items'])

    insert_recipe_types(schema)

    if object is None:
        action_type_id = action_type_id_by_action_id.get(action_id)
        action = get_action(action_id)
        if action_type_id is None or get_action_type(action_type_id).disable_create_objects or action.disable_create_objects or (action.admin_only and not flask_login.current_user.is_admin):
            flask.flash(_('Creating objects with this action has been disabled.'), 'error')
            return flask.redirect(flask.url_for('.action', action_id=action_id))
        if not flask.current_app.config["LOAD_OBJECTS_IN_BACKGROUND"]:
            existing_objects = get_objects_with_permissions(
                user_id=flask_login.current_user.id,
                permissions=Permissions.GRANT
            )

        user_groups = logic.groups.get_user_groups(flask_login.current_user.id)
        user_projects = logic.projects.get_user_projects(flask_login.current_user.id, include_groups=True)

        return flask.render_template(
            'objects/forms/form_create.html',
            action_id=action_id,
            schema=schema,
            data=data,
            errors=errors,
            form_data=form_data,
            previous_actions=serializer.dumps(previous_actions),
            form=form,
            can_copy_permissions=True,
            existing_objects=existing_objects,
            user_groups=user_groups,
            user_projects=user_projects,
            referencable_objects=referencable_objects,
            sorted_actions=sorted_actions,
            action_type_id_by_action_id=action_type_id_by_action_id,
            get_object_if_current_user_has_read_permissions=get_object_if_current_user_has_read_permissions,
            ActionType=models.ActionType,
            datetime=datetime,
            tags=tags,
            users=users,
            may_create_log_entry=may_create_log_entry,
            instrument_log_categories=instrument_log_categories,
            create_log_entry_default=create_log_entry_default,
            previous_object_id=previous_object_id,
            has_grant_for_previous_object=has_grant_for_previous_object,
            languages=get_languages(only_enabled_for_input=True),
            get_component=get_component,
            ENGLISH=english,
            possible_properties=possible_properties,
            passed_object_ids=passed_object_ids,
            show_selecting_modal=show_selecting_modal
        )
    else:
        return flask.render_template(
            'objects/forms/form_edit.html',
            schema=schema,
            data=data,
            object_id=object.object_id,
            errors=errors,
            form_data=form_data,
            previous_actions=serializer.dumps(previous_actions),
            form=form,
            referencable_objects=referencable_objects,
            sorted_actions=sorted_actions,
            get_object_if_current_user_has_read_permissions=get_object_if_current_user_has_read_permissions,
            action_type_id_by_action_id=action_type_id_by_action_id,
            ActionType=models.ActionType,
            datetime=datetime,
            tags=tags,
            users=users,
            mode=mode,
            languages=get_languages(),
            get_component=get_component,
            ENGLISH=english,
            possible_properties=None
        )


def _get_sub_data_and_schema(data, schema, id_prefix):
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
            if isinstance(key, int):
                while key >= len(sub_data):
                    sub_data.append(generate_placeholder(sub_schema))
            elif key not in sub_data:
                sub_data[key] = generate_placeholder(sub_schema)
            sub_data = sub_data[key]
        if sub_schema['type'] != 'array':
            raise ValueError('invalid type')
    except (ValueError, KeyError, IndexError, TypeError):
        # TODO: error handling/logging?
        raise ValueError('invalid action')
    return sub_data, sub_schema


def _apply_action_to_form_data(action, form_data):
    new_form_data = form_data
    action_id_prefix, action_index, action_type = action[len('action_'):].rsplit('__', 2)
    if action_type == 'delete':
        deleted_item_index = int(action_index)
        parent_id_prefix = action_id_prefix
        new_form_data = {}
        for name in form_data:
            if not name.startswith(parent_id_prefix + '__') or '__' not in name[len(parent_id_prefix) + 2:]:
                new_form_data[name] = form_data[name]
            else:
                item_index, id_suffix = name[len(parent_id_prefix) + 2:].split('__', 1)
                item_index = int(item_index)
                if item_index < deleted_item_index:
                    new_form_data[name] = form_data[name]
                if item_index > deleted_item_index:
                    new_name = parent_id_prefix + '__' + str(item_index - 1) + '__' + id_suffix
                    new_form_data[new_name] = form_data[name]
    return new_form_data


def _apply_action_to_data(action, data, schema):
    action_id_prefix, action_index, action_type = action[len('action_'):].rsplit('__', 2)
    if action_type not in ('add', 'delete', 'addcolumn', 'deletecolumn'):
        raise ValueError('invalid action')
    sub_data, sub_schema = _get_sub_data_and_schema(data, schema, action_id_prefix.split('__', 1)[1])
    if action_type in ('addcolumn', 'deletecolumn') and (sub_schema["style"] != "table" or sub_schema["items"]["type"] != "array"):
        raise ValueError('invalid action')
    num_existing_items = len(sub_data)
    if action_type == 'add':
        if 'maxItems' not in sub_schema or num_existing_items < sub_schema["maxItems"]:
            sub_data.append(generate_placeholder(sub_schema["items"]))
            if isinstance(sub_data[-1], list) and sub_schema.get('style') == 'table':
                num_existing_columns = sub_schema["items"].get("minItems", 0)
                for row in sub_data:
                    num_existing_columns = max(num_existing_columns, len(row))
                while len(sub_data[-1]) < num_existing_columns:
                    sub_data[-1].append(None)
    elif action_type == 'delete':
        action_index = int(action_index)
        if ('minItems' not in sub_schema or num_existing_items > sub_schema["minItems"]) and action_index < num_existing_items:
            del sub_data[action_index]
    else:
        num_existing_columns = sub_schema["items"].get("minItems", 0)
        for row in sub_data:
            num_existing_columns = max(num_existing_columns, len(row))
        if action_type == 'addcolumn':
            if 'maxItems' not in sub_schema["items"] or num_existing_columns < sub_schema["items"]["maxItems"]:
                num_existing_columns += 1
                for row in sub_data:
                    while len(row) < num_existing_columns:
                        row.append(generate_placeholder(sub_schema["items"]["items"]))
        elif action_type == 'deletecolumn':
            if num_existing_columns > sub_schema.get("minItems", 0):
                num_existing_columns -= 1
                for row in sub_data:
                    while len(row) > num_existing_columns:
                        del row[-1]
