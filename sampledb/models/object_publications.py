# coding: utf-8
"""

"""

from .. import db
from . import Objects


class ObjectPublication(db.Model):
    __tablename__ = 'object_publications'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), nullable=False)
    doi = db.Column(db.String, nullable=False)
    title = db.Column(db.String)
    object_name = db.Column(db.String)

    __table_args__ = (
        db.PrimaryKeyConstraint(object_id, doi),
        {},
    )
