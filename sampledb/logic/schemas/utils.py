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
    :param valid_property_types: a set of property types, or None
    :param path: the path to this subschema, or None
    :param path_depth_limit: how deep paths may be, or None
    :return: the generated dict
    """
    return {
        property_path: {
            'type': property_schema.get('type'),
            'title': property_schema.get('title')
        }
        for property_path, property_schema in schema_iter(
            schema=schema,
            path=tuple(path or []),
            filter_property_types=valid_property_types,
            filter_path_depth_limit=path_depth_limit
        )
        if property_schema.get('type') is not None
    }


def schema_iter(
        schema: typing.Dict[str, typing.Any],
        *,
        path: typing.Sequence[typing.Optional[str]] = (),
        filter_path_depth_limit: typing.Optional[int] = None,
        filter_property_types: typing.Optional[typing.Set[str]] = None,
        filter_property_path: typing.Optional[typing.Sequence[typing.Optional[str]]] = None
) -> typing.Iterator[typing.Tuple[typing.Sequence[typing.Optional[str]], typing.Dict[str, typing.Any]]]:
    """
    Iterate over a schema.

    :param schema: the schema to iterate over
    :param path: the path to this schema
    :param filter_path_depth_limit: how deep paths may be, or None
    :param filter_property_types: a set of property types to include in the
        iterator, or None
    :param filter_property_path: a path to return the schema and sub-schemas
        for, or None
    :return: an iterator over tuples of path and schema at that path
    """
    if filter_path_depth_limit is not None and len(path) > filter_path_depth_limit:
        return
    if filter_property_path is not None and path[:min(len(path), len(filter_property_path))] != filter_property_path[:min(len(path), len(filter_property_path))]:
        return
    schema_type = schema.get('type')
    if (
            (filter_property_types is None or schema_type in filter_property_types) and
            (filter_property_path is None or path[:len(filter_property_path)] == filter_property_path)
    ):
        yield path, schema
    if schema_type == 'object':
        schema_properties = schema.get('properties')
        if isinstance(schema_properties, dict):
            for property_name, property_schema in schema_properties.items():
                if isinstance(property_name, str) and isinstance(property_schema, dict):
                    yield from schema_iter(
                        schema=property_schema,
                        path=tuple(path) + (property_name,),
                        filter_path_depth_limit=filter_path_depth_limit,
                        filter_property_types=filter_property_types,
                        filter_property_path=filter_property_path
                    )
    if schema_type == 'array':
        item_schema = schema.get('items')
        if isinstance(item_schema, dict):
            yield from schema_iter(
                schema=item_schema,
                path=tuple(path) + (None,),
                filter_path_depth_limit=filter_path_depth_limit,
                filter_property_types=filter_property_types,
                filter_property_path=filter_property_path
            )


def data_iter(
        data: typing.Union[typing.Dict[str, typing.Any], typing.List[typing.Any]],
        *,
        path: typing.Sequence[typing.Union[str, int]] = (),
        filter_property_types: typing.Optional[typing.Set[str]] = None,
) -> typing.Iterator[typing.Tuple[typing.Sequence[typing.Union[str, int]], typing.Union[typing.Dict[str, typing.Any], typing.Sequence[typing.Any]]]]:
    """
    Iterate over data.

    :param data: the data to iterate over
    :param path: the path to this schema
    :param filter_property_types: a set of property types to include in the
        iterator, or None
    :return: an iterator over tuples of path and data at that path
    """
    if isinstance(data, dict):
        if '_type' in data:
            data_type = data['_type']
        else:
            data_type = 'object'
    elif isinstance(data, list):
        data_type = 'array'
    else:
        return
    if filter_property_types is None or data_type in filter_property_types:
        yield path, data
    if data_type == 'object' and isinstance(data, dict):
        for property_name, property_data in data.items():
            if isinstance(property_name, str) and isinstance(property_data, (dict, list)):
                yield from data_iter(
                    data=property_data,
                    path=tuple(path) + (property_name,),
                    filter_property_types=filter_property_types,
                )
    if data_type == 'array':
        for index, item_data in enumerate(data):
            yield from data_iter(
                data=item_data,
                path=tuple(path) + (index,),
                filter_property_types=filter_property_types,
            )
