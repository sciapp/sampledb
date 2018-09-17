# coding: utf-8
"""

"""

from .. import db


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    uses = db.Column(db.Integer, nullable=False, default=0)
