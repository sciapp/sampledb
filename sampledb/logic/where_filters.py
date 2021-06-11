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

import operator
import json
import sqlalchemy as db
from . import datatypes
from . import languages

EPSILON = 1e-7

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def float_operator_equals(left, right):
    return db.and_(
        left * (1 - EPSILON) <= right,
        left * (1 + EPSILON) >= right
    )


def float_operator_less_than_equals(left, right):
    return db.and_(
        left * (1 - EPSILON) <= right
    )


def float_operator_greater_than_equals(left, right):
    return db.and_(
        left * (1 + EPSILON) >= right
    )


def quantity_binary_operator(db_obj, other, operator):
    return db.and_(
        db_obj['_type'].astext == 'quantity',
        db_obj['dimensionality'].astext == str(other.dimensionality),
        operator(db_obj['magnitude_in_base_units'].astext.cast(db.Float), other.magnitude_in_base_units)
    )


def quantity_equals(db_obj, other):
    return quantity_binary_operator(db_obj, other, float_operator_equals)


def quantity_less_than(db_obj, other):
    return quantity_binary_operator(db_obj, other, operator.lt)


def quantity_less_than_equals(db_obj, other):
    return quantity_binary_operator(db_obj, other, float_operator_less_than_equals)


def quantity_greater_than(db_obj, other):
    return quantity_binary_operator(db_obj, other, operator.gt)


def quantity_greater_than_equals(db_obj, other):
    return quantity_binary_operator(db_obj, other, float_operator_greater_than_equals)


def quantity_between(db_obj, left, right, including=True):
    if left.dimensionality != right.dimensionality:
        return False
    if including:
        return db.and_(
            db_obj['_type'].astext == 'quantity',
            db_obj['dimensionality'].astext == str(left.dimensionality),
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) * (1 + EPSILON) >= left.magnitude_in_base_units,
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) * (1 - EPSILON) <= right.magnitude_in_base_units
        )
    else:
        return db.and_(
            db_obj['_type'].astext == 'quantity',
            db_obj['dimensionality'].astext == str(left.dimensionality),
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) > left.magnitude_in_base_units,
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) < right.magnitude_in_base_units
        )


def datetime_binary_operator(db_obj, other, operator):
    if isinstance(other, datatypes.DateTime):
        other = other.utc_datetime
    other = other.date()
    return db.and_(
        db_obj['_type'].astext == 'datetime',
        operator(db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD'), other)
    )


def datetime_equals(db_obj, other):
    return datetime_binary_operator(db_obj, other, operator.eq)


def datetime_less_than(db_obj, other):
    return datetime_binary_operator(db_obj, other, operator.lt)


def datetime_less_than_equals(db_obj, other):
    return datetime_binary_operator(db_obj, other, operator.le)


def datetime_greater_than(db_obj, other):
    return datetime_binary_operator(db_obj, other, operator.gt)


def datetime_greater_than_equals(db_obj, other):
    return datetime_binary_operator(db_obj, other, operator.ge)


def datetime_between(db_obj, left, right, including=True):
    if isinstance(left, datatypes.DateTime):
        left = left.utc_datetime
    if isinstance(right, datatypes.DateTime):
        right = right.utc_datetime
    left = left.date()
    right = right.date()
    if including:
        return db.and_(
            db_obj['_type'].astext == 'datetime',
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD') >= left,
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD') <= right,
        )
    else:
        return db.and_(
            db_obj['_type'].astext == 'datetime',
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD') > left,
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD') < right,
        )


def boolean_equals(db_obj, value):
    if isinstance(value, datatypes.Boolean):
        value = value.value
    return db.and_(
        db_obj['_type'].astext == 'bool',
        db_obj['value'].astext.cast(db.Boolean) == value
    )


def boolean_true(db_obj):
    return boolean_equals(db_obj, True)


def boolean_false(db_obj):
    return boolean_equals(db_obj, False)


def text_equals(db_obj, text):
    if isinstance(text, datatypes.Text):
        text = text.text
    return db.or_(
        db.and_(
            db_obj['_type'].astext == 'text',
            db.or_(
                db.and_(
                    db_obj['text']['en'].astext == db.null(),
                    db_obj['text'].astext == text,
                ),
                db.and_(
                    db_obj['text']['en'].astext != db.null(),
                    db.or_(
                        *[
                            db_obj['text'][language.lang_code].astext == text
                            for language in languages.get_languages()
                        ]
                    )
                )
            )
        ),
        db.and_(
            db_obj['_type'].astext == 'plotly_chart',
            db_obj['plotly']['layout']['title']['text'].astext == text
        )
    )


def text_contains(db_obj, text):
    if isinstance(text, datatypes.Text):
        text = text.text
    return db.or_(
        db.and_(
            db_obj['_type'].astext == 'text',
            db.or_(
                db.and_(
                    db_obj['text']['en'].astext == db.null(),
                    db_obj['text'].astext.like('%' + text + '%')
                ),
                db.and_(
                    db_obj['text']['en'].astext != db.null(),
                    db.or_(
                        *[
                            db_obj['text'][language.lang_code].astext.like('%' + text + '%')
                            for language in languages.get_languages()
                        ]
                    )
                )
            )
        ),
        db.and_(
            db_obj['_type'].astext == 'plotly_chart',
            db_obj['plotly']['layout']['title']['text'].astext.like('%' + text + '%')
        )
    )


def sample_equals(db_obj, object_id):
    return db.and_(
        db_obj['_type'].astext == 'sample',
        db_obj['object_id'].astext.cast(db.Integer) == object_id
    )


def tags_contain(db_obj, tag):
    tag = tag.strip().lower()
    return db.and_(
        db_obj['_type'].astext == 'tags',
        db_obj['tags'].contains(json.dumps(tag))
    )
