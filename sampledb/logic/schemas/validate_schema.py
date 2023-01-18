# coding: utf-8
"""
Implementation of validate_schema(schema)
"""


import datetime
import math
import string
import typing
import urllib.parse
import re

import pint

from ..errors import ValidationError, ActionDoesNotExistError, InvalidNumberError, InvalidTemplateIDError, RecursiveTemplateError
from .utils import units_are_valid
from .validate import validate
from .templates import substitute_templates
from .conditions import validate_condition_schema
from ..languages import get_language_codes
from .. import datatypes

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def validate_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.Optional[typing.List[str]] = None,
        *,
        parent_conditions: typing.Optional[typing.List[typing.Tuple[typing.List[str], typing.Dict[str, typing.Any]]]] = None,
        invalid_template_action_ids: typing.Sequence[int] = (),
        strict: bool = False,
        all_language_codes: typing.Optional[typing.Set[str]] = None
) -> None:
    """
    Validates the given schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param parent_conditions: conditions defined in parent objects
    :param invalid_template_action_ids: IDs of actions that may not be used as templates to prevent recursion
    :param strict: whether the schema should be evaluated in strict mode, or backwards compatible otherwise
    :param all_language_codes: the set of existing language codes, or None
    :raise ValidationError: if the schema is invalid.
    """
    if all_language_codes is None:
        all_language_codes = get_language_codes()
    if path is None:
        path = []
    if not isinstance(schema, dict):
        raise ValidationError('invalid schema (must be dict)', path)
    if 'type' not in schema:
        raise ValidationError('invalid schema (must contain type)', path)
    if not isinstance(schema['type'], str):
        raise ValidationError('invalid schema (type must be str)', path)
    if 'title' not in schema:
        raise ValidationError('invalid schema (must contain title)', path)
    if not isinstance(schema['title'], str) and not isinstance(schema['title'], dict):
        raise ValidationError('title must be str or dict', path)
    if isinstance(schema['title'], dict):
        if 'en' not in schema['title']:
            raise ValidationError('title must include an english translation', path)
        for lang_code in schema['title'].keys():
            if lang_code not in all_language_codes:
                raise ValidationError('title must only contain known languages', path)
        for note_text in schema['title'].values():
            if not isinstance(note_text, str):
                raise ValidationError('title must only contain text', path)
    if 'style' in schema and not isinstance(schema['style'], str):
        raise ValidationError('style must only contain text', path)
    if 'conditions' in schema:
        if parent_conditions is not None:
            if not isinstance(schema['conditions'], list):
                raise ValidationError('conditions must be a list', path)
            for i, condition in enumerate(schema['conditions']):
                parent_conditions.append((path + [str(i)], condition))
        else:
            raise ValidationError('only schemas with an object parent may contain conditions', path)
    if not isinstance(schema.get('may_copy', True), bool):
        raise ValidationError('may_copy must be bool', path)

    if path == [] and schema['type'] != 'object':
        raise ValidationError('invalid schema (root must be an object)', path)
    if schema['type'] == 'array':
        return _validate_array_schema(schema, path, invalid_template_action_ids=invalid_template_action_ids, strict=strict, all_language_codes=all_language_codes)
    elif schema['type'] == 'object':
        return _validate_object_schema(schema, path, invalid_template_action_ids=invalid_template_action_ids, strict=strict, all_language_codes=all_language_codes)
    elif schema['type'] == 'text':
        return _validate_text_schema(schema, path, all_language_codes=all_language_codes)
    elif schema['type'] == 'datetime':
        return _validate_datetime_schema(schema, path, all_language_codes=all_language_codes)
    elif schema['type'] == 'bool':
        return _validate_bool_schema(schema, path, all_language_codes=all_language_codes)
    elif schema['type'] == 'quantity':
        return _validate_quantity_schema(schema, path, all_language_codes=all_language_codes)
    elif schema['type'] == 'sample':
        return _validate_sample_schema(schema, path, all_language_codes=all_language_codes)
    elif schema['type'] == 'measurement':
        return _validate_measurement_schema(schema, path, all_language_codes=all_language_codes)
    elif schema['type'] == 'object_reference':
        return _validate_object_reference_schema(schema, path, all_language_codes=all_language_codes)
    elif schema['type'] == 'tags':
        return _validate_tags_schema(schema, path, strict=strict)
    elif schema['type'] == 'hazards':
        return _validate_hazards_schema(schema, path, all_language_codes=all_language_codes)
    elif schema['type'] == 'user':
        return _validate_user_schema(schema, path, all_language_codes=all_language_codes)
    elif schema['type'] == 'plotly_chart':
        return _validate_plotly_chart_schema(schema, path, all_language_codes=all_language_codes)
    else:
        raise ValidationError('invalid type', path)


def _validate_note_in_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    if 'note' in schema and not isinstance(schema['note'], str) and not isinstance(schema['note'], dict):
        raise ValidationError('note must be str or dict', path)
    if 'note' in schema and isinstance(schema['note'], dict):
        if 'en' not in schema['note']:
            raise ValidationError('note must include an english translation', path)
        for lang_code in schema['note'].keys():
            if lang_code not in all_language_codes:
                raise ValidationError('note must only contain known languages', path)
        for note_text in schema['note'].values():
            if not isinstance(note_text, str):
                raise ValidationError('note must only contain text', path)


def _validate_hazards_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validate the given GHS hazards schema and raise a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'dataverse_export', 'scicat_export', 'may_copy', 'style'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    if path != ['hazards']:
        raise ValidationError('GHS hazards must be a top-level entry named "hazards"', path)

    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_array_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        invalid_template_action_ids: typing.Sequence[int] = (),
        strict: bool = False,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given array schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param invalid_template_action_ids: IDs of actions that may not be used as templates to prevent recursion
    :param strict: whether the schema should be evaluated in strict mode, or backwards compatible otherwise
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'items', 'style', 'minItems', 'maxItems', 'defaultItems', 'default', 'may_copy', 'conditions'}
    required_keys = {'type', 'title', 'items'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    has_min_items = False
    if 'minItems' in schema:
        if not isinstance(schema['minItems'], int):
            raise ValidationError('minItems must be an integer', path)
        elif schema['minItems'] < 0:
            raise ValidationError('minItems must not be negative', path)
        else:
            has_min_items = True
    has_max_items = False
    if 'maxItems' in schema:
        if not isinstance(schema['maxItems'], int):
            raise ValidationError('maxItems must be an integer', path)
        elif schema['maxItems'] < 0:
            raise ValidationError('maxItems must not be negative', path)
        else:
            has_max_items = True
    has_default_items = False
    if 'defaultItems' in schema:
        if not isinstance(schema['defaultItems'], int):
            raise ValidationError('defaultItems must be an integer', path)
        elif schema['defaultItems'] < 0:
            raise ValidationError('defaultItems must not be negative', path)
        else:
            has_default_items = True
    if has_min_items and has_max_items:
        if schema['minItems'] > schema['maxItems']:
            raise ValidationError('minItems must be less than or equal to maxItems', path)
    if has_min_items and has_default_items:
        if schema['minItems'] > schema['defaultItems']:
            raise ValidationError('minItems must be less than or equal to defaultItems', path)
    if has_default_items and has_max_items:
        if schema['defaultItems'] > schema['maxItems']:
            raise ValidationError('defaultItems must be less than or equal to maxItems', path)
    validate_schema(schema['items'], path + ['[?]'], invalid_template_action_ids=invalid_template_action_ids, strict=strict, all_language_codes=all_language_codes)
    if 'default' in schema:
        if has_default_items:
            raise ValidationError('default and defaultItems are mutually exclusive', path)
        validate(schema['default'], schema, path + ['(default)'], strict=strict)


def _validate_tags_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        strict: bool = False
) -> None:
    """
    Validates the given tags schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param strict: whether the schema should be evaluated in strict mode, or backwards compatible otherwise
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default', 'dataverse_export', 'scicat_export', 'may_copy', 'style'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if 'default' in schema:
        validate({'_type': 'tags', 'tags': schema['default']}, schema, path + ['(default)'], strict=strict)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    if path != ['tags']:
        raise ValidationError('Tags must be a top-level entry named "tags"', path)


def _validate_object_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        invalid_template_action_ids: typing.Sequence[int] = (),
        strict: bool = False,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param invalid_template_action_ids: IDs of actions that may not be used as templates to prevent recursion
    :param strict: whether the schema should be evaluated in strict mode, or backwards compatible otherwise
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    try:
        substitute_templates(schema, invalid_template_action_ids)
    except ActionDoesNotExistError:
        raise ValidationError('schema template action does not exist', path)
    except InvalidNumberError:
        raise ValidationError('template must be an integer', path)
    except RecursiveTemplateError:
        raise ValidationError('template must not recursively include itself', path)
    except InvalidTemplateIDError:
        raise ValidationError('template must be the ID of a template action', path)

    if schema.get('template') is not None:
        invalid_template_action_ids = list(invalid_template_action_ids) + [typing.cast(int, schema['template'])]

    valid_keys = {'type', 'title', 'properties', 'propertyOrder', 'required', 'default', 'may_copy', 'style', 'template', 'recipes', 'note', 'show_more'}
    if not path:
        # the top level object may contain a list of properties to be displayed in a table of objects
        valid_keys.add('displayProperties')
        valid_keys.add('batch')
        valid_keys.add('batch_name_format')
        valid_keys.add('notebookTemplates')
    if path:
        # the top level object must not have any conditions
        valid_keys.add('conditions')
    required_keys = {'type', 'title', 'properties'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)

    if not isinstance(schema['properties'], dict):
        raise ValidationError('properties must be dict', path)
    property_conditions: typing.List[typing.Tuple[typing.List[str], typing.Dict[str, typing.Any]]] = []
    property_schemas = {}
    for property_name, property_schema in schema['properties'].items():
        property_name_valid = True
        if not property_name:
            property_name_valid = False
        if '__' in property_name:
            property_name_valid = False
        if strict and property_name_valid:
            # property name may only consist of ascii characters, digits and underscores
            if not all(c in (string.ascii_letters + string.digits + '_') for c in property_name):
                property_name_valid = False
            # property name must start with a character
            if property_name[0] not in string.ascii_letters:
                property_name_valid = False
            # property name must not end with an underscore
            if property_name.endswith('_'):
                property_name_valid = False
        if not property_name_valid:
            raise ValidationError('invalid property name: {}'.format(property_name), path)

        validate_schema(
            property_schema,
            path + [property_name],
            parent_conditions=property_conditions,
            invalid_template_action_ids=invalid_template_action_ids,
            strict=strict,
            all_language_codes=all_language_codes
        )
        property_schemas[property_name] = property_schema
    for condition_path, condition in property_conditions:
        if not isinstance(condition, dict) or not isinstance(condition.get('type'), str):
            raise ValidationError('condition must be a dict containg the key type', condition_path)
        validate_condition_schema(condition, property_schemas, condition_path)

    if 'required' in schema:
        if not isinstance(schema['required'], list):
            raise ValidationError('required must be list', path)
        for i, property_name in enumerate(schema['required']):
            if property_name not in schema['properties']:
                raise ValidationError('unknown required property: {}'.format(property_name), path)
            if property_name in schema['required'][:i]:
                raise ValidationError('duplicate required property: {}'.format(property_name), path)
            # the name property in the root object is always required and may not be conditional
            if schema['properties'][property_name].get('conditions') and property_name == 'name' and path == []:
                raise ValidationError('conditional required property: {}'.format(property_name), path)

    if 'hazards' in schema['properties'] and schema['properties']['hazards']['type'] == 'hazards' and 'hazards' not in schema.get('required', []):
        raise ValidationError('GHS hazards may not be optional', path)

    if not path:
        if 'name' not in schema['properties'] or schema['properties']['name']['type'] != 'text':
            raise ValidationError('Schema must include a text property "name"', path)
        if schema['properties']['name'].get('multiline') or schema['properties']['name'].get('markdown'):
            raise ValidationError('Object name must not be multiline or markdown text', path)
        if 'required' not in schema or 'name' not in schema['required']:
            raise ValidationError('"name" must be a required property for the root object', path)

    if 'propertyOrder' in schema:
        if not isinstance(schema['propertyOrder'], list):
            raise ValidationError('propertyOrder must be list', path)
        for i, property_name in enumerate(schema['propertyOrder']):
            if property_name not in schema['properties']:
                raise ValidationError('unknown propertyOrder property: {}'.format(property_name), path)
            if property_name in schema['propertyOrder'][:i]:
                raise ValidationError('duplicate propertyOrder property: {}'.format(property_name), path)

    if 'default' in schema:
        validate(schema['default'], schema, strict=strict)

    if 'displayProperties' in schema:
        if not isinstance(schema['displayProperties'], list):
            raise ValidationError('displayProperties must be list', path)
        for i, property_name in enumerate(schema['displayProperties']):
            if property_name not in schema['properties']:
                raise ValidationError('unknown display property: {}'.format(property_name), path)
            if property_name in schema['displayProperties'][:i]:
                raise ValidationError('duplicate displayProperties property: {}'.format(property_name), path)

    if 'batch' in schema:
        if not isinstance(schema['batch'], bool):
            raise ValidationError('batch must be bool', path)

    if 'batch_name_format' in schema:
        if not schema.get('batch', False):
            raise ValidationError('batch must be True for batch_name_format to be set', path)
        if not isinstance(schema['batch_name_format'], str):
            raise ValidationError('batch_name_format must be a string', path)
        try:
            schema['batch_name_format'].format(1)
        except (ValueError, KeyError):
            raise ValidationError('invalid batch_name_format', path)

    if 'notebookTemplates' in schema:
        _validate_notebook_templates(schema['notebookTemplates'])

    if 'recipes' in schema:
        for recipe in schema['recipes']:
            if 'name' not in recipe:
                raise ValidationError('missing recipe name', path + ['(recipes)'])
            if not isinstance(recipe['name'], str) and not isinstance(recipe['name'], dict):
                raise ValidationError('recipe name must be str or dict', path + ['(recipes)'])
            if isinstance(recipe['name'], dict):
                if 'en' not in recipe['name']:
                    raise ValidationError('recipe name must include an english translation', path + ['(recipes)'])
                for lang_code in recipe['name'].keys():
                    if lang_code not in all_language_codes:
                        raise ValidationError('recipe name must only contain known languages', path + ['(recipes)'])
                for name_text in recipe['name'].values():
                    if not isinstance(name_text, str):
                        raise ValidationError('recipe name must only contain text', path + ['(recipes)'])
            if 'property_values' not in recipe:
                raise ValidationError('missing property_values', path + ['(recipes)'])
            for property_name in recipe['property_values']:
                if property_name not in schema['properties'].keys():
                    raise ValidationError('unknown property: {}'.format(property_name), path + ['(recipes)'])
                if schema['properties'][property_name]['type'] not in ['text', 'quantity', 'datetime', 'bool']:
                    raise ValidationError('unsupported type in recipe', path + ['(recipes)', property_name])
                if recipe['property_values'][property_name] is not None:
                    validate(recipe['property_values'][property_name], schema['properties'][property_name], path + ['(recipes)', property_name], strict=strict)
                elif schema['properties'][property_name]['type'] == 'bool':
                    raise ValidationError('recipe values for type \'bool\' must not be None', path + ['(recipes)', property_name])

    if 'show_more' in schema:
        if not isinstance(schema['show_more'], list):
            raise ValidationError('show_more must be list', path)
        for property_name in schema['show_more']:
            if property_name not in schema['properties'].keys():
                raise ValidationError('unknown property: {}'.format(property_name), path)

    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_text_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given text object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default', 'minLength', 'maxLength', 'choices', 'pattern', 'multiline', 'markdown', 'note', 'placeholder', 'dataverse_export', 'scicat_export', 'languages', 'conditions', 'may_copy', 'style'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)

    if 'languages' in schema:
        if schema['languages'] != 'all':
            if not isinstance(schema['languages'], list) or len(schema['languages']) == 0:
                raise ValidationError('languages must be a non-empty list of known language codes or "all"', path)
            for language in schema['languages']:
                if not isinstance(language, str) or language not in all_language_codes:
                    raise ValidationError('languages must be a list of known language codes or "all"', path)
            allowed_language_codes = set(schema['languages'])
        else:
            allowed_language_codes = all_language_codes
    else:
        allowed_language_codes = {'en'}
    if 'placeholder' in schema and 'choices' in schema:
        raise ValidationError('placeholder cannot be used together with choices', path)
    if 'placeholder' in schema and not isinstance(schema['placeholder'], str) and not isinstance(schema['placeholder'], dict):
        raise ValidationError('placeholder must be str or dict', path)
    if 'placeholder' in schema and isinstance(schema['placeholder'], dict):
        if 'en' not in schema['placeholder']:
            raise ValidationError('placeholder must include an english translation', path)
        for lang_code in schema['placeholder'].keys():
            if lang_code not in all_language_codes:
                raise ValidationError('placeholder must only contain known languages', path)
        for placeholder_text in schema['placeholder'].values():
            if not isinstance(placeholder_text, str):
                raise ValidationError('placeholder must only contain text', path)
    if 'minLength' in schema and (not isinstance(schema['minLength'], int) or isinstance(schema['minLength'], bool)):
        raise ValidationError('minLength must be int', path)
    if 'maxLength' in schema and (not isinstance(schema['maxLength'], int) or isinstance(schema['maxLength'], bool)):
        raise ValidationError('maxLength must be int', path)
    if 'minLength' in schema and schema['minLength'] < 0:
        raise ValidationError('minLength must not be negative', path)
    if 'maxLength' in schema and schema['maxLength'] < 0:
        raise ValidationError('maxLength must not be negative', path)
    if 'minLength' in schema and 'maxLength' in schema and schema['maxLength'] < schema['minLength']:
        raise ValidationError('maxLength must not be less than minLength', path)
    if 'choices' in schema and not isinstance(schema['choices'], list):
        raise ValidationError('choices must be list', path)
    if 'choices' in schema and not schema['choices']:
        raise ValidationError('choices must not be empty', path)
    if 'choices' in schema:
        choice_type = None
        for i, choice in enumerate(schema['choices']):
            if not isinstance(choice, str) and not isinstance(choice, dict):
                raise ValidationError('choice must be str or dict', path + [str(i)])
            if choice_type is not None and type(choice) != choice_type:
                raise ValidationError('choices must be either all str or all dict', path + [str(i)])
            choice_type = type(choice)
            if isinstance(choice, dict):
                if 'en' not in choice:
                    raise ValidationError('choice must include an english translation', path + [str(i)])
                for lang_code in choice.keys():
                    if lang_code not in all_language_codes:
                        raise ValidationError('choice must only contain known languages', path + [str(i)])
                for choice_text in choice.values():
                    if not isinstance(choice_text, str):
                        raise ValidationError('choice must only contain text', path + [str(i)])
                    if choice_text.isspace():
                        raise ValidationError('choice must contain more than whitespace', path + [str(i)])
            else:
                if choice.isspace():
                    raise ValidationError('choice must contain more than whitespace', path + [str(i)])
    if 'default' in schema and not isinstance(schema['default'], str) and not isinstance(schema['default'], dict):
        raise ValidationError('default must be str or dict', path)
    if 'choices' in schema and 'default' in schema:
        if schema['default'] not in schema['choices']:
            raise ValidationError('default must only contain a valid choice', path)
    elif 'default' in schema and isinstance(schema['default'], dict):
        for lang_code in schema['default'].keys():
            if lang_code not in allowed_language_codes:
                raise ValidationError('default must only contain allowed languages', path)
        for default_text in schema['default'].values():
            if not isinstance(default_text, str):
                raise ValidationError('default must only contain text', path)
    if 'pattern' in schema and not isinstance(schema['pattern'], str):
        raise ValidationError('pattern must be str', path)
    if 'pattern' in schema:
        try:
            re.compile(schema['pattern'])
        except re.error:
            raise ValidationError('pattern is no valid regular expression', path)
    if 'multiline' in schema and not isinstance(schema['multiline'], bool):
        raise ValidationError('multiline must be bool', path)
    if 'markdown' in schema and not isinstance(schema['markdown'], bool):
        raise ValidationError('markdown must be bool', path)
    if schema.get('markdown') and schema.get('multiline'):
        raise ValidationError('text may not both be multiline and markdown', path)
    if 'choices' in schema and schema.get('multiline'):
        raise ValidationError('text may not both be multiline and have choices', path)
    if 'choices' in schema and schema.get('markdown'):
        raise ValidationError('text may not both be markdown and have choices', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'dataverse_export' in schema and not schema['dataverse_export'] and path == ['name']:
        raise ValidationError('dataverse_export must be True for the object name', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    if 'scicat_export' in schema and not schema['scicat_export'] and path == ['name']:
        raise ValidationError('scicat_export must be True for the object name', path)
    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_datetime_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given datetime object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default', 'note', 'dataverse_export', 'scicat_export', 'conditions', 'may_copy', 'style'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)

    if 'default' in schema:
        if not isinstance(schema['default'], str):
            raise ValidationError('default must be str', path)
        else:
            try:
                datetime.datetime.strptime(schema['default'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                raise ValidationError('invalid default value', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_bool_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given boolean object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'default', 'note', 'dataverse_export', 'scicat_export', 'conditions', 'may_copy', 'style'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)

    if 'default' in schema and not isinstance(schema['default'], bool):
        raise ValidationError('default must be bool', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_quantity_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given quantity object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'units', 'default', 'note', 'placeholder', 'dataverse_export', 'scicat_export', 'conditions', 'may_copy', 'style', 'display_digits', 'min_magnitude', 'max_magnitude'}
    required_keys = {'type', 'title', 'units'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)

    if isinstance(schema['units'], str):
        if not units_are_valid(schema['units']):
            raise ValidationError('invalid units', path)
    elif isinstance(schema['units'], list) and len(schema['units']) > 0:
        dimensionality = None
        pint_units = []
        for unit in schema['units']:
            if not isinstance(unit, str):
                raise ValidationError('units must be string or list of strings', path)
            try:
                quantity = datatypes.Quantity(1.0, units=unit)
            except pint.UndefinedUnitError:
                raise ValidationError('invalid units', path)
            if dimensionality is None:
                dimensionality = quantity.dimensionality
            elif quantity.dimensionality != dimensionality:
                raise ValidationError('units must be for same dimensionality', path)
            if quantity.pint_units in pint_units:
                raise ValidationError('units must not be duplicate', path)
            pint_units.append(quantity.pint_units)
    else:
        raise ValidationError('units must be string or list of strings', path)

    if 'default' in schema and not isinstance(schema['default'], float) and not isinstance(schema['default'], int):
        raise ValidationError('default must be float or int', path)
    if 'min_magnitude' in schema and not isinstance(schema['min_magnitude'], float) and not isinstance(schema['min_magnitude'], int):
        raise ValidationError('min_magnitude must be float or int', path)
    if 'max_magnitude' in schema and not isinstance(schema['max_magnitude'], float) and not isinstance(schema['max_magnitude'], int):
        raise ValidationError('max_magnitude must be float or int', path)
    if 'default' in schema and not math.isfinite(schema['default']):
        raise ValidationError('default must be a finite number', path)
    if 'min_magnitude' in schema and not math.isfinite(schema['min_magnitude']):
        raise ValidationError('min_magnitude must be a finite number', path)
    if 'max_magnitude' in schema and not math.isfinite(schema['max_magnitude']):
        raise ValidationError('max_magnitude must be a finite number', path)
    if 'min_magnitude' in schema and 'max_magnitude' in schema and schema['min_magnitude'] > schema['max_magnitude']:
        raise ValidationError('max_magnitude must be greater than or equal to min_magnitude', path)
    if 'min_magnitude' in schema and 'default' in schema and schema['min_magnitude'] > schema['default']:
        raise ValidationError('default must be greater than or equal to min_magnitude', path)
    if 'max_magnitude' in schema and 'default' in schema and schema['max_magnitude'] < schema['default']:
        raise ValidationError('default must be less than or equal to max_magnitude', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    if 'placeholder' in schema and not isinstance(schema['placeholder'], str) and not isinstance(schema['placeholder'], dict):
        raise ValidationError('placeholder must be str or dict', path)
    if 'placeholder' in schema and isinstance(schema['placeholder'], dict):
        if 'en' not in schema['placeholder']:
            raise ValidationError('placeholder must include an english translation', path)
        for lang_code in schema['placeholder'].keys():
            if lang_code not in all_language_codes:
                raise ValidationError('placeholder must only contain known languages', path)
        for placeholder_text in schema['placeholder'].values():
            if not isinstance(placeholder_text, str):
                raise ValidationError('placeholder must only contain text', path)
    if 'display_digits' in schema and (type(schema['display_digits']) is not int or schema['display_digits'] < 0):
        raise ValidationError('display_digits must be a non-negative int', path)
    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_sample_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given sample object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'dataverse_export', 'scicat_export', 'conditions', 'may_copy', 'style'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)

    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_measurement_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given measurement object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'dataverse_export', 'scicat_export', 'conditions', 'may_copy', 'style'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)

    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_object_reference_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given object reference object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'action_type_id', 'action_id', 'dataverse_export', 'scicat_export', 'conditions', 'may_copy', 'style'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)

    if 'action_type_id' in schema and not (
            schema['action_type_id'] is None or
            type(schema['action_type_id']) == int or
            type(schema['action_type_id']) == list and all(
                type(action_type_id) == int for action_type_id in schema['action_type_id']
            )
    ):
        raise ValidationError('action_type_id must be int, None or a list of ints', path)
    if 'action_id' in schema and not (
            schema['action_id'] is None or
            type(schema['action_id']) == int or
            type(schema['action_id']) == list and all(
                type(action_type_id) == int for action_type_id in schema['action_id']
            )
    ):
        raise ValidationError('action_id must be int, None or a list of ints', path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_notebook_templates(notebook_templates: typing.Any) -> None:
    """
    Validate the given notebook templates and raise a ValidationError if they are invalid.

    :param notebook_templates: the sampledb object schema
    :raise ValidationError: if the notebook templates are invalid
    """
    if not isinstance(notebook_templates, list):
        raise ValidationError('notebookTemplates must be a list', ['notebookTemplates'])

    for notebook_index, notebook_template in enumerate(notebook_templates):
        path = ['notebookTemplates', str(notebook_index)]
        if not isinstance(notebook_template, dict):
            raise ValidationError('notebook template must be a dict', path)
        valid_keys = {'title', 'url', 'params'}
        required_keys = valid_keys
        schema_keys = set(notebook_template.keys())
        invalid_keys = schema_keys - valid_keys
        if invalid_keys:
            raise ValidationError('unexpected keys in notebook template: {}'.format(invalid_keys), path)
        missing_keys = required_keys - schema_keys
        if missing_keys:
            raise ValidationError('missing keys in notebook template: {}'.format(missing_keys), path)
        if not isinstance(notebook_template['title'], str):
            raise ValidationError('notebook template title must be str', path)
        if not isinstance(notebook_template['url'], str):
            raise ValidationError('notebook template url must be str', path)
        if not notebook_template['url'].endswith('.ipynb'):
            raise ValidationError('notebook template url must end with .ipynb', path)
        base_url = 'https://iffjupyter.fz-juelich.de/templates/t/'
        test_url = urllib.parse.urljoin(base_url, notebook_template['url'])
        if not test_url.startswith(base_url) or urllib.parse.urlparse(base_url).netloc != urllib.parse.urlparse(test_url).netloc:
            raise ValidationError('notebook template url must be relative', path)
        if not isinstance(notebook_template['params'], dict):
            raise ValidationError('notebook template params must be a dict', path)
        for param_name, param_value in notebook_template['params'].items():
            if not isinstance(param_name, str):
                raise ValidationError('notebook template param names must be str', path)
            if not isinstance(param_value, str) and not isinstance(param_value, list):
                raise ValidationError('notebook template param values must be str or a list', path)
            if isinstance(param_value, list):
                for param_step in param_value:
                    if not isinstance(param_step, str) and not isinstance(param_step, int):
                        raise ValidationError('notebook template param value steps must be str or int', path)
            if isinstance(param_value, str):
                valid_param_values = {'object_id'}
                if param_value not in valid_param_values:
                    raise ValidationError('notebook template param value must be a list or one of {}'.format(valid_param_values), path)


def _validate_user_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given user object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'dataverse_export', 'scicat_export', 'default', 'conditions', 'may_copy', 'style'}
    required_keys = {'type', 'title'}
    schema_keys = set(schema.keys())
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    missing_keys = required_keys - schema_keys
    if missing_keys:
        raise ValidationError('missing keys in schema: {}'.format(missing_keys), path)
    if 'dataverse_export' in schema and not isinstance(schema['dataverse_export'], bool):
        raise ValidationError('dataverse_export must be True or False', path)
    if 'scicat_export' in schema and not isinstance(schema['scicat_export'], bool):
        raise ValidationError('scicat_export must be True or False', path)
    if 'default' in schema and (schema['default'] != 'self' and type(schema['default']) is not int):
        raise ValidationError('default must be "self" or int', path)
    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)


def _validate_plotly_chart_schema(
        schema: typing.Dict[str, typing.Any],
        path: typing.List[str],
        *,
        all_language_codes: typing.Set[str]
) -> None:
    """
    Validates the given plotly_chart object schema and raises a ValidationError if it is invalid.

    :param schema: the sampledb object schema
    :param path: the path to this subschema
    :param all_language_codes: the set of existing language codes
    :raise ValidationError: if the schema is invalid.
    """
    valid_keys = {'type', 'title', 'note', 'dataverse_export', 'conditions', 'may_copy', 'style'}
    schema_keys = schema.keys()
    invalid_keys = schema_keys - valid_keys
    if invalid_keys:
        raise ValidationError('unexpected keys in schema: {}'.format(invalid_keys), path)
    _validate_note_in_schema(schema, path, all_language_codes=all_language_codes)
