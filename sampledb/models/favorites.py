# coding: utf-8
"""
Models for users' favorite actions and instruments.
"""

from .. import db


class FavoriteAction(db.Model):
    __tablename__ = 'favorite_actions'

    action_id = db.Column(db.Integer, db.ForeignKey("actions.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)


class FavoriteInstrument(db.Model):
    __tablename__ = 'favorite_instruments'

    instrument_id = db.Column(db.Integer, db.ForeignKey("instruments.id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
