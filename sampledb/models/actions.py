# coding: utf-8
"""

"""

import typing

from .. import db


class ActionType(db.Model):
    __tablename__ = 'action_types'

    # default action type IDs
    # offset to -100 to allow later addition of new default action types
    # see: migrations/action_type_create_default_action_types.py
    SAMPLE_CREATION = -100 + 1
    MEASUREMENT = -100 + 2
    SIMULATION = -100 + 3

    id = db.Column(db.Integer, primary_key=True)
    admin_only = db.Column(db.Boolean, nullable=False, default=False)
    show_on_frontpage = db.Column(db.Boolean, nullable=False, default=False)
    show_in_navbar = db.Column(db.Boolean, nullable=False, default=False)
    enable_labels = db.Column(db.Boolean, nullable=False, default=True)
    enable_files = db.Column(db.Boolean, nullable=False, default=True)
    enable_locations = db.Column(db.Boolean, nullable=False, default=True)
    enable_publications = db.Column(db.Boolean, nullable=False, default=True)
    enable_comments = db.Column(db.Boolean, nullable=False, default=True)
    enable_activity_log = db.Column(db.Boolean, nullable=False, default=True)
    enable_related_objects = db.Column(db.Boolean, nullable=False, default=True)
    enable_project_link = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    def __repr__(self):
        return '<{0}(id={1.id!r}, name={1.name!r})>'.format(type(self).__name__, self)


class Action(db.Model):
    __tablename__ = 'actions'

    id = db.Column(db.Integer, primary_key=True)
    type_id = db.Column(db.Integer, db.ForeignKey("action_types.id"), nullable=False)
    type = db.relationship(ActionType)
    instrument_id = db.Column(db.Integer, db.ForeignKey("instruments.id"), nullable=True)
    instrument = db.relationship("Instrument", backref="actions")
    schema = db.Column(db.JSON, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", backref="actions")
    description_is_markdown = db.Column(db.Boolean, nullable=False, default=False)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False)
    short_description_is_markdown = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(
            self,
            action_type_id: int,
            schema: dict,
            instrument_id: typing.Optional[int] = None,
            user_id: typing.Optional[int] = None,
            description_is_markdown: bool = False,
            is_hidden: bool = False,
            short_description_is_markdown: bool = False
    ):

        self.type_id = action_type_id
        self.instrument_id = instrument_id
        self.schema = schema
        self.user_id = user_id
        self.description_is_markdown = description_is_markdown
        self.is_hidden = is_hidden
        self.short_description_is_markdown = short_description_is_markdown

    def __eq__(self, other):
        return (
            self.id == other.id and
            self.instrument_id == other.instrument_id and
            self.user_id == other.user_id and
            self.description_is_markdown == other.description_is_markdown and
            self.short_description_is_markdown == other.short_description_is_markdown and
            self.is_hidden == other.is_hidden and
            self.schema == other.schema
        )

    def __repr__(self):
        return '<{0}(id={1.id!r})>'.format(type(self).__name__, self)
