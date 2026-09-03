import typing

import flask
from pydantic import BaseModel, Field

from ..utils import Resource
from .authentication import multi_auth
from ...logic.object_log import get_object_log_entries_by_user
from .utils.openapi import method
from ...models import object_log


class ObjectLogEntryModel(BaseModel):
    log_entry_id: int = Field(description="the ID of the object log entry", examples=[1])
    type: str = Field(description="the type of the object log entry", examples=["CREATE_OBJECT"])
    object_id: int = Field(description="the ID of the object the log entry belongs to", examples=[1])
    user_id: int = Field(description="the ID of the user who caused the object log entry", examples=[1])
    data: typing.Dict[str, typing.Any] = Field(description="the data of the log entry", examples=[{}])
    utc_datetime: str = Field(description="the datetime in UTC when the object log entry was created, formatted as YYYY-MM-DD HH:MM:SS", examples=["2026-01-02 03:04:05"])
    is_imported: bool = Field(description="whether the object log entry was imported", examples=[False])

    @classmethod
    def from_object_log_entry(cls, log_entry: object_log.ObjectLogEntry) -> typing.Self:
        return cls(
            log_entry_id=log_entry.id,
            type=log_entry.type.name,
            object_id=log_entry.object_id,
            user_id=log_entry.user_id,
            data={key: value for key, value in log_entry.data.items() if key not in ['object', 'sample', 'measurement']},
            utc_datetime=log_entry.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            is_imported=log_entry.is_imported
        )


class ObjectLogEntries(Resource):
    class QueryModel(BaseModel):
        after_id: int = Field(0, description="the ID of an existing log entry — filter for log entries with an ID greater than this one", examples=[0])

    @multi_auth.login_required
    @method()
    def get(self, query: QueryModel) -> typing.List[ObjectLogEntryModel]:
        """
        List all object log entries.
        """
        after_id = max(query.after_id, 0)
        log_entries = get_object_log_entries_by_user(flask.g.user.id, after_id)
        return [
            ObjectLogEntryModel.from_object_log_entry(log_entry)
            for log_entry in log_entries
        ]
