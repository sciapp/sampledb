import typing

from .. import actions
from ... import logic
from ..errors import InvalidNumberError, InvalidTemplateIDError, RecursiveTemplateError, ValidationError
from ...models import ActionType, Permissions
from .utils import schema_iter

# keys and properties that only can be used in root objects

SKIPPED_TEMPLATE_KEYS = {
    'displayProperties',
    'batch',
    'batch_name_format',
    'notebookTemplates',
}
SKIPPED_TEMPLATE_PROPERTY_NAMES = {
    'name',
    'tags',
    'hazards'
}


def process_template_action_schema(
        template_action_schema: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Any]:
    processed_schema: typing.Dict[str, typing.Any] = {}
    for key in template_action_schema:
        if key == 'properties':
            processed_schema['properties'] = {
                property_name: property_value
                for property_name, property_value in template_action_schema['properties'].items()
                if property_name not in SKIPPED_TEMPLATE_PROPERTY_NAMES
            }
        elif key == 'required':
            processed_schema['required'] = [
                property_name
                for property_name in template_action_schema['required']
                if property_name not in SKIPPED_TEMPLATE_PROPERTY_NAMES
            ]
        elif key == 'propertyOrder':
            processed_schema['propertyOrder'] = [
                property_name
                for property_name in template_action_schema['propertyOrder']
                if property_name not in SKIPPED_TEMPLATE_PROPERTY_NAMES
            ]
        elif key == 'show_more':
            processed_schema['show_more'] = [
                property_name
                for property_name in template_action_schema['show_more']
                if property_name not in SKIPPED_TEMPLATE_PROPERTY_NAMES
            ]
        elif key not in SKIPPED_TEMPLATE_KEYS:
            processed_schema[key] = template_action_schema[key]
    return processed_schema


def substitute_templates(
        schema: typing.Dict[str, typing.Any],
        invalid_template_action_ids: typing.Sequence[int] = ()
) -> None:
    if 'template' in schema.keys():
        if type(schema['template']) is dict and 'action_id' in schema['template'] and 'component_uuid' in schema['template']\
                and type(schema['template']['action_id']) is int and type(schema['template']['component_uuid']) is str:
            return
        if type(schema['template']) is not int:
            raise InvalidNumberError()
        if schema['template'] in invalid_template_action_ids:
            raise RecursiveTemplateError()
        for key in ['properties', 'required', 'propertyOrder']:
            if key in schema:
                del schema[key]
        template_action = actions.get_action(schema['template'])
        if template_action.schema is None or template_action.type is None or not (template_action.type.is_template or template_action.type.fed_id == ActionType.TEMPLATE):
            raise InvalidTemplateIDError()
        template_schema = template_action.schema
        template_schema = process_template_action_schema(template_schema)
        if schema.get('title'):
            del template_schema['title']
        if 'show_more' in schema and 'show_more' in template_schema:
            del template_schema['show_more']
        if 'note' in schema and 'note' in template_schema:
            del template_schema['note']
        schema.update(template_schema)


def reverse_substitute_templates(schema: typing.Dict[str, typing.Any]) -> None:
    root_schema = schema
    for _, schema in schema_iter(root_schema, filter_property_types={'object'}):
        if 'template' in schema:
            # ensure the action exists
            actions.check_action_exists(schema['template'])
            for key in list(schema.keys()):
                if key in ['title', 'type', 'template', 'may_copy', 'conditions']:
                    continue
                elif key in ['properties']:
                    schema[key] = {}
                elif key in ['propertyOrder', 'required']:
                    schema[key] = []
                else:
                    del schema[key]


def update_schema_using_template_action(
        schema: typing.Dict[str, typing.Any],
        template_action_id: int,
        template_action_schema: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Any]:
    root_schema = schema
    for _, schema in schema_iter(root_schema, filter_property_types={'object'}):
        if schema.get('template') == template_action_id:
            if schema.get('title'):
                title = schema['title']
            else:
                title = None
            schema.update(template_action_schema)
            if title is not None:
                schema['title'] = title
    return root_schema


def find_invalid_template_paths(
        schema: typing.Dict[str, typing.Any],
        user_id: int
) -> typing.Sequence[typing.List[str]]:
    """
    Find all property paths to object schemas with an invalid template action.

    :param schema: the schema to check for invalid template paths
    :param user_id: the user ID to check permissions with
    :return: a list of property paths for invalid templates
    """
    invalid_template_paths = []
    if not isinstance(schema, dict):
        raise ValidationError('schema must be dict', [])
    for property_path, property_schema in schema_iter(schema, filter_property_types={'object'}):
        template_action_id = property_schema.get('template')
        if type(template_action_id) is int:
            template_action_permissions = logic.action_permissions.get_user_action_permissions(
                action_id=template_action_id,
                user_id=user_id
            )
            if Permissions.READ not in template_action_permissions:
                invalid_template_paths.append([
                    path_element or '[?]'
                    for path_element in property_path
                ])
    return invalid_template_paths


def find_used_template_ids(
        schema: typing.Dict[str, typing.Any]
) -> typing.Set[int]:
    """
    Find all template action IDs used by the schema.

    :param schema: the schema to search for template objects
    :return: a set of template action IDs
    """
    template_action_ids = set()
    for _property_path, property_schema in schema_iter(schema, filter_property_types={'object'}):
        template_action_id = property_schema.get('template')
        if type(template_action_id) is int:
            template_action_ids.add(template_action_id)
    return template_action_ids
