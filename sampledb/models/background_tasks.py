import enum
import datetime
import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .utils import Model


@enum.unique
class BackgroundTaskStatus(enum.Enum):
    POSTED = 0
    CLAIMED = 1
    DONE = 2
    FAILED = 3

    def is_final(self) -> bool:
        return self in {
            BackgroundTaskStatus.DONE,
            BackgroundTaskStatus.FAILED
        }


class BackgroundTask(Model):
    __tablename__ = 'background_tasks'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    type: Mapped[str] = db.Column(db.Text, nullable=False)
    auto_delete: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    data: Mapped[typing.Dict[str, typing.Any]] = db.Column(db.JSON, nullable=False)
    status: Mapped[BackgroundTaskStatus] = db.Column(db.Enum(BackgroundTaskStatus), nullable=False)
    result: Mapped[typing.Optional[typing.Dict[str, typing.Any]]] = db.Column(db.JSON, nullable=True)
    expiration_date: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.TIMESTAMP(timezone=True), nullable=True)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["BackgroundTask"]]

    @staticmethod
    def delete_expired_tasks() -> None:
        expired_tasks = BackgroundTask.query.filter(BackgroundTask.expiration_date <= datetime.datetime.now(datetime.timezone.utc)).all()
        for task in expired_tasks:
            db.session.delete(task)
        db.session.commit()

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, auto_delete={self.auto_delete}, data={self.data}, status={self.status})>'
