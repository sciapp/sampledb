# coding: utf-8
"""

"""

import datetime
import typing

from .. import db
from .objects import Objects
from .users import User


class DataverseExport(db.Model):
    __tablename__ = 'dataverse_exports'

    object_id = db.Column(db.Integer, db.ForeignKey(Objects.object_id_column), primary_key=True)
    dataverse_url = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)

    def __init__(self, object_id: int, dataverse_url: str, user_id: int, utc_datetime: typing.Optional[datetime.datetime] = None):
        self.object_id = object_id
        self.dataverse_url = dataverse_url
        self.user_id = user_id
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self):
        return '<{0}(object_id={1.object_id}, dataverse_url={1.dataverse_url})>'.format(type(self).__name__, self)
