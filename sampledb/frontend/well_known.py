# coding: utf-8
"""

"""
import flask
import minisign
from flask import url_for

from ..logic import minisign_keys
from . import frontend
from ..utils import FlaskResponseT


@frontend.route('/.well-known/keys.json')
def key_list_json() -> FlaskResponseT:
    key_pairs = minisign_keys.get_key_pairs()
    res = [
        {
            "@context": "https://schema.org",
            "@type": "MediaObject",
            "contentUrl": url_for("frontend.minisign_pub_key_by_id", keypair_id=kp.id, _external=True),
            "name": f"ed25519_pub_{str(kp.id)}",
            "encodingFormat": "application/x-minisign-key",
            "description": "Signing key for exported archives",
            "dateCreated": kp.utc_datetime_created
        }
        for kp in key_pairs
    ]
    return flask.jsonify(res)


@frontend.route('/.well-known/keys/<int:keypair_id>')
def minisign_pub_key_by_id(keypair_id: int) -> FlaskResponseT:
    kp = minisign_keys.get_key_pair_by_id(keypair_id)
    if kp is None:
        return flask.abort(404)
    public_key = minisign.PublicKey.from_bytes(kp.pk_bytes)
    key_bytes: bytes = public_key.to_base64()
    return key_bytes.decode('utf-8')
