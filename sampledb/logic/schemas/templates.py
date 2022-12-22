import typing

from .. import actions
from ... import logic
from ..errors import ActionDoesNotExistError, InvalidNumberError, InvalidTemplateIDError, RecursiveTemplateError
from ...models import ActionType, Permissions

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
        for key in {'properties', 'required', 'propertyOrder'}:
            if key in schema:
                del schema[key]
        try:
            template_action = actions.get_action(schema['template'])
        except ActionDoesNotExistError:
            raise
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
    if schema.get('type') == 'array' and 'items' in schema and isinstance(schema['items'], dict):
        reverse_substitute_templates(schema['items'])
    if schema.get('type') == 'object':
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
        elif 'properties' in schema:
            for property_schema in schema['properties'].values():
                if type(property_schema) is dict:
                    reverse_substitute_templates(property_schema)


def update_schema_using_template_action(
        schema: typing.Dict[str, typing.Any],
        template_action_id: int,
        template_action_schema: typing.Dict[str, typing.Any]
) -> typing.Dict[str, typing.Any]:
    if schema.get('type') == 'array' and 'items' in schema and isinstance(schema['items'], dict):
        schema['items'] = update_schema_using_template_action(schema['items'], template_action_id, template_action_schema)
    if schema.get('type') == 'object':
        if schema.get('template') == template_action_id:
            if schema.get('title'):
                title = schema['title']
            else:
                title = None
            schema.update(template_action_schema)
            if title is not None:
                schema['title'] = title
        elif 'properties' in schema:
            for property_name, property_schema in schema['properties'].items():
                if type(property_schema) is dict:
                    schema['properties'][property_name] = update_schema_using_template_action(property_schema, template_action_id, template_action_schema)
    return schema


def enforce_permissions(
        schema: typing.Dict[str, typing.Any],
        user_id: int,
        path: typing.Sequence[str] = ()
) -> typing.Sequence[typing.List[str]]:
    path = list(path)
    invalid_template_paths = []
    if schema.get('type') == 'object' and schema.get('properties'):
        for property_name, property_schema in schema['properties'].items():
            if property_schema.get('type') == 'object':
                if property_schema.get('template'):
                    template_action_id = property_schema['template']
                    if type(template_action_id) is int:
                        template_action_permissions = logic.action_permissions.get_user_action_permissions(template_action_id, user_id)
                        if Permissions.READ not in template_action_permissions:
                            invalid_template_paths.append(path + [property_name])
                else:
                    invalid_template_paths.extend(enforce_permissions(property_schema, user_id, path + [property_name]))
            elif property_schema.get('type') == 'array':
                invalid_template_paths.extend(enforce_permissions(property_schema, user_id, path + [property_name]))
    if schema.get('type') == 'array' and schema.get('items'):
        invalid_template_paths.extend(enforce_permissions(schema['items'], user_id, path + ['[?]']))

    return invalid_template_paths
