import enum

from .. import db


@enum.unique
class BackgroundTaskStatus(enum.Enum):
    POSTED = 0,
    CLAIMED = 1,
    DONE = 2,
    FAILED = 3

    def is_final(self) -> bool:
        return self in {
            BackgroundTaskStatus.DONE,
            BackgroundTaskStatus.FAILED
        }


class BackgroundTask(db.Model):  # type: ignore
    __tablename__ = 'background_tasks'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Text, nullable=False)
    auto_delete = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    data = db.Column(db.JSON, nullable=False)
    status = db.Column(db.Enum(BackgroundTaskStatus), nullable=False)

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, type={1.type}, auto_delete={1.auto_delete}, data={1.data}, status={1.status})>'.format(type(self).__name__, self)
