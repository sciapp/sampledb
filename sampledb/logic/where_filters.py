# coding: utf-8
"""
This module defines functions which can help filtering objects by using the sampledb.datetypes types. Each function
returns a SQLAlchemy object which can be used for the filter_func in
VersionedJSONSerializableObjectTables.get_current_objects().
"""

import operator
import sqlalchemy as db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def quantity_binary_operator(db_obj, other, operator):
    return db.and_(
        db_obj['_type'].astext == 'quantity',
        db_obj['dimensionality'].astext == str(other.dimensionality),
        operator(db_obj['magnitude_in_base_units'].astext.cast(db.Float), other.maginitude_in_base_units)
    )


def quantity_equals(db_obj, other):
    return quantity_binary_operator(db_obj, other, operator.eq)


def quantity_less_than(db_obj, other):
    return quantity_binary_operator(db_obj, other, operator.lt)


def quantity_less_than_equals(db_obj, other):
    return quantity_binary_operator(db_obj, other, operator.le)


def quantity_greater_than(db_obj, other):
    return quantity_binary_operator(db_obj, other, operator.gt)


def quantity_greater_than_equals(db_obj, other):
    return quantity_binary_operator(db_obj, other, operator.ge)


def quantity_between(db_obj, left, right, including=True):
    if left.dimensionality != right.dimensionality:
        return False
    if including:
        return db.and_(
            db_obj['_type'].astext == 'quantity',
            db_obj['dimensionality'].astext == str(left.dimensionality),
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) >= left.maginitude_in_base_units,
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) <= right.maginitude_in_base_units
        )
    else:
        return db.and_(
            db_obj['_type'].astext == 'quantity',
            db_obj['dimensionality'].astext == str(left.dimensionality),
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) > left.maginitude_in_base_units,
            db_obj['magnitude_in_base_units'].astext.cast(db.Float) < right.maginitude_in_base_units
        )


def datetime_binary_operator(db_obj, other, operator):
    return db.and_(
        db_obj['_type'].astext == 'datetime',
        operator(db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD HH24:MI:SS'), other.utc_datetime)
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
    if including:
        return db.and_(
            db_obj['_type'].astext == 'datetime',
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD HH24:MI:SS') >= left.utc_datetime,
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD HH24:MI:SS') <= right.utc_datetime,
        )
    else:
        return db.and_(
            db_obj['_type'].astext == 'datetime',
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD HH24:MI:SS') > left.utc_datetime,
            db.func.to_timestamp(db_obj['utc_datetime'].astext, 'YYYY-MM-DD HH24:MI:SS') < right.utc_datetime,
        )


def boolean_equals(db_obj, value):
    return db.and_(
        db_obj['_type'].astext == 'bool',
        db_obj['value'].astext.cast(db.Boolean) == value
    )


def boolean_true(db_obj):
    return boolean_equals(db_obj, True)


def boolean_false(db_obj):
    return boolean_equals(db_obj, False)


def text_equals(db_obj, text):
    return db.and_(
        db_obj['_type'].astext == 'text',
        db_obj['text'].astext == text
    )


def text_contains(db_obj, text):
    return db.and_(
        db_obj['_type'].astext == 'text',
        db_obj['text'].astext.like('%'+text+'%')
    )


def sample_equals(db_obj, object_id):
    return db.and_(
        db_obj['_type'].astext == 'sample',
        db_obj['object_id'].astext.cast(db.Integer) == object_id
    )
