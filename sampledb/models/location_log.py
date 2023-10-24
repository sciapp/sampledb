import datetime
import enum
import typing

from sqlalchemy.orm import Query, Mapped

from .. import db
from .utils import Model


@enum.unique
class LocationLogEntryType(enum.Enum):
    OTHER = 0
    CREATE_LOCATION = 1
    UPDATE_LOCATION = 2
    ADD_OBJECT = 3
    CHANGE_OBJECT = 4
    REMOVE_OBJECT = 5


class LocationLogEntry(Model):
    __tablename__ = 'location_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[LocationLogEntryType] = db.Column(db.Enum(LocationLogEntryType), nullable=False)
    location_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    user_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["LocationLogEntry"]]

    def __init__(
            self,
            location_id: int,
            user_id: typing.Optional[int],
            type: LocationLogEntryType,
            data: typing.Dict[str, typing.Any],
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            type=type,
            location_id=location_id,
            user_id=user_id,
            data=data,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, location_id={self.location_id}, user_id={self.user_id}, utc_datetime={self.utc_datetime}, data={self.data})>'
