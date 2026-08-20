# coding: utf-8
"""
RESTful API for SampleDB
"""

import flask
from pydantic import BaseModel, Field

from ..utils import Resource, ResponseData
from .authentication import multi_auth
from ...logic.object_log import get_object_log_entries_by_user, object_log_entry_to_json
from .utils.validation import method


class ObjectLogEntries(Resource):
    class QueryModel(BaseModel):
        after_id: int = Field(0, description="the ID of an existing log entry — filter for log entries with an ID greater than this one", examples=[0])

    @multi_auth.login_required
    @method()
    def get(self, query: QueryModel) -> ResponseData:
        """
        List all object log entries.
        """
        after_id = max(query.after_id, 0)
        log_entries = get_object_log_entries_by_user(flask.g.user.id, after_id)
        return [object_log_entry_to_json(log_entry) for log_entry in log_entries]
