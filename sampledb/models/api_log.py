# coding: utf-8
"""

"""

import enum
import datetime

from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@enum.unique
class HTTPMethod(enum.Enum):
    GET = 0
    POST = 1
    PUT = 2
    PATCH = 3
    DELETE = 4
    HEAD = 5
    OPTIONS = 6
    OTHER = 7


class APILogEntry(db.Model):
    __tablename__ = 'api_log_entries'

    id = db.Column(db.Integer, primary_key=True)
    api_token_id = db.Column(db.Integer, db.ForeignKey('authentications.id'), nullable=False)
    method = db.Column(db.Enum(HTTPMethod), nullable=False)
    route = db.Column(db.String, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)
    api_token = db.relationship('Authentication', backref=db.backref("api_log_entries", cascade="all,delete"))

    def __init__(self, api_token_id, method, route, utc_datetime=None):
        self.api_token_id = api_token_id
        self.method = method
        self.route = route
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self):
        return '<{0}(id={1.id}, api_token_id={1.api_token_id}, method={1.method}, route={1.route}, utc_datetime={1.utc_datetime})>'.format(type(self).__name__, self)
