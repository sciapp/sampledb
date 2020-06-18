# coding: utf-8
"""
Status route to allow health checks.
"""

import flask


from . import frontend
from .. import db
from .. import version


@frontend.route('/status/')
def status():
    status_info = {
        'sampledb_version': version.__version__,
        'flask_status': True
    }
    try:
        db.engine.execute('select 1').fetchone()
        status_info['postgres_status'] = True
    except Exception:
        status_info['postgres_status'] = False
    if all(status_info.values()):
        status_code = 200
    else:
        status_code = 500
    return flask.jsonify(status_info), status_code
