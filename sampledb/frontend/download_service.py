"""

"""

import flask
from flask import request

from . import frontend
from .objects.permissions import on_unauthorized
from .. import db
from ..logic.object_permissions import Permissions
from ..logic.security_tokens import generate_token
from ..models import DownloadServiceJobFile
from ..utils import object_permissions_required


def upload_file_list(object_id: int) -> int:
    job_id = None
    file_ids = request.args.getlist('file_ids', type=int)
    for file_id in file_ids:
        ds = DownloadServiceJobFile(job_id, object_id, int(file_id))
        db.session.add(ds)
        db.session.commit()
        if job_id is None:
            job_id = ds.id
    return job_id


@frontend.route('/objects/<int:object_id>/download_service/', methods=['GET'])
@object_permissions_required(Permissions.READ, on_unauthorized=on_unauthorized)
def download_service(object_id: int):
    download_service_enabled = flask.current_app.config['DOWNLOAD_SERVICE_URL'] and flask.current_app.config['DOWNLOAD_SERVICE_SECRET']
    if not download_service_enabled:
        return flask.abort(404)

    job_id = upload_file_list(object_id)
    signature = generate_token(
        job_id,
        'download_service_zipping',
        flask.current_app.config['DOWNLOAD_SERVICE_SECRET'])
    url = '{}?signature={}'.format(
        flask.current_app.config['DOWNLOAD_SERVICE_URL'],
        signature)
    return flask.redirect(url, code=302)
