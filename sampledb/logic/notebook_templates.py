# coding: utf-8
"""

"""

import typing
import copy
from .errors import ObjectDoesNotExistError
from .objects import get_object
from .object_permissions import get_user_object_permissions, Permissions


def get_notebook_templates(
        object_id: int,
        data: typing.Dict[str, typing.Any],
        schema: typing.Dict[str, typing.Any],
        user_id: int
) -> typing.List[typing.Dict[str, typing.Any]]:
    """
    Return notebook templates with parameters from object data.

    :param object_id: the ID of the object
    :param data: the data of the object
    :param schema: the schema of the object
    :param user_id: the user for which the notebook templates are prepared.
    :return: the prepared notebook template data
    """
    notebook_templates = copy.deepcopy(schema.get('notebookTemplates', []))
    for notebook_template in notebook_templates:
        for parameter, parameter_value in list(notebook_template.get('params', {}).items()):
            if parameter_value == 'object_id':
                notebook_template['params'][parameter] = object_id
            elif isinstance(parameter_value, list):
                parameter_data = data
                parameter_schema = schema
                for step in parameter_value:
                    if isinstance(step, str) and isinstance(parameter_data, dict) and step in parameter_data:
                        parameter_data = parameter_data[step]
                        if parameter_schema.get('type') == 'object' and step in parameter_schema.get('properties', {}):
                            parameter_schema = parameter_schema['properties'][step]
                        else:
                            parameter_schema = None
                    elif isinstance(step, int) and isinstance(parameter_data, list) and isinstance(parameter_schema, dict) and parameter_schema.get('type') == 'array' and 0 <= step < len(parameter_data):
                        parameter_data = parameter_data[step]
                        parameter_schema = parameter_schema.get('items', {})
                    elif step == 'object' and isinstance(parameter_data, dict) and isinstance(parameter_data.get('object_id'), int) and parameter_schema.get('type') in ('sample', 'measurement', 'object_reference'):
                        referenced_object_id = parameter_data['object_id']
                        try:
                            if Permissions.READ not in get_user_object_permissions(referenced_object_id, user_id):
                                parameter_data = None
                                break
                            referenced_object = get_object(referenced_object_id)
                        except ObjectDoesNotExistError:
                            parameter_data = None
                            break
                        parameter_data = referenced_object.data
                        parameter_schema = referenced_object.schema
                    else:
                        parameter_data = None
                        break
                notebook_template['params'][parameter] = parameter_data
            else:
                notebook_template['params'][parameter] = None
    return notebook_templates
