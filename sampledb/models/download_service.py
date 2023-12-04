# coding: utf-8
"""

"""
import typing
import datetime

import flask
from sqlalchemy.orm import Mapped, Query

from .. import db
from .utils import Model


class DownloadServiceJobFile(Model):
    __tablename__ = 'download_service_job_files'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    file_id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    creation: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    expiration: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["DownloadServiceJobFile"]]

    __table_args__ = (
        db.ForeignKeyConstraint(['object_id', 'file_id'], ['files.object_id', 'files.id']),
    )

    def __init__(
            self,
            job_id: typing.Optional[int],
            object_id: int,
            file_id: int
    ) -> None:
        super().__init__(
            id=job_id,
            object_id=object_id,
            file_id=file_id,
            creation=datetime.datetime.now(datetime.timezone.utc),
            expiration=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=flask.current_app.config['DOWNLOAD_SERVICE_TIME_LIMIT'])
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, object_id={self.object_id}, file_id={self.file_id}'
