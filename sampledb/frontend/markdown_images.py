# coding: utf-8
"""
There are several Markdown editors built into the SampleDB frontend, which
need to be able to upload images. This module allows uploading images which
are then assigned a random file name and can be used in the Markdown editors
using that name.
"""

import base64
import os

import flask
import flask_login

from . import frontend
from ..logic import markdown_images

_temporary_markdown_images = {}

IMAGE_FORMATS = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
}


@frontend.route('/markdown_images/<file_name>')
@flask_login.login_required
def markdown_image(file_name):
    image_data = markdown_images.get_markdown_image(file_name, flask_login.current_user.id)
    if image_data is None:
        return flask.abort(404)
    file_extension = os.path.splitext(file_name)[1]
    return flask.Response(
        image_data,
        mimetype=IMAGE_FORMATS.get(file_extension, 'application/octet-stream')
    )


@frontend.route('/markdown_images/', methods=['POST'])
@flask_login.login_required
def upload_markdown_image():
    image_data_url = flask.request.get_data()
    for image_file_extension, image_content_type in IMAGE_FORMATS.items():
        image_data_url_prefix = b'data:' + image_content_type.encode('ascii') + b';base64,'
        if image_data_url.startswith(image_data_url_prefix):
            image_base64_data = image_data_url[len(image_data_url_prefix):]
            break
    else:
        return flask.abort(400)
    try:
        image_data = base64.b64decode(image_base64_data)
    except Exception:
        return flask.abort(400)
    file_name = markdown_images.store_temporary_markdown_image(image_data, image_file_extension, flask_login.current_user.id)
    return flask.url_for('.markdown_image', file_name=file_name)
