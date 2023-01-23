# coding: utf-8
"""

"""
from datetime import datetime, timedelta

import flask

from .. import db


class DownloadServiceJobFile(db.Model):  # type: ignore
    __tablename__ = 'download_service_job_files'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    object_id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, primary_key=True)
    creation = db.Column(db.DateTime)
    expiration = db.Column(db.DateTime)

    __table_args__ = (
        db.ForeignKeyConstraint(['object_id', 'file_id'], ['files.object_id', 'files.id']),
    )

    def __init__(
            self,
            job_id: int,
            object_id: int,
            file_id: int
    ) -> None:
        self.id = job_id
        self.object_id = object_id
        self.file_id = file_id
        self.creation = datetime.now()
        self.expiration = self.creation + timedelta(seconds=flask.current_app.config['DOWNLOAD_SERVICE_TIME_LIMIT'])

    def __repr__(self) -> str:
        return '<{0}(id={1.id}, object_id={1.object_id}, file_id={1.file_id}' \
            .format(type(self).__name__, self)
