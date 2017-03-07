# coding: utf-8
"""

"""

import enum
from .. import db
from ..authentication import User
from ..object_database import Objects

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class Permissions(enum.Enum):
    NONE = 0
    READ = 1
    WRITE = 2  # includes READ
    GRANT = 3  # includes READ and WRITE

    def __contains__(self, item: 'Permissions') -> bool:
        return self.value >= item.value


class UserObjectPermissions(db.Model):
    __tablename__ = 'user_object_permissions'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    permissions = db.Column(db.Enum(Permissions), nullable=False, default=Permissions.NONE)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, user_id),
        {},
    )


class PublicObjects(db.Model):
    __tablename__ = 'public_objects'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
