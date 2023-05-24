# coding: utf-8
"""
Status route to allow health checks.
"""

import flask


from . import frontend
from .. import db
from .. import version
from ..utils import FlaskResponseT


@frontend.route('/status/')
def status() -> FlaskResponseT:
    status_info = {
        'sampledb_version': version.__version__,
        'flask_status': True
    }
    try:
        db.session.execute(db.text('select 1')).fetchone()
        status_info['postgres_status'] = True
    except Exception:
        status_info['postgres_status'] = False
    if all(status_info.values()):
        status_code = 200
    else:
        status_code = 500
    status_info['name'] = flask.current_app.config['SERVICE_NAME']
    status_info['federation_uuid'] = flask.current_app.config['FEDERATION_UUID'] if flask.current_app.config['ENABLE_FEDERATION_DISCOVERABILITY'] else None
    return flask.jsonify(status_info), status_code, {
        'Access-Control-Allow-Origin': '*'
    }
