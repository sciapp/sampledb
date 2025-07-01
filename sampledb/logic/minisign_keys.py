# coding: utf-8
"""

"""
import dataclasses
import datetime
import typing

import minisign

from .. import db
from .. models import minisign_keys


@dataclasses.dataclass(frozen=True)
class KeyPair:
    """
    This class provides an immutable wrapper around models.minisign_keys.KeyPair.
    """
    id: int
    sk_bytes: bytes
    pk_bytes: bytes
    utc_datetime_created: datetime.datetime

    @classmethod
    def from_database(cls, key_pair: minisign_keys.KeyPair) -> 'KeyPair':
        return KeyPair(
            id=key_pair.id,
            sk_bytes=key_pair.sk_bytes,
            pk_bytes=key_pair.pk_bytes,
            utc_datetime_created=key_pair.utc_datetime_created
        )


def get_current_key_pair() -> KeyPair:
    kp = db.session.query(minisign_keys.KeyPair).first()
    if kp is None:
        return new_key_pair()
    return KeyPair.from_database(kp)


def new_key_pair() -> KeyPair:
    key_pair = minisign.KeyPair.generate()
    kp = minisign_keys.KeyPair(sk_bytes=bytes(key_pair.secret_key), pk_bytes=bytes(key_pair.public_key))
    db.session.add(kp)
    db.session.commit()
    return KeyPair.from_database(kp)


def get_key_pairs() -> typing.List[KeyPair]:
    kps = db.session.query(minisign_keys.KeyPair).all()
    return [KeyPair.from_database(kp) for kp in kps]


def get_key_pair_by_id(id: int) -> typing.Optional[KeyPair]:
    kp = db.session.query(minisign_keys.KeyPair).filter(minisign_keys.KeyPair.id == id).first()
    return KeyPair.from_database(kp) if kp else None
