# coding: utf-8
"""

"""
import copy
import secrets
import typing
from copy import deepcopy
import datetime

import flask
import flask_login
import itsdangerous
from flask_babel import _

from ... import logic
from ... import models
from ...logic.actions import Action
from ...logic.action_permissions import get_sorted_actions_for_user
from ...logic.object_permissions import get_user_object_permissions
from ...logic.users import get_users
from ...logic.schemas import generate_placeholder
from ...logic.objects import create_object, create_object_batch, update_object
from ...logic.languages import get_language, get_languages, Language
from ...logic.components import get_component
from .forms import ObjectForm
from ..utils import default_format_datetime, custom_format_number, format_time
from .object_form_parser import parse_form_data
from ...logic.utils import get_translated_text
from .permissions import get_object_if_current_user_has_read_permissions
from ...models import Permissions, Object
from ...utils import FlaskResponseT


def show_object_form(
        object: typing.Optional[Object],
        action: Action,
        previous_object: typing.Optional[Object] = None,
        should_upgrade_schema: bool = False,
        placeholder_data: typing.Optional[typing.Dict[typing.Sequence[typing.Union[str, int]], typing.Any]] = None,
        possible_object_id_properties: typing.Optional[typing.Dict[str, typing.Any]] = None,
        passed_object_ids: typing.Optional[typing.List[int]] = None,
        show_selecting_modal: bool = False
) -> FlaskResponseT:

    if object is None:
        if action.type is None or action.type.disable_create_objects or action.disable_create_objects or (action.admin_only and not flask_login.current_user.is_admin):
            flask.flash(_('Creating objects with this action has been disabled.'), 'error')
            return flask.redirect(flask.url_for('.action', action_id=action.id))

    template_arguments: typing.Dict[str, typing.Any] = {
        'ENGLISH': get_language(Language.ENGLISH),
        'get_component': get_component,
        'get_object_if_current_user_has_read_permissions': get_object_if_current_user_has_read_permissions,
        'template_mode': 'form',
    }

    errors: typing.Dict[str, str] = {}
    form = ObjectForm()
    if flask.request.method != 'GET' and form.validate_on_submit():
        raw_form_data = {key: flask.request.form.getlist(key) for key in flask.request.form}
        form_data = {k: v[0] for k, v in raw_form_data.items()}
    else:
        raw_form_data = {}
        form_data = {}
    template_arguments.update({
        'errors': errors,
        'form': form,
    })

    template_arguments.update({
        'previous_schema': None,
        'diff': None
    })
    if should_upgrade_schema and previous_object is None:
        # edit object with schema upgrade
        mode = 'upgrade'
        if action.schema is None or object is None or object.schema is None or object.data is None:
            return flask.abort(400)
        schema = action.schema
        data, upgrade_warnings = logic.schemas.convert_to_schema(object.data, object.schema, action.schema)
        for upgrade_warning in upgrade_warnings:
            flask.flash(upgrade_warning, 'warning')
        template_arguments.update({
            'previous_schema': object.schema,
            'diff': logic.schemas.calculate_diff(object.data, data)
        })
    elif object is not None:
        # edit object
        mode = 'edit'
        if object.data is None or object.schema is None:
            return flask.abort(400)
        schema = object.schema
        data = copy.deepcopy(object.data)
    elif previous_object is not None:
        # create object via 'Use as Template'
        mode = 'create'
        if previous_object.data is None or previous_object.schema is None:
            return flask.abort(400)
        if should_upgrade_schema:
            if action.schema is None:
                return flask.abort(400)
            schema = action.schema
            data, upgrade_warnings = logic.schemas.convert_to_schema(previous_object.data, previous_object.schema, action.schema)
            for upgrade_warning in upgrade_warnings:
                flask.flash(upgrade_warning, 'warning')
            template_arguments.update({
                'previous_schema': previous_object.schema,
                'diff': logic.schemas.calculate_diff(previous_object.data, data)
            })
        else:
            schema = previous_object.schema
            data = logic.schemas.copy_data(previous_object.data, previous_object.schema)
        template_arguments.update({
            'previous_object_id': previous_object.id,
            'has_grant_for_previous_object': Permissions.GRANT in get_user_object_permissions(user_id=flask_login.current_user.id, object_id=previous_object.id),
        })
    else:
        # create object from scratch
        mode = 'create'
        if action.schema is None:
            return flask.abort(400)
        schema = action.schema
        data = generate_placeholder(action.schema)
        if not isinstance(data, dict):
            return flask.abort(400)
        if placeholder_data:
            _apply_placeholder_data(placeholder_data, data)
        template_arguments.update({
            'previous_object_id': None,
            'has_grant_for_previous_object': False,
        })

    if passed_object_ids:
        has_grant_for_first_passed_object = Permissions.GRANT in get_user_object_permissions(user_id=flask_login.current_user.id, object_id=passed_object_ids[0])
    else:
        has_grant_for_first_passed_object = False
    template_arguments.update({
        'has_grant_for_first_passed_object': has_grant_for_first_passed_object,
    })

    if not isinstance(data, dict):
        return flask.abort(400)
    if not isinstance(schema, dict):
        return flask.abort(400)

    template_arguments.update({
        'data': data,
        'schema': schema,
    })

    if object is None:
        # allow creating an instrument log entry for a newly created object
        if not flask.current_app.config['DISABLE_INSTRUMENTS'] and action is not None and action.instrument is not None and flask_login.current_user in action.instrument.responsible_users:
            may_create_log_entry = True
            create_log_entry_default = action.instrument.create_log_entry_default
            instrument_log_categories = logic.instrument_log_entries.get_instrument_log_categories(action.instrument.id)
        else:
            may_create_log_entry = False
            create_log_entry_default = False
            instrument_log_categories = []
        template_arguments.update({
            'may_create_log_entry': may_create_log_entry,
            'create_log_entry_default': create_log_entry_default,
            'instrument_log_categories': instrument_log_categories,
        })

    template_arguments.update({
        'form_data': form_data,
    })

    template_arguments.update(get_object_form_template_kwargs(object.id if object is not None else None))

    actual_file_names_by_id = {
        file_id: file_names[0]
        for file_id, file_names in template_arguments['file_names_by_id'].items()
    }
    context_id = template_arguments['context_id']

    if "action_submit" in form_data:
        batch_names = _handle_batch_names(schema, form_data, raw_form_data, errors)
        object_data, parsing_errors = parse_form_data(raw_form_data, schema, file_names_by_id=actual_file_names_by_id, previous_data=data)
        errors.update(parsing_errors)
        if batch_names is not None:
            for key in errors:
                if key.startswith('object__name__'):
                    errors[key] += _(' Batch numbering resulted in name: %(name)s', name=f'"{batch_names[0]["en"]}"' if len(batch_names[0]) == 1 else ', '.join([f'"{name}" ({get_translated_text(logic.languages.get_language_by_lang_code(lang_code).names)})' for lang_code, name in batch_names[0].items()]))
        if object_data is not None and not errors and batch_names is not None:
            data_sequence = []
            object_data = typing.cast(typing.Dict[str, typing.Any], object_data)
            for name in batch_names:
                object_data['name']['text'] = name
                data_sequence.append(deepcopy(object_data))
                try:
                    logic.schemas.validate(data_sequence[-1], schema, strict=True, file_names_by_id=actual_file_names_by_id)
                except logic.errors.ValidationError as e:
                    batch_error_message = _(
                        '"%(error)s" for object name %(name)s',
                        error=e.raw_message,
                        name=f'"{name["en"]}"' if len(name) == 1 else ', '.join(
                            [
                                f'"{n}" ({get_translated_text(logic.languages.get_language_by_lang_code(lang_code).names)})'
                                for lang_code, n in name.items()
                            ]
                        )
                    )
                    if 'batch' in errors:
                        errors['batch'] += '\n' + batch_error_message
                    else:
                        errors['batch'] = batch_error_message
        if form_data['action_submit'] == 'inline_edit' and errors:
            return flask.jsonify({
                'errors': errors
            }), 400
        template_arguments.update({
            'errors_by_title': get_errors_by_title(errors, schema)
        })
        if object_data is not None and not errors:
            object_data = typing.cast(typing.Dict[str, typing.Any], object_data)
            for markdown in logic.markdown_to_html.get_markdown_from_object_data(object_data):
                markdown_as_html = logic.markdown_to_html.markdown_to_safe_html(markdown)
                logic.markdown_images.mark_referenced_markdown_images_as_permanent(markdown_as_html)
            referenced_temporary_file_ids = sorted(logic.temporary_files.get_referenced_temporary_file_ids(object_data))
            if object is None:
                copy_permissions_object_id, permissions_for_group_id, permissions_for_project_id = _parse_permissions_ids(form_data)
                read_permissions_to_all_users = form_data.get('all_users_read_permissions') == '1'
                permanent_file_names_by_id = {}
                permanent_file_map = {}
                for ind, file_id in enumerate(referenced_temporary_file_ids):
                    permanent_file_map[file_id] = ind
                    permanent_file_names_by_id[ind] = actual_file_names_by_id[-file_id]
                logic.temporary_files.replace_file_reference_ids(object_data, permanent_file_map)
                if batch_names is not None:
                    objects = create_object_batch(
                        action_id=action.id,
                        data_sequence=data_sequence,
                        user_id=flask_login.current_user.id,
                        copy_permissions_object_id=copy_permissions_object_id,
                        permissions_for_group_id=permissions_for_group_id,
                        permissions_for_project_id=permissions_for_project_id,
                        permissions_for_all_users=Permissions.READ if read_permissions_to_all_users else None,
                        data_validator_arguments={'file_names_by_id': permanent_file_names_by_id},
                        validate_data=False     # validated on data_sequence creation
                    )
                else:
                    objects = [create_object(
                        action_id=action.id,
                        data=object_data,
                        user_id=flask_login.current_user.id,
                        previous_object_id=previous_object.id if previous_object is not None else None,
                        schema=previous_object.schema if previous_object is not None and not should_upgrade_schema else None,
                        copy_permissions_object_id=copy_permissions_object_id,
                        permissions_for_group_id=permissions_for_group_id,
                        permissions_for_project_id=permissions_for_project_id,
                        permissions_for_all_users=Permissions.READ if read_permissions_to_all_users else None,
                        data_validator_arguments={'file_names_by_id': permanent_file_names_by_id}
                    )]
                object_ids = [object.id for object in objects]
                if action.instrument_id and not flask.current_app.config['DISABLE_INSTRUMENTS'] and may_create_log_entry:
                    if 'create_instrument_log_entry' in form_data:
                        category_ids = []
                        for category_id in raw_form_data.get('instrument_log_categories', []):
                            try:
                                if int(category_id) in [category.id for category in instrument_log_categories]:
                                    category_ids.append(int(category_id))
                            except Exception:
                                pass
                        log_entry = logic.instrument_log_entries.create_instrument_log_entry(
                            instrument_id=action.instrument_id,
                            user_id=flask_login.current_user.id,
                            content='',
                            category_ids=category_ids
                        )
                        for object_id in object_ids:
                            logic.instrument_log_entries.create_instrument_log_object_attachment(
                                instrument_log_entry_id=log_entry.id,
                                object_id=object_id
                            )
                logic.temporary_files.copy_temporary_files(file_ids=referenced_temporary_file_ids, context_id=context_id, user_id=flask_login.current_user.id, object_ids=object_ids)
                logic.temporary_files.delete_temporary_files(context_id=context_id)
                if len(object_ids) == 1:
                    flask.flash(_('The object was created successfully.'), 'success')
                    return flask.redirect(flask.url_for('.object', object_id=object_ids[0]))
                else:
                    flask.flash(_('The objects were created successfully.'), 'success')
                    return flask.redirect(flask.url_for('.objects', ids=','.join([str(object_id) for object_id in object_ids])))
            else:
                if object_data != object.data or schema != object.schema:
                    actual_temporary_file_id_map = logic.temporary_files.copy_temporary_files(file_ids=referenced_temporary_file_ids, context_id=context_id, user_id=flask_login.current_user.id, object_ids=[object.id])
                    logic.temporary_files.delete_temporary_files(context_id=context_id)
                    logic.temporary_files.replace_file_reference_ids(object_data, actual_temporary_file_id_map)
                    update_object(object_id=object.id, user_id=flask_login.current_user.id, data=object_data, schema=schema)
                    flask.flash(_('The object was updated successfully.'), 'success')
                return flask.redirect(flask.url_for('.object', object_id=object.id))

    _update_recipes_for_input(schema)

    if object is None:
        # alternatives to default permissions
        user_groups = logic.groups.get_user_groups(flask_login.current_user.id)
        user_projects = logic.projects.get_user_projects(flask_login.current_user.id, include_groups=True)
        template_arguments.update({
            'can_copy_permissions': True,
            'user_groups': user_groups,
            'user_projects': user_projects
        })

        return flask.render_template(
            'objects/forms/form_create.html',
            action_id=action.id,
            action=action,
            possible_properties=possible_object_id_properties,
            passed_object_ids=passed_object_ids,
            show_selecting_modal=show_selecting_modal,
            **template_arguments
        )
    else:
        return flask.render_template(
            'objects/forms/form_edit.html',
            object_id=object.object_id,
            mode=mode,
            **template_arguments
        )


def _apply_placeholder_data(
        placeholder_data: typing.Dict[typing.Sequence[typing.Union[str, int]], typing.Any],
        data: typing.Dict[str, typing.Any]
) -> None:
    for path, value in placeholder_data.items():
        try:
            sub_data: typing.Optional[typing.Union[typing.List[typing.Any], typing.Dict[str, typing.Any]]] = data
            for step in path[:-1]:
                if isinstance(sub_data, list) and isinstance(step, int):
                    sub_data = sub_data[step]
                elif isinstance(sub_data, dict) and isinstance(step, str):
                    sub_data = sub_data[step]
                else:
                    sub_data = None
                    break
            step = path[-1]
            if isinstance(sub_data, list) and isinstance(step, int):
                sub_data[step] = value
            elif isinstance(sub_data, dict) and isinstance(step, str):
                sub_data[step] = value
        except Exception:
            # Ignore invalid placeholder data
            pass


def _parse_permissions_ids(
        form_data: typing.Dict[str, typing.Any]
) -> typing.Tuple[typing.Optional[int], typing.Optional[int], typing.Optional[int]]:
    """
    Parse and return the IDs for assigning permissions.

    :param form_data: the filtered form data
    :return: the object, basic group and project group IDs as a tuple
    """
    if form_data.get('permissions_method') == 'copy_permissions':
        copy_permissions_object_id_str = form_data.get('copy_permissions_object_id')
        if copy_permissions_object_id_str:
            try:
                copy_permissions_object_id = int(copy_permissions_object_id_str)
                if Permissions.READ in get_user_object_permissions(copy_permissions_object_id, flask_login.current_user.id):
                    return copy_permissions_object_id, None, None
            except Exception:
                pass
            flask.flash(_("Unable to copy permissions. Default permissions will be applied."), 'error')
        else:
            flask.flash(_("No object selected. Default permissions will be applied."), 'error')
        return None, None, None
    if form_data.get('permissions_method') == 'permissions_for_group':
        permissions_for_group_id_str = form_data.get('permissions_for_group_group_id')
        if permissions_for_group_id_str:
            try:
                permissions_for_group_id = int(permissions_for_group_id_str)
                if flask_login.current_user.id in logic.groups.get_group_member_ids(permissions_for_group_id):
                    return None, permissions_for_group_id, None
            except Exception:
                pass
            flask.flash(_("Unable to grant permissions to basic group. Default permissions will be applied."), 'error')
        else:
            flask.flash(_("No basic group selected. Default permissions will be applied."), 'error')
        return None, None, None
    if form_data.get('permissions_method') == 'permissions_for_project':
        permissions_for_project_id_str = form_data.get('permissions_for_project_project_id')
        if permissions_for_project_id_str:
            try:
                permissions_for_project_id = int(permissions_for_project_id_str)
                if flask_login.current_user.id in logic.projects.get_project_member_user_ids_and_permissions(permissions_for_project_id, include_groups=True):
                    return None, None, permissions_for_project_id
            except Exception:
                pass
            flask.flash(_("Unable to grant permissions to project group. Default permissions will be applied."), 'error')
        else:
            flask.flash(_("No project group selected. Default permissions will be applied."), 'error')
        return None, None, None
    return None, None, None


def _handle_batch_names(
        schema: typing.Dict[str, typing.Any],
        form_data: typing.Dict[str, typing.Any],
        raw_form_data: typing.Dict[str, typing.List[typing.Any]],
        errors: typing.Dict[str, str]
) -> typing.Optional[typing.List[typing.Dict[str, str]]]:
    """
    Generate object names for a batch.

    :param schema: the object schema
    :param form_data: the filtered form data, to read values from
    :param raw_form_data: the raw form data, to write the example name into
    :param errors: an error dict, to write errors to
    :return: the batch names as a list of multi-language dicts, or None
    """
    if not schema.get('batch', False) or 'input_num_batch_objects' not in form_data:
        return None

    # parse the number of objects in the batch
    try:
        # the form allows notations like '1.2e1' for '12', however Python can only parse these as floats
        num_objects_in_batch_float = float(form_data['input_num_batch_objects'])
        if num_objects_in_batch_float == int(num_objects_in_batch_float):
            num_objects_in_batch = int(num_objects_in_batch_float)
        else:
            num_objects_in_batch = None
    except ValueError:
        num_objects_in_batch = None
    if num_objects_in_batch is not None:
        form_data['input_num_batch_objects'] = str(num_objects_in_batch)
    if num_objects_in_batch is None or num_objects_in_batch <= 0:
        errors['input_num_batch_objects'] = _('The number of objects in batch must be an positive integer.')
        return None
    if num_objects_in_batch > flask.current_app.config['MAX_BATCH_SIZE']:
        errors['input_num_batch_objects'] = _('The maximum number of objects in one batch is %(max_batch_size)s.', max_batch_size=flask.current_app.config['MAX_BATCH_SIZE'])
        return None
    # parse the first number
    try:
        # the form allows notations like '1.2e1' for '12', however Python can only parse these as floats
        first_number_float = float(form_data['input_first_number_batch'])
        if first_number_float == int(first_number_float):
            first_number = int(first_number_float)
        else:
            first_number = None
    except ValueError:
        first_number = None
    if first_number is None:
        errors['input_first_number_batch'] = _('The first number must be an integer.')
        return None
    form_data['input_first_number_batch'] = str(first_number)

    # The object name might need the batch number to match the pattern
    name_suffix_format = schema.get('batch_name_format', '{:d}')
    try:
        example_name_suffix = name_suffix_format.format(first_number)
    except (ValueError, KeyError):
        name_suffix_format = '{:d}'
        example_name_suffix = ''
    if 'object__name__text' in form_data:
        batch_base_name = {'en': form_data['object__name__text']}
        raw_form_data['object__name__text'] = [batch_base_name['en'] + example_name_suffix]
    else:
        enabled_languages_raw: typing.Union[str, typing.List[str]] = form_data.get('object__name__text_languages', [])
        if isinstance(enabled_languages_raw, str):
            enabled_languages = [enabled_languages_raw]
        else:
            enabled_languages = enabled_languages_raw
        if 'en' not in enabled_languages:
            enabled_languages.append('en')
        batch_base_name = {}
        for language_code in enabled_languages:
            batch_base_name[language_code] = form_data.get('object__name__text_' + language_code, '')
            raw_form_data['object__name__text_' + language_code] = [batch_base_name[language_code] + example_name_suffix]
    return [
        {
            language_code: batch_base_name_str + (name_suffix_format.format(i) if name_suffix_format else '')
            for language_code, batch_base_name_str in batch_base_name.items()
        }
        for i in range(first_number, first_number + num_objects_in_batch)
    ]


def _update_recipes_for_input(schema: typing.Dict[str, typing.Any]) -> None:
    """
    Update a schema so that recipes contain the values and types used for input instead of the internal representation.

    :param schema: the schema to update
    """
    if schema['type'] == 'object':
        if 'recipes' in schema:
            for recipe in schema['recipes']:
                recipe['name'] = get_translated_text(recipe['name'])
                for property_name in recipe['property_values']:
                    property_schema = schema['properties'][property_name]
                    property_value = recipe['property_values'][property_name]
                    if property_schema['type'] == 'datetime':
                        if property_value:
                            value = default_format_datetime(property_value['utc_datetime'])
                        else:
                            value = None
                        property_value = {
                            'value': value,
                            'type': 'datetime'
                        }
                    elif property_schema['type'] == 'quantity':
                        if property_value:
                            units = property_value['units']
                            if units in ['min', 'h']:
                                value = format_time(property_value['magnitude_in_base_units'], units)
                            else:
                                value = custom_format_number(property_value['magnitude'])
                        else:
                            units = None
                            value = None
                        property_value = {
                            'value': value,
                            'units': units,
                            'type': 'quantity'
                        }
                    elif property_schema['type'] == 'text':
                        if property_value:
                            value = property_value['text']
                        else:
                            value = None
                        if 'choices' in property_schema:
                            property_value = {
                                'value': value,
                                'type': 'choice'
                            }
                        elif 'markdown' in property_schema and property_schema['markdown']:
                            property_value = {
                                'value': value,
                                'type': 'markdown'
                            }
                        elif 'multiline' in property_schema and property_schema['multiline']:
                            property_value = {
                                'value': value,
                                'type': 'multiline'
                            }
                        else:
                            property_value = {
                                'value': value,
                                'type': 'text'
                            }
                    elif property_schema['type'] == 'bool':
                        property_value = {
                            'value': property_value['value'],
                            'type': 'bool'
                        }
                    property_value['title'] = get_translated_text(property_schema['title'])
                    recipe['property_values'][property_name] = property_value
        for property_schema in schema['properties'].values():
            _update_recipes_for_input(property_schema)
    elif schema['type'] == 'array':
        _update_recipes_for_input(schema['items'])


def _get_sub_data_and_schema(data: typing.Dict[str, typing.Any], schema: typing.Dict[str, typing.Any], id_prefix: str) -> typing.Tuple[typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]], typing.Dict[str, typing.Any]]:
    sub_data: typing.Any
    sub_data = data
    sub_schema = schema
    try:
        key: typing.Union[str, int]
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
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ValueError('invalid action') from exc
    return sub_data, sub_schema


def _apply_action_to_form_data(action: str, form_data: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
    new_form_data = form_data
    action_id_prefix, action_index_str, action_type = action[len('action_'):].rsplit('__', 2)
    if action_type == 'delete':
        deleted_item_index = int(action_index_str)
        parent_id_prefix = action_id_prefix
        new_form_data = {}
        for name in form_data:
            if not name.startswith(parent_id_prefix + '__') or '__' not in name[len(parent_id_prefix) + 2:]:
                new_form_data[name] = form_data[name]
            else:
                item_index_str, id_suffix = name[len(parent_id_prefix) + 2:].split('__', 1)
                item_index = int(item_index_str)
                if item_index < deleted_item_index:
                    new_form_data[name] = form_data[name]
                if item_index > deleted_item_index:
                    new_name = parent_id_prefix + '__' + str(item_index - 1) + '__' + id_suffix
                    new_form_data[new_name] = form_data[name]
    return new_form_data


def get_object_form_template_kwargs(object_id: typing.Optional[int]) -> typing.Dict[str, typing.Any]:
    template_kwargs = {
        'datetime': datetime,
        'languages': get_languages(),
    }

    # actions and action types
    sorted_actions = get_sorted_actions_for_user(
        user_id=flask_login.current_user.id
    )
    fed_action_type_id_map = {
        action_type.id: action_type.fed_id
        for action_type in logic.action_types.get_action_types()
        if action_type.fed_id is not None and action_type.fed_id < 0
    }
    action_type_id_by_action_id = {
        action_id: fed_action_type_id_map.get(action_type_id, action_type_id) if action_type_id is not None else None
        for action_id, action_type_id in logic.actions.get_action_type_ids_for_action_ids(None).items()
    }
    template_kwargs.update({
        'sorted_actions': sorted_actions,
        'action_type_id_by_action_id': action_type_id_by_action_id,
        'ActionType': models.ActionType,
    })

    # temporary file upload for file fields
    context_id_serializer = itsdangerous.URLSafeTimedSerializer(flask.current_app.config['SECRET_KEY'], salt='temporary-file-upload')
    if 'context_id_token' in flask.request.form:
        context_id_token = flask.request.form.get('context_id_token', '')
        try:
            user_id, context_id = context_id_serializer.loads(context_id_token, max_age=flask.current_app.config['TEMPORARY_FILE_TIME_LIMIT'])
        except itsdangerous.BadSignature:
            return flask.abort(400)
        if user_id != flask_login.current_user.id:
            return flask.abort(400)
    else:
        context_id = secrets.token_hex(32)
        context_id_token = context_id_serializer.dumps((flask_login.current_user.id, context_id))

    if object_id is not None:
        file_names_by_id = logic.files.get_file_names_by_id_for_object(object_id)
    else:
        file_names_by_id = {}
    temporary_files = logic.temporary_files.get_files_for_context_id(context_id=context_id)
    for temporary_file in temporary_files:
        file_names_by_id[-temporary_file.id] = temporary_file.file_name, temporary_file.file_name

    template_kwargs.update({
        'context_id': context_id,
        'context_id_token': context_id_token,
        'file_names_by_id': file_names_by_id,
    })

    # previously used tags
    tags = [
        {
            'name': tag.name,
            'uses': tag.uses
        }
        for tag in logic.tags.get_tags()
    ]
    template_kwargs.update({
        'tags': tags,
    })

    # users
    users = get_users(exclude_hidden=not flask_login.current_user.is_admin or not flask_login.current_user.settings['SHOW_HIDDEN_USERS_AS_ADMIN'])
    users.sort(key=lambda user: user.id)
    template_kwargs.update({
        'users': users,
    })

    return template_kwargs


def _get_title_by_property_path(
        schema: typing.Any,
        property_path: typing.Sequence[str],
        *,
        index: typing.Optional[str] = None,
        is_root_object: bool = True
) -> str:
    if not isinstance(schema, dict):
        return ''
    schema_title = get_translated_text(schema.get('title', ''))
    if index:
        schema_title += ' #' + index
    if len(property_path) == 0 or not schema_title:
        return schema_title
    if schema.get('type') == 'array':
        return ('' if is_root_object else f'{schema_title} ➜ ') + _get_title_by_property_path(schema.get('items'), property_path[1:], is_root_object=False, index=property_path[0])
    if schema.get('type') == 'object':
        property_schemas = schema.get('properties')
        if isinstance(property_schemas, dict):
            return ('' if is_root_object else f'{schema_title} ➜ ') + _get_title_by_property_path(property_schemas.get(property_path[0]), property_path[1:], is_root_object=False)
    return ''


def get_errors_by_title(
        errors: typing.Dict[str, str],
        schema: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Set[str]]:
    # filter out errors for required fields or None array entries with existing error messages
    missing_required_fields = {}
    invalid_type_entries = {}
    for name, message in errors.items():
        if name.startswith('object__') and name.endswith('__hidden') and message.startswith('missing required property "'):
            parent_property_path = name.split('__')[1:-1]
            property_name = message.split('"')[1]
            missing_required_fields[tuple(parent_property_path + [property_name])] = (name, message)
        if name.startswith('object__') and name.endswith('__hidden') and message.startswith('invalid type (at '):
            parent_property_path = name.split('__')[1:-1]
            property_name = message.split('(at ')[1].split(')')[0]
            invalid_type_entries[tuple(parent_property_path + [property_name])] = (name, message)
    ignorable_errors = set()
    for name, message in errors.items():
        if name.startswith('object__'):
            property_path = tuple(name.split('__')[1:-1])
            for potential_ignorable_errors in (missing_required_fields, invalid_type_entries):
                if tuple(property_path) in potential_ignorable_errors:
                    ignorable_errors.add(potential_ignorable_errors[property_path])

    # construct title -> error messages dict
    errors_by_title: typing.Dict[str, typing.Set[str]] = {}
    for name, message in errors.items():
        if (name, message) in ignorable_errors:
            continue
        title = ''
        if name.startswith('object__'):
            property_path = tuple(name.split('__')[1:-1])
            if property_path:
                title = _get_title_by_property_path(schema, property_path)
        elif name == 'batch':
            title = _('Batch Object Creation')
        if not title:
            title = _('Unknown (%(name)s)', name=name)
        if title in errors_by_title:
            errors_by_title[title].update(message.splitlines())
        else:
            errors_by_title[title] = set(message.splitlines())
    return errors_by_title
