# coding: utf-8
"""
RESTful API for SampleDB
"""

import flask

from ..utils import Resource, ResponseData
from ...api.server.authentication import multi_auth
from ...logic.object_log import get_object_log_entries_by_user, object_log_entry_to_json


class ObjectLogEntries(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        after_id = 0
        after_id_str = flask.request.args.get('after_id')
        if after_id_str is not None:
            try:
                after_id = max(int(after_id_str), 0)
            except ValueError:
                pass

        log_entries = get_object_log_entries_by_user(flask.g.user.id, after_id)
        return [object_log_entry_to_json(log_entry) for log_entry in log_entries]
