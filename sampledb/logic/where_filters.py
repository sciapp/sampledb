# coding: utf-8
"""
This module defines functions which can help filtering objects by using the
sampledb.datetypes types. Each function returns a SQLAlchemy object which can
be used for the filter_func in
VersionedJSONSerializableObjectTables.get_current_objects().

Filters that use equality cannot be expected to be exact due to floating point
precision. These filters use operators that include a range of EPSILON of the
left operand's magnitude in base units.
"""

from datetime import datetime, date
import operator
import json
import typing

import flask
import sqlalchemy as db
from flask_login import current_user

from . import datatypes
from . import languages
from .utils import get_translated_text, get_postgres_timezone_alias
from ..models import Objects
from ..models.files import File
from ..models.file_log import FileLogEntry

EPSILON = 1e-7

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def float_operator_equals(left: typing.Any, right: typing.Any) -> typing.Any:
    return db.and_(
        left * (1 - db.func.sign(left) * EPSILON) <= right,
        left * (1 + db.func.sign(left) * EPSILON) >= right
    )


def float_operator_less_than_equals(left: typing.Any, right: typing.Any) -> typing.Any:
    return left * (1 - db.func.sign(left) * EPSILON) <= right


def float_operator_greater_than_equals(left: typing.Any, right: typing.Any) -> typing.Any:
    return left * (1 + db.func.sign(left) * EPSILON) >= right


def quantity_binary_operator(db_obj: typing.Any, other: datatypes.Quantity, operator: typing.Callable[[typing.Any, typing.Any], typing.Any]) -> typing.Any:
    return db.and_(
        db_obj['_type'].astext == 'quantity',
        db_obj['dimensionality'].astext == str(other.dimensionality),
        operator(db_obj['magnitude_in_base_units'].astext.cast(db.Float), other.magnitude_in_base_units)
    )


def quantity_equals(db_obj: typing.Any, other: datatypes.Quantity) -> typing.Any:
    return quantity_binary_operator(db_obj, other, float_operator_equals)


def quantity_less_than(db_obj: typing.Any, other: datatypes.Quantity) -> typing.Any:
    return quantity_binary_operator(db_obj, other, operator.lt)


def quantity_less_than_equals(db_obj: typing.Any, other: datatypes.Quantity) -> typing.Any:
    return quantity_binary_operator(db_obj, other, float_operator_less_than_equals)


def quantity_greater_than(db_obj: typing.Any, other: datatypes.Quantity) -> typing.Any:
    return quantity_binary_operator(db_obj, other, operator.gt)


def quantity_greater_than_equals(db_obj: typing.Any, other: datatypes.Quantity) -> typing.Any:
    return quantity_binary_operator(db_obj, other, float_operator_greater_than_equals)


def quantity_between(db_obj: typing.Any, left: datatypes.Quantity, right: datatypes.Quantity, including: bool = True) -> typing.Any:
    if left.dimensionality != right.dimensionality:
        return False
    if including:
        return db.and_(
            db_obj['_type'].astext == 'quantity',
            db_obj['dimensionality'].astext == str(left.dimensionality),
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) * (1 + db.func.sign(db_obj['magnitude_in_base_units'].astext.cast(db.Float)) * EPSILON) >= left.magnitude_in_base_units,
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) * (1 - db.func.sign(db_obj['magnitude_in_base_units'].astext.cast(db.Float)) * EPSILON) <= right.magnitude_in_base_units
        )
    else:
        return db.and_(
            db_obj['_type'].astext == 'quantity',
            db_obj['dimensionality'].astext == str(left.dimensionality),
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) > left.magnitude_in_base_units,
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) < right.magnitude_in_base_units
        )


def datetime_binary_operator(db_obj: typing.Any, other: typing.Union[datatypes.DateTime, datetime], operator: typing.Callable[[typing.Any, date], typing.Any]) -> typing.Any:
    if isinstance(other, datatypes.DateTime):
        other = other.utc_datetime
    other_date = other.date()

    if flask.g.get('user') is not None and flask.g.user.timezone is not None:
        current_timezone_name = flask.g.user.timezone
    elif hasattr(current_user, 'timezone') and current_user.timezone is not None:
        current_timezone_name = current_user.timezone
    else:
        current_timezone_name = 'UTC'
    current_timezone_name = get_postgres_timezone_alias(current_timezone_name, other_date)
    naive_datetime = db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD HH24:MI:SS')
    local_timestamp = db.func.timezone(current_timezone_name, naive_datetime)
    locale_date = db.func.date_trunc('day', local_timestamp)
    return db.and_(
        db_obj['_type'].astext == 'datetime',
        operator(locale_date, other_date)
    )


def datetime_equals(db_obj: typing.Any, other: typing.Union[datatypes.DateTime, datetime]) -> typing.Any:
    return datetime_binary_operator(db_obj, other, operator.eq)


def datetime_less_than(db_obj: typing.Any, other: typing.Union[datatypes.DateTime, datetime]) -> typing.Any:
    return datetime_binary_operator(db_obj, other, operator.lt)


def datetime_less_than_equals(db_obj: typing.Any, other: typing.Union[datatypes.DateTime, datetime]) -> typing.Any:
    return datetime_binary_operator(db_obj, other, operator.le)


def datetime_greater_than(db_obj: typing.Any, other: typing.Union[datatypes.DateTime, datetime]) -> typing.Any:
    return datetime_binary_operator(db_obj, other, operator.gt)


def datetime_greater_than_equals(db_obj: typing.Any, other: typing.Union[datatypes.DateTime, datetime]) -> typing.Any:
    return datetime_binary_operator(db_obj, other, operator.ge)


def datetime_between(db_obj: typing.Any, left: typing.Union[datatypes.DateTime, datetime], right: typing.Union[datatypes.DateTime, datetime], including: bool = True) -> typing.Any:
    if isinstance(left, datatypes.DateTime):
        left = left.utc_datetime
    if isinstance(right, datatypes.DateTime):
        right = right.utc_datetime
    left_date = left.date()
    right_date = right.date()
    if including:
        return db.and_(
            db_obj['_type'].astext == 'datetime',
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD') >= left_date,
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD') <= right_date,
        )
    else:
        return db.and_(
            db_obj['_type'].astext == 'datetime',
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD') > left_date,
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD') < right_date,
        )


def boolean_equals(db_obj: typing.Any, value: typing.Union[datatypes.Boolean, bool]) -> typing.Any:
    if isinstance(value, datatypes.Boolean):
        value = value.value
    return db.and_(
        db_obj['_type'].astext == 'bool',
        db_obj['value'].astext.cast(db.Boolean) == value
    )


def boolean_true(db_obj: typing.Any) -> typing.Any:
    return boolean_equals(db_obj, True)


def boolean_false(db_obj: typing.Any) -> typing.Any:
    return boolean_equals(db_obj, False)


def text_equals(db_obj: typing.Any, text: typing.Union[datatypes.Text, str]) -> typing.Any:
    if isinstance(text, datatypes.Text):
        text_str = get_translated_text(text.text)
    else:
        text_str = text
    return db.or_(
        db.and_(
            db_obj['_type'].astext == 'text',
            db.or_(
                db.and_(
                    db.func.jsonb_typeof(db_obj['text']) == 'string',
                    db_obj['text'].astext == text_str,
                ),
                *[
                    db.and_(
                        db_obj['text'].has_key(lang_code),
                        db_obj['text'][lang_code].astext == text_str
                    )
                    for lang_code in languages.get_language_codes()
                ]
            )
        ),
        db.and_(
            db_obj['_type'].astext == 'plotly_chart',
            db_obj['plotly']['layout']['title']['text'].astext == text_str
        )
    )


def text_contains(db_obj: typing.Any, text: typing.Union[datatypes.Text, str]) -> typing.Any:
    if isinstance(text, datatypes.Text):
        text_str = get_translated_text(text.text)
    else:
        text_str = text
    return db.or_(
        db.and_(
            db_obj['_type'].astext == 'text',
            db.or_(
                db.and_(
                    db.func.jsonb_typeof(db_obj['text']) == 'string',
                    db_obj['text'].astext.like('%' + text_str + '%')
                ),
                *[
                    db.and_(
                        db_obj['text'].has_key(lang_code),
                        db_obj['text'][lang_code].astext.like('%' + text_str + '%')
                    )
                    for lang_code in languages.get_language_codes()
                ]
            )
        ),
        db.and_(
            db_obj['_type'].astext == 'plotly_chart',
            db_obj['plotly']['layout']['title']['text'].astext.like('%' + text_str + '%')
        )
    )


def sample_equals(db_obj: typing.Any, object_id: int) -> typing.Any:
    return db.and_(
        db_obj['_type'].astext == 'sample',
        db_obj['object_id'].astext.cast(db.Integer) == object_id
    )


def reference_equals(db_obj: typing.Any, reference_id: int) -> typing.Any:
    return db.or_(
        db.and_(
            db.or_(
                db_obj['_type'].astext == 'object_reference',
                db_obj['_type'].astext == 'sample',
                db_obj['_type'].astext == 'measurement'
            ),
            db_obj['object_id'].astext.cast(db.Integer) == reference_id
        ),
        db.and_(
            db_obj['_type'].astext == 'user',
            db_obj['user_id'].astext.cast(db.Integer) == reference_id
        ),
    )


def tags_contain(db_obj: typing.Any, tag: str) -> typing.Any:
    tag = tag.strip().lower()
    return db.and_(
        db_obj['_type'].astext == 'tags',
        db_obj['tags'].contains(json.dumps(tag))
    )


def attribute_not_set(db_obj: typing.Any) -> typing.Any:
    return db_obj == db.null()


def _has_file(db_obj: typing.Any, file_filter: db.ColumnElement[bool]) -> typing.Any:
    matching_files = db.select(
        File.object_id
    ).distinct().outerjoin(
        FileLogEntry,
        db.and_(
            FileLogEntry.object_id == File.object_id,
            FileLogEntry.file_id == File.id,
        )
    ).where(
        file_filter
    ).group_by(
        File.object_id,
        File.id
    ).having(
        db.func.sum(  # pylint: disable=not-callable
            db.case(
                {
                    'HIDE_FILE': 1,
                    'UNHIDE_FILE': -1
                },
                else_=0,
                value=FileLogEntry.type
            )
        ) == 0
    ).subquery()
    return db.and_(
        Objects.object_id_column == matching_files.c.object_id,
    )


def file_name_contains(db_obj: typing.Any, text: typing.Union[datatypes.Text, str]) -> typing.Any:
    if isinstance(text, datatypes.Text):
        text_str = get_translated_text(text.text)
    else:
        text_str = text
    return _has_file(
        db_obj,
        db.or_(
            File.data.op("->>")("url").cast(db.Text).like('%' + text_str + '%'),
            File.data.op("->>")("original_file_name").cast(db.Text).like('%' + text_str + '%'),
            File.data.op("->>")("filepath").cast(db.Text).like('%' + text_str + '%')
        )
    )


def file_name_equals(db_obj: typing.Any, text: typing.Union[datatypes.Text, str]) -> typing.Any:
    if isinstance(text, datatypes.Text):
        text_str = get_translated_text(text.text)
    else:
        text_str = text
    return _has_file(
        db_obj,
        db.or_(
            File.data.op("->>")("url").cast(db.Text) == text_str,
            File.data.op("->>")("original_file_name").cast(db.Text) == text_str,
            File.data.op("->>")("filepath").cast(db.Text) == text_str
        )
    )
