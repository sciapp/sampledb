# coding: utf-8
"""

"""

import flask

from . import frontend
from ..utils import FlaskResponseT

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/')
def index() -> FlaskResponseT:
    return flask.render_template(
        'index.html'
    )
