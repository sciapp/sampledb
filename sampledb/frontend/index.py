# coding: utf-8
"""

"""

import flask

from . import frontend

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/')
def index():
    return flask.render_template('index.html')
