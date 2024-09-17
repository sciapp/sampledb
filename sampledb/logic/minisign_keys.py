# coding: utf-8
"""

"""
import typing

import minisign

from .. import db
from .. import models


def create_dummy_kps():
    if len(db.session.query(models.KeyPair).all()) < 2:
        for i in range(2):
            new_key_pair = minisign.KeyPair.generate()
            kp = models.KeyPair(sk_bytes=bytes(new_key_pair.secret_key), pk_bytes=bytes(new_key_pair.public_key))
            db.session.add(kp)
        db.session.commit()

    # create_dummy_kps()


# TODO manage keys, keypair expiration?
def get_current_key_pair() -> models.KeyPair:
    kp = db.session.query(models.KeyPair).first()
    if kp is None:
        new_key_pair = minisign.KeyPair.generate()
        kp = models.KeyPair(sk_bytes=bytes(new_key_pair.secret_key), pk_bytes=bytes(new_key_pair.public_key))
        db.session.add(kp)
        db.session.commit()
    return kp


def new_key_pair() -> None:
    key_pair = minisign.KeyPair.generate()
    kp = models.KeyPair(sk_bytes=bytes(key_pair.secret_key), pk_bytes=bytes(key_pair.public_key))
    db.session.add(kp)
    db.session.commit()


def get_key_pairs() -> typing.List[models.KeyPair]:
    return db.session.query(models.KeyPair).all()


def get_key_pair_by_id(id: int) -> models.KeyPair:
    kp = db.session.query(models.KeyPair).filter(models.KeyPair.id==id).first()
    return kp