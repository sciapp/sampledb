# coding: utf-8
"""

"""

from .. import db
import sqlalchemy.dialects.postgresql as postgresql


association_table = db.Table(
    'user_group_memberships',
    db.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id'))
)


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(postgresql.JSON, nullable=False)
    description = db.Column(postgresql.JSON, nullable=False)
    members = db.relationship("User", secondary=association_table, backref="groups")


class GroupInvitation(db.Model):
    __tablename__ = 'group_invitations'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    accepted = db.Column(db.Boolean, nullable=False, default=False)
