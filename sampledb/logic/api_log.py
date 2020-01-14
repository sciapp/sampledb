# coding: utf-8
"""

"""

import datetime
import typing
from ..models import APILogEntry, HTTPMethod
from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def get_api_log_entries(api_token_id: int) -> typing.List[APILogEntry]:
    """
    Return a list of API log entries for a given API token.

    :param api_token_id: the ID of an existing API token
    :return: a list of API log entries for this token
    """
    return APILogEntry.query.filter_by(api_token_id=api_token_id).order_by(db.desc(APILogEntry.utc_datetime)).all()


def create_log_entry(api_token_id: int, method: HTTPMethod, route: str):
    """
    Create a new API log entry.

    :param api_token_id: the ID of an existing API token
    :param method: the HTTP method
    :param route: the route
    """
    api_log_entry = APILogEntry(
        api_token_id=api_token_id,
        method=method,
        route=route,
        utc_datetime=datetime.datetime.utcnow()
    )
    db.session.add(api_log_entry)
    db.session.commit()
