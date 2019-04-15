# coding: utf-8
"""

"""

from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

instrument_user_association_table = db.Table(
    'association',
    db.metadata,
    db.Column('instrument_id', db.Integer, db.ForeignKey('instruments.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
)


class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    description = db.Column(db.String, nullable=False, default='')
    responsible_users = db.relationship("User", secondary=instrument_user_association_table, order_by="User.name")

    def __init__(self, name, description=''):
        self.name = name
        self.description = description

    def __eq__(self, other):
        return (
            self.id == other.id and
            self.name == other.name and
            self.description == other.description and
            self.responsible_users == other.responsible_users
        )

    def __repr__(self):
        return '<{0}(id={1.id}, name={1.name})>'.format(type(self).__name__, self)
