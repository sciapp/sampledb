# coding: utf-8
"""

"""

import enum
from .. import db
from .groups import Group
from .users import User
from .objects import Objects

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class Permissions(enum.Enum):
    NONE = 0
    READ = 1
    WRITE = 2  # includes READ
    GRANT = 3  # includes READ and WRITE

    def __contains__(self, item: 'Permissions') -> bool:
        return self.value >= item.value

    def __str__(self):
        return self.name.lower()

    @staticmethod
    def from_name(name):
        members = {
            'none': Permissions.NONE,
            'read': Permissions.READ,
            'write': Permissions.WRITE,
            'grant': Permissions.GRANT,
        }
        try:
            return members[name.lower()]
        except KeyError:
            raise ValueError('Invalid name')


class UserObjectPermissions(db.Model):
    __tablename__ = 'user_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, user_id),
        {},
    )


class GroupObjectPermissions(db.Model):
    __tablename__ = 'group_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey(Group.id), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, group_id),
        {},
    )


class PublicObjects(db.Model):
    __tablename__ = 'public_objects'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
