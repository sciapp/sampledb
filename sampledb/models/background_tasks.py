import enum

import datetime
from .. import db


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


class BackgroundTask(db.Model):  # type: ignore
    __tablename__ = 'background_tasks'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Text, nullable=False)
    auto_delete = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    data = db.Column(db.JSON, nullable=False)
    status = db.Column(db.Enum(BackgroundTaskStatus), nullable=False)
    result = db.Column(db.JSON, nullable=True)
    expiration_date = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def delete_expired_tasks() -> None:
        expired_tasks = BackgroundTask.query.filter(BackgroundTask.expiration_date <= datetime.datetime.utcnow()).all()
        for task in expired_tasks:
            db.session.delete(task)
        db.session.commit()

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, type={self.type}, auto_delete={self.auto_delete}, data={self.data}, status={self.status})>'
