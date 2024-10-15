# coding: utf-8
"""

"""

import flask
import minisign

from ..logic import minisign_keys
from . import frontend
from ..utils import FlaskResponseT


@frontend.route('/.well-known/keys.json')
def key_list_json() -> FlaskResponseT:
    key_pairs = minisign_keys.get_key_pairs()
    # TODO replace hardcoded URL to localhost
    res = [
        {
            "@context": "https://schema.org",
            "@type": "MediaObject",
            # "contentUrl": f"http://localhost:8000/.well-known/keys/{str(kp.id)}",
            "contentUrl": f"http://{flask.current_app.config['SERVER_NAME']}/.well-known/keys/{str(kp.id)}",
            "name": f"ed25519_pub_{str(kp.id)}",
            "encodingFormat": "application/x-minisign-key",
            "description": "Signing key for exported archives",
            "dateCreated": kp.utc_datetime_created
        }
        for kp in key_pairs
    ]
    return flask.jsonify(res)


@frontend.route('/.well-known/keys/<int:keypair_id>')
def minisign_pub_key_by_id(keypair_id: int) -> bytes:
    kp = minisign_keys.get_key_pair_by_id(keypair_id)
    if kp is None:
        return flask.abort(404)
    public_key = minisign.PublicKey.from_bytes(kp.pk_bytes)
    return public_key.to_base64()  # type: ignore
