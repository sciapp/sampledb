# coding: utf-8
"""

"""

import typing

import pint

from ..units import ureg
from ..errors import UndefinedUnitError

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def units_are_valid(units: str) -> bool:
    try:
        ureg.Unit(units)
        return True
    except pint.UndefinedUnitError:
        return False


def get_dimensionality_for_units(
        units: typing.Union[str, typing.List[str]]
) -> str:
    """
    Returns the units' dimensionality in the dimensionality syntax of the pint package.

    :param units: a valid
    :return: dimensionality as string
    :raise errors.UndefinedUnitError: if the units are undefined
    """
    if isinstance(units, list):
        if len(units) > 0:
            units = units[0]
        else:
            units = '1'
    try:
        return str(ureg.Unit(units).dimensionality)
    except pint.UndefinedUnitError:
        raise UndefinedUnitError()


def get_property_paths_for_schema(
        schema: typing.Dict[str, typing.Any],
        valid_property_types: typing.Optional[typing.Set[str]] = None,
        path: typing.Optional[typing.List[typing.Optional[str]]] = None,
        path_depth_limit: typing.Optional[int] = None
) -> typing.Dict[
    typing.Sequence[typing.Optional[str]],
    typing.Dict[str, typing.Optional[typing.Union[str, typing.Dict[str, str]]]]
]:
    """
    Get a dict mapping property paths to the type used in the given schema.

    None is used as a placeholder for array indices and types may be limited
    to a set of valid types.

    :param schema: the schema to generate the dict for
    :param valid_property_types: a list of property types, or None
    :param path: the path to this subschema, or None
    :param path_depth_limit: how deep paths may be, or None
    :return: the generated dict
    """
    if path is None:
        path = []
    property_type = schema.get('type')
    property_paths: typing.Dict[
        typing.Sequence[typing.Optional[str]],
        typing.Dict[str, typing.Optional[typing.Union[str, typing.Dict[str, str]]]]
    ] = {}
    if path_depth_limit is not None and len(path) > path_depth_limit:
        return property_paths
    if property_type == 'object':
        property_paths.update(_get_property_paths_for_object_schema(
            schema=schema,
            valid_property_types=valid_property_types,
            path=path,
            path_depth_limit=path_depth_limit
        ))
    if property_type == 'array':
        property_paths.update(_get_property_paths_for_array_schema(
            schema=schema,
            valid_property_types=valid_property_types,
            path=path,
            path_depth_limit=path_depth_limit
        ))
    if property_type is not None and (valid_property_types is None or property_type in valid_property_types):
        property_paths[tuple(path)] = {
            "type": property_type,
            "title": schema.get('title')
        }
    return property_paths


def _get_property_paths_for_object_schema(
        schema: typing.Dict[str, typing.Any],
        valid_property_types: typing.Optional[typing.Set[str]],
        path: typing.List[typing.Optional[str]],
        path_depth_limit: typing.Optional[int] = None
) -> typing.Dict[
    typing.Sequence[typing.Optional[str]],
    typing.Dict[str, typing.Optional[typing.Union[str, typing.Dict[str, str]]]]
]:
    path = list(path)
    if path_depth_limit is not None and len(path) + 1 > path_depth_limit:
        # properties will have reached the path depth limit
        return {}
    if not isinstance(schema, dict):
        return {}
    if not schema.get('type') == 'object':
        return {}
    if not isinstance(schema.get('properties'), dict):
        return {}
    property_paths = {}
    for property_name, property_schema in schema['properties'].items():
        property_paths.update(get_property_paths_for_schema(
            schema=property_schema,
            valid_property_types=valid_property_types,
            path=path + [property_name],
            path_depth_limit=path_depth_limit
        ))
    return property_paths


def _get_property_paths_for_array_schema(
        schema: typing.Dict[str, typing.Any],
        valid_property_types: typing.Optional[typing.Set[str]],
        path: typing.List[typing.Optional[str]],
        path_depth_limit: typing.Optional[int] = None
) -> typing.Dict[
    typing.Sequence[typing.Optional[str]],
    typing.Dict[str, typing.Optional[typing.Union[str, typing.Dict[str, str]]]]
]:
    path = list(path)
    if path_depth_limit is not None and len(path) + 1 > path_depth_limit:
        # array items will have reached the path depth limit
        return {}
    if not isinstance(schema, dict):
        return {}
    if not schema.get('type') == 'array':
        return {}
    property_schema = schema.get('items')
    if not isinstance(property_schema, dict):
        return {}

    property_paths = {}
    property_paths.update(get_property_paths_for_schema(
        schema=property_schema,
        valid_property_types=valid_property_types,
        path=path + [None],
        path_depth_limit=path_depth_limit
    ))
    return property_paths
