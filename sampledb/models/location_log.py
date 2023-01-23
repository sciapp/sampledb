import datetime
import enum
import typing

from .. import db


@enum.unique
class LocationLogEntryType(enum.Enum):
    OTHER = 0
    CREATE_LOCATION = 1
    UPDATE_LOCATION = 2
    ADD_OBJECT = 3
    CHANGE_OBJECT = 4
    REMOVE_OBJECT = 5


class LocationLogEntry(db.Model):  # type: ignore
    __tablename__ = 'location_log_entries'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(LocationLogEntryType), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    data = db.Column(db.JSON, nullable=False)
    utc_datetime = db.Column(db.DateTime, nullable=False)

    def __init__(
            self,
            location_id: int,
            user_id: typing.Optional[int],
            type: LocationLogEntryType,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        self.location_id = location_id
        self.user_id = user_id
        self.type = type
        self.data = data
        if utc_datetime is None:
            utc_datetime = datetime.datetime.utcnow()
        self.utc_datetime = utc_datetime

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, type={1.type}, location_id={1.location_id}, user_id={1.user_id}, utc_datetime={1.utc_datetime}, data={1.data})>'.format(type(self).__name__, self)
