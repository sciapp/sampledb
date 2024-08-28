# coding: utf-8
"""

"""

from ..logic import minisign_keys
from . import frontend

@frontend.route('/.well-known/pub-key/')
def minisign_pub_key() -> bytes:
    kp = minisign_keys.get_key_pair()
    return kp.public_key.to_base64()