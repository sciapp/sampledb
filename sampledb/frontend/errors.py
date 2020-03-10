# coding: utf-8
"""

"""

import flask

from . import frontend
from ..logic.errors import UserIsReadonlyError

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.app_errorhandler(403)
def forbidden(error):
    try:
        return flask.render_template('errors/403.html'), 403
    except Exception:
        return 'Forbidden', 403


@frontend.app_errorhandler(404)
def file_not_found(error):
    try:
        return flask.render_template('errors/404.html'), 404
    except Exception:
        return 'Not found', 404


@frontend.app_errorhandler(500)
def internal_server_error(error):
    try:
        return flask.render_template('errors/500.html'), 500
    except Exception:
        return 'Internal Server Error', 500


@frontend.errorhandler(UserIsReadonlyError)
def user_is_readonly_error(error):
    return flask.render_template('errors/user_is_readonly.html'), 403
