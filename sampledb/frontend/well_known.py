# coding: utf-8
"""

"""
import json

import flask
import minisign

from ..logic import minisign_keys
from . import frontend
from ..utils import FlaskResponseT


@frontend.route('/.well-known/pub-key/')
def minisign_pub_key() -> bytes:
    kp = minisign_keys.get_key_pair()
    public_key = minisign.PublicKey.from_bytes(kp.pk_bytes)
    return public_key.to_base64()


@frontend.route('/.well-known/keys.json/')
def key_list_json() -> FlaskResponseT:
    key_pairs = minisign_keys.get_key_pairs()
    res = [
        {
            "@context": "https://schema.org",
	        "@type": "MediaObject",
            #TODO replace hardcoded URL
            "url": "http://localhost:8000/.well-known/keys/" + str(kp.id),
            "name": "ed25519_pub_" + str(kp.id)
        }
        for kp in key_pairs
    ]
    return json.dumps(res)


@frontend.route('/.well-known/keys/<int:id>/')
def minisign_pub_key_by_id(id: int) -> bytes:
    kp = minisign_keys.get_key_pair_by_id(id)
    if kp is None:
        return flask.abort(404)
    kp = minisign_keys.get_key_pair()
    public_key = minisign.PublicKey.from_bytes(kp.pk_bytes)
    return public_key.to_base64()
