# coding: utf-8
"""

"""

from .. import db


class ActionTypeTranslation(db.Model):
    __tablename__ = 'action_type_translations'

    id = db.Column(db.Integer, primary_key=True)

    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'))
    language = db.relationship('Language')

    action_type_id = db.Column(db.Integer, db.ForeignKey('action_types.id'))
    action_types = db.relationship("ActionType")

    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    object_name = db.Column(db.String, nullable=False)
    object_name_plural = db.Column(db.String, nullable=False)
    view_text = db.Column(db.String, nullable=False)
    perform_text = db.Column(db.String, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('language_id', 'action_type_id', name='_language_id_action_type_id_uc'),
    )

    def __init__(self, language_id: int, action_type_id: int, name: str, description: str, object_name: str, object_name_plural: str,
                 view_text: str, perform_text: str):
        self.language_id = language_id,
        self.action_type_id = action_type_id,
        self.name = name,
        self.description = description,
        self.object_name = object_name,
        self.object_name_plural = object_name_plural,
        self.view_text = view_text,
        self.perform_text = perform_text

    def __eq__(self, other):
        return (
            self.id == other.id and
            self.language_id == other.language_id and
            self.action_type_id == other.action_type_id and
            self.name == other.name and
            self.description == other.description and
            self.object_name == other.object_name and
            self.object_name_plural == other.object_name_plural and
            self.view_text == other.view_text and
            self.perform_text == other.perform_text
        )

    def __repr__(self):
        return '<{0}(id={1.id!r}, name={1.name!r})>'.format(type(self).__name__, self)


class ActionTranslation(db.Model):
    __tablename__ = 'action_translations'

    id = db.Column(db.Integer, primary_key=True)

    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'))
    language = db.relationship('Language')

    action_id = db.Column(db.Integer, db.ForeignKey('actions.id'))
    action = db.relationship("Action")

    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False, default='')
    short_description = db.Column(db.String, nullable=False, default='')

    __table_args__ = (
        db.UniqueConstraint('language_id', 'action_id', name='_language_id_action_id_uc'),
    )

    def __init__(self,
                 action_id: int,
                 language_id: int,
                 name: str,
                 description: str = '',
                 short_description: str = '',
                 ):

        self.action_id = action_id
        self.language_id = language_id
        self.name = name
        self.description = description
        self.short_description = short_description

    def __eq__(self, other):
        return (
            self.id == other.id and
            self.action_id == other.action_id and
            self.language_id == other.language_id and
            self.name == other.name and
            self.description == other.description and
            self.short_description == other.short_description
        )

    def __repr__(self):
        return '<{0}(id={1.id!r})>'.format(type(self).__name__, self)
