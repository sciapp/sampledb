# coding: utf-8
"""

"""
import typing

import sqlalchemy


def ascending(sorting_func: typing.Any) -> typing.Any:
    """
    Modify a sorting function to sort in ascending order.

    :param sorting_func: the original sorting function
    :return: the modified sorting function
    """
    def modified_sorting_func(
            current_columns: typing.Any,
            original_columns: typing.Any,
            sorting_func: typing.Callable[[typing.Any, typing.Any], typing.Any] = sorting_func
    ) -> typing.Any:
        return sqlalchemy.sql.asc(sorting_func(current_columns, original_columns))
    setattr(modified_sorting_func, 'require_original_columns', getattr(sorting_func, 'require_original_columns', False))
    return modified_sorting_func


def descending(sorting_func: typing.Any) -> typing.Any:
    """
    Modify a sorting function to sort in descending order.

    :param sorting_func: the original sorting function
    :return: the modified sorting function
    """
    def modified_sorting_func(
            current_columns: typing.Any,
            original_columns: typing.Any,
            sorting_func: typing.Callable[[typing.Any, typing.Any], typing.Any] = sorting_func
    ) -> typing.Any:
        return sqlalchemy.sql.desc(sorting_func(current_columns, original_columns))
    setattr(modified_sorting_func, 'require_original_columns', getattr(sorting_func, 'require_original_columns', False))
    return modified_sorting_func


def object_id() -> typing.Callable[[typing.Any, typing.Any], typing.Any]:
    """
    Create a sorting function to sort by object ID.

    :return: the sorting function
    """
    def sorting_func(current_columns: typing.Any, original_columns: typing.Any) -> typing.Any:
        return current_columns.object_id
    return sorting_func


def creation_date() -> typing.Callable[[typing.Any, typing.Any], typing.Any]:
    """
    Create a sorting function to sort by creation date.

    :return: the sorting function
    """
    def sorting_func(current_columns: typing.Any, original_columns: typing.Any) -> typing.Any:
        return sqlalchemy.sql.func.coalesce(original_columns.utc_datetime, current_columns.utc_datetime)  # pylint: disable=not-callable
    setattr(sorting_func, 'require_original_columns', True)
    return sorting_func


def last_modification_date() -> typing.Callable[[typing.Any, typing.Any], typing.Any]:
    """
    Create a sorting function to sort by last modification date.

    :return: the sorting function
    """
    def sorting_func(current_columns: typing.Any, original_columns: typing.Any) -> typing.Any:
        return current_columns.utc_datetime
    return sorting_func


def property_value(property_name: str, language_code: str = 'en') -> typing.Callable[[typing.Any, typing.Any], typing.Any]:
    """
    Create a sorting function to sort by an arbitrary property.

    :param property_name: the name of the property to sort by
    :param language_code: the language code to primarily sort text properties by
    :return: the sorting function
    """
    def sorting_func(current_columns: typing.Any, original_columns: typing.Any) -> typing.Any:
        columns = current_columns
        return sqlalchemy.sql.expression.case(
            (
                sqlalchemy.and_(columns.data[property_name]['_type'].astext == 'text', sqlalchemy.func.jsonb_typeof(columns.data[property_name]['text']) == 'string'),
                columns.data[property_name]['text'].astext
            ),
            (
                sqlalchemy.and_(columns.data[property_name]['_type'].astext == 'text', columns.data[property_name]['text'].has_key(language_code)),
                columns.data[property_name]['text'][language_code].astext
            ),
            (
                sqlalchemy.and_(columns.data[property_name]['_type'].astext == 'text', columns.data[property_name]['text'].has_key('en')),
                columns.data[property_name]['text']['en'].astext
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
            ),
            (
                columns.data[property_name]['_type'].astext == 'measurement',
                columns.data[property_name]['object_id'].astext
            ),
            (
                columns.data[property_name]['_type'].astext == 'object_reference',
                columns.data[property_name]['object_id'].astext
            ),
            else_=sqlalchemy.sql.null()
        )
    return sorting_func
