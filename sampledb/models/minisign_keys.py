# coding: utf-8
"""

"""

import minisign

from sqlalchemy.orm import Mapped

from .. import db
from .utils import Model


class SecretKey(Model):
    __tablename__ = 'secret_keys'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    sk_bytes: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)

    def __init__(self, sk_bytes: bytes):
        super().__init__(sk_bytes=sk_bytes)

    def __repr__(self) -> str:
        sk = minisign.SecretKey.from_bytes(self.sk_bytes)
        return f'<{type(self).__name__}(id={self.id}, untrusted_comment={sk._untrusted_comment})>'


class PublicKey(Model):
    __tablename__ = 'public_keys'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    pk_bytes: Mapped[bytes] = db.Column(db.LargeBinary, nullable=False)

    def __init__(self, pk_bytes: bytes):
        super().__init__(pk_bytes=pk_bytes)

    def __repr__(self) -> str:
        pk = minisign.PublicKey.from_bytes(self.pk_bytes)
        return f'<{type(self).__name__}(id={self.id}, untrusted_comment={pk._untrusted_comment})>'