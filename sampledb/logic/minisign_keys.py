# coding: utf-8
"""

"""

import minisign
from minisign import KeyPair

from .. import db
from .. import models

# TODO manage keys, keypair expiration?
def get_key_pair() -> minisign.KeyPair:
    sk = db.session.query(models.SecretKey).first()
    if sk is None:
        keypair = minisign.KeyPair.generate()
        db.session.add(models.SecretKey(sk_bytes=bytes(keypair.secret_key)))
        db.session.add(models.PublicKey(pk_bytes=bytes(keypair.public_key)))
        return keypair
    else:
        secret_key = minisign.SecretKey.from_bytes(sk.sk_bytes)
        public_key = minisign.PublicKey.from_secret_key(secret_key)
        return KeyPair(secret_key, public_key)