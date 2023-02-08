# coding: utf-8
"""

"""

import os

import flask

from . import frontend
from ..utils import FlaskResponseT

STATIC_IMAGE_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'static', 'sampledb', 'img')


@frontend.route('/favicon.ico')
def favicon() -> FlaskResponseT:
    return flask.send_from_directory(
        STATIC_IMAGE_DIRECTORY,
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@frontend.route('/apple-touch-icon.png')
def apple_touch_icon() -> FlaskResponseT:
    return flask.send_from_directory(
        STATIC_IMAGE_DIRECTORY,
        'apple-touch-icon.png',
        mimetype='image/png'
    )
