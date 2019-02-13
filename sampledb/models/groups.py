# coding: utf-8
"""

"""

from .. import db

association_table = db.Table(
    'user_group_memberships',
    db.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id'))
)


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.String, nullable=False, default='')
    members = db.relationship("User", secondary=association_table, backref="groups")
