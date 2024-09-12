# coding: utf-8
"""

"""

import minisign

from sqlalchemy.orm import Mapped

from .. import db
from .utils import Model


class KeyPair(Model):
    __tablename__ = 'key_pairs'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    sk_bytes: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)
    pk_bytes: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)

    def __init__(self, sk_bytes: bytes, pk_bytes: bytes):
        super().__init__(sk_bytes=sk_bytes, pk_bytes=pk_bytes)
