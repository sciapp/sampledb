# coding: utf-8
"""

"""

import sqlalchemy
import typing


def ascending(sorting_func: typing.Any) -> typing.Any:
    """
    Modify a sorting function to sort in ascending order.

    :param sorting_func: the original sorting function
    :return: the modified sorting function
    """
    def modified_sorting_func(columns, sorting_func=sorting_func):
        return sqlalchemy.sql.asc(sorting_func(columns))
    return modified_sorting_func


def descending(sorting_func: typing.Any) -> typing.Any:
    """
    Modify a sorting function to sort in descending order.

    :param sorting_func: the original sorting function
    :return: the modified sorting function
    """
    def modified_sorting_func(columns, sorting_func=sorting_func):
        return sqlalchemy.sql.desc(sorting_func(columns))
    return modified_sorting_func


def object_id() -> typing.Callable[[typing.Any], typing.Any]:
    """
    Create a sorting function to sort by object ID.

    :return: the sorting function
    """
    def sorting_func(columns: typing.Any) -> typing.Any:
        return columns.object_id
    return sorting_func


def creation_date() -> typing.Callable[[typing.Any], typing.Any]:
    """
    Create a sorting function to sort by creation date.

    :return: the sorting function
    """
    def sorting_func(columns: typing.Any) -> typing.Any:
        return columns.utc_datetime
    return sorting_func


def property_value(property_name: str) -> typing.Callable[[typing.Any], typing.Any]:
    """
    Create a sorting function to sort by an arbitrary property.

    :param property_name: the name of the property to sort by
    :return: the sorting function
    """
    def sorting_func(columns: typing.Any) -> typing.Any:
        return sqlalchemy.sql.expression.case([
            (
                columns.data[property_name]['_type'].astext == 'text',
                columns.data[property_name]['text'].astext
            ),
            (
                columns.data[property_name]['_type'].astext == 'quantity',
                sqlalchemy.func.to_char(columns.data[property_name]['magnitude_in_base_units'].astext.cast(sqlalchemy.Float), '00000000000000000000.00000000000000000000')
            ),
            (
                columns.data[property_name]['_type'].astext == 'bool',
                columns.data[property_name]['value'].astext
            ),
            (
                columns.data[property_name]['_type'].astext == 'datetime',
                columns.data[property_name]['utc_datetime'].astext
            ),
            (
                columns.data[property_name]['_type'].astext == 'sample',
                columns.data[property_name]['object_id'].astext
            )
        ], else_=sqlalchemy.sql.null())
    return sorting_func
