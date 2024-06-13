# coding: utf-8
"""

"""
import datetime
import typing

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, Query, relationship

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User
    from .group_categories import GroupCategory


association_table = db.Table(
    'user_group_memberships',
    db.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('groups.id'))
)


class Group(Model):
    __tablename__ = 'groups'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[typing.Dict[str, str]] = db.Column(postgresql.JSON, nullable=False)
    description: Mapped[typing.Dict[str, str]] = db.Column(postgresql.JSON, nullable=False)
    members: Mapped[typing.List['User']] = relationship("User", secondary=association_table, back_populates="groups")
    categories: Mapped[typing.List['GroupCategory']] = relationship('GroupCategory', secondary='basic_group_category_association_table', back_populates='basic_groups')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Group"]]


class GroupInvitation(Model):
    __tablename__ = 'group_invitations'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    group_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey(Group.id, ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    inviter_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    accepted: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    revoked: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())  # TODO: migration

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["GroupInvitation"]]
