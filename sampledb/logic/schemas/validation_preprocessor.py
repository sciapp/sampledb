from .. import actions
from ..errors import ActionDoesNotExistError


def substitute_templates(schema: dict):
    if 'template' in schema.keys():
        if 'properties' in schema.keys() and schema['properties'].keys():
            return
        try:
            template_schema = actions.get_action(schema['template']).schema
        except ActionDoesNotExistError:
            raise
        for key in template_schema:
            if key == 'title':
                schema['title'] = schema['title'] if schema['title'] else template_schema['title']
            elif key == 'properties':
                keys = set(template_schema['properties'].keys()) - set(['name'])
                schema['properties'] = {k: template_schema['properties'][k] for k in keys}
            elif key == 'required':
                schema['required'] = [item for item in set(template_schema['required']) - set(['name'])]
            elif key == 'propertyOrder':
                schema['propertyOrder'] = [item for item in set(template_schema['propertyOrder']) - set(['name'])]
            else:
                schema[key] = template_schema[key]


def reverse_substitute_templates(schema: dict):
    if type(schema) is not dict:
        return
    if 'type' in schema and schema['type'] == 'array' and 'items' in schema.keys():
        reverse_substitute_templates(schema['items'])
    elif 'type' in schema and schema['type'] == 'object':
        if 'template' in schema:
            try:
                actions.get_action(schema['template']).schema
            except ActionDoesNotExistError:
                raise
            for key in schema.keys():
                if key in ['title', 'type', 'template']:
                    pass
                elif key in ['properties']:
                    schema[key] = {}
                elif key in ['propertyOrder', 'required']:
                    schema[key] = []
                else:
                    schema[key] = ''
        elif 'properties' in schema.keys():
            for key in schema['properties'].keys():
                reverse_substitute_templates(schema['properties'][key])
