# coding: utf-8
"""

"""

import binascii
import base64
import functools
import flask
import flask_login

from . import login_manager
from .authentication.logic import login

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def admin_required(func):
    @flask_login.login_required
    @functools.wraps(func)
    def wrapper(**kwargs):
        user = flask_login.current_user
        if not user.is_admin:
            return flask.abort(403)
        return func(**kwargs)
    return wrapper


@login_manager.request_loader
def basic_auth_loader(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header.startswith('Basic '):
        return None
    try:
        auth_data = base64.b64decode(auth_header.replace('Basic ', '', 1), validate=True).decode('utf-8')
    except (TypeError, binascii.Error, UnicodeDecodeError):
        return None
    if ':' not in auth_data:
        return None
    username, password = auth_data.split(':', 1)
    # Prevent cookies?
    if login(username, password):
        return flask_login.current_user
    return None
