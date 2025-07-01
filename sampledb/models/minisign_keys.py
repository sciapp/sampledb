# coding: utf-8
"""

"""

import datetime
import typing

from sqlalchemy.orm import Mapped

from .. import db
from .utils import Model


class KeyPair(Model):
    __tablename__ = 'key_pairs'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    sk_bytes: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)
    pk_bytes: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)
    utc_datetime_created: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)

    def __init__(
            self,
            sk_bytes: bytes,
            pk_bytes: bytes,
            utc_datetime_created: typing.Optional[datetime.datetime] = None
    ):
        super().__init__(
            sk_bytes=sk_bytes,
            pk_bytes=pk_bytes,
            utc_datetime_created=utc_datetime_created if utc_datetime_created is not None else
            datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        )
