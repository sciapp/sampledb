# coding: utf-8
"""

"""

import enum
import typing

from .. import db


class ActionType(enum.Enum):
    SAMPLE_CREATION = 1
    MEASUREMENT = 2
    SIMULATION = 3


class Action(db.Model):
    __tablename__ = 'actions'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(ActionType), nullable=False)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False, default='')
    instrument_id = db.Column(db.Integer, db.ForeignKey("instruments.id"), nullable=True)
    instrument = db.relationship("Instrument", backref="actions")
    schema = db.Column(db.JSON, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", backref="actions")

    def __init__(self, action_type: ActionType, name: str, schema: dict, description: str = '', instrument_id: typing.Optional[int] = None, user_id: typing.Optional[int] = None):
        self.type = action_type
        self.name = name
        self.description = description
        self.instrument_id = instrument_id
        self.schema = schema
        self.user_id = user_id

    def __eq__(self, other):
        return (
            self.id == other.id and
            self.instrument_id == other.instrument_id and
            self.user_id == other.user_id and
            self.name == other.name and
            self.description == other.description and
            self.schema == other.schema
        )

    def __repr__(self):
        return '<{0}(id={1.id}, name={1.name})>'.format(type(self).__name__, self)
