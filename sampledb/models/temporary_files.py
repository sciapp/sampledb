
import datetime
import typing

from sqlalchemy.orm import Query, Mapped, relationship

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .users import User


class TemporaryFile(Model):
    __tablename__ = 'temporary_files'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    context_id: Mapped[str] = db.Column(db.String, nullable=False)
    file_name: Mapped[str] = db.Column(db.String, nullable=False)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    binary_data: Mapped[bytes] = db.deferred(db.Column(db.LargeBinary, nullable=False))
    uploader: Mapped['User'] = relationship('User')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["TemporaryFile"]]
