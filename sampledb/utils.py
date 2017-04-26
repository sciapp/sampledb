# coding: utf-8
"""

"""

import base64
import binascii
import functools
import os

import flask
import flask_login

from sampledb import logic
from sampledb.logic.authentication import login
from sampledb.models import Permissions, Objects

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


def http_auth_required(func):
    func = flask_login.login_required(func)

    @functools.wraps(func)
    def wrapper(**kwargs):
        auth_header = flask.request.headers.get('Authorization', None)
        if not auth_header:
            return flask.abort(401)
        if not auth_header.startswith('Basic '):
            return flask.abort(401)
        try:
            auth_data = base64.b64decode(auth_header.replace('Basic ', '', 1), validate=True).decode('utf-8')
        except (TypeError, binascii.Error, UnicodeDecodeError):
            return flask.abort(401)
        if ':' not in auth_data:
            return flask.abort(401)
        username, password = auth_data.split(':', 1)
        user = login(username, password)
        if user is None:
            return flask.abort(401)
        flask_login.login_user(user, remember=False)
        if not flask_login.current_user.is_authenticated or not flask_login.current_user.is_active:
            return flask.abort(401)
        return func(**kwargs)
    return wrapper


def object_permissions_required(required_object_permissions: Permissions):
    def decorator(func):
        @flask_login.login_required
        @functools.wraps(func)
        def wrapper(**kwargs):
            assert 'object_id' in kwargs
            object_id = kwargs['object_id']
            if Objects.get_current_object(object_id) is None:
                return flask.abort(404)
            if not logic.permissions.object_is_public(object_id):
                user_id = flask_login.current_user.id
                user_object_permissions = logic.permissions.get_user_object_permissions(object_id=object_id, user_id=user_id)
                if required_object_permissions not in user_object_permissions:
                    # TODO: handle lack of permissions better
                    return flask.abort(403)
            return func(**kwargs)
        return wrapper
    return decorator


def load_environment_configuration(env_prefix):
    """
    Loads configuration data from environment variables with a given prefix.
    
    :return: a dict containing the configuration values
    """
    config = {
        key[len(env_prefix):]: value
        for key, value in os.environ.items()
        if key.startswith(env_prefix)
    }
    return config


def generate_secret_key(num_bits):
    """
    Generates a secure, random key for the application.
    
    :param num_bits: number of bits of random data in the secret key
    :return: the base64 encoded secret key
    """
    num_bytes = num_bits // 8
    binary_key = os.urandom(num_bytes)
    base64_key = base64.b64encode(binary_key).decode('ascii')
    return base64_key
