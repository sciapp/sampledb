# coding: utf-8
"""

"""

import flask

from . import frontend

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.app_errorhandler(403)
def forbidden(error):
    return flask.render_template('403.html'), 403


@frontend.app_errorhandler(404)
def file_not_found(error):
    return flask.render_template('404.html'), 404


@frontend.app_errorhandler(500)
def internal_server_error(error):
    return flask.render_template('500.html'), 500
