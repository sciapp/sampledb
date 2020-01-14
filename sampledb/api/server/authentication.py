# coding: utf-8
"""
Authentication functions for the iffSamples RESTful API.
"""

import flask

from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth

from sampledb.logic.authentication import login, login_via_api_token
from sampledb.logic.object_permissions import Permissions
from sampledb.utils import object_permissions_required as object_permissions_required_generic

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

http_basic_auth = HTTPBasicAuth()
http_token_auth = HTTPTokenAuth(scheme='Bearer')
multi_auth = MultiAuth(http_basic_auth, http_token_auth)


@http_token_auth.verify_token
def verify_token(api_token):
    if not api_token:
        return None
    flask.g.user = login_via_api_token(api_token)
    return flask.g.user


@http_basic_auth.verify_password
def verify_password(username, password):
    if not username:
        return None
    flask.g.user = login(username, password)
    return flask.g.user


def object_permissions_required(permissions: Permissions):
    """
    Only allow access to a route it the user has the required permissions.

    Wrapper around the more generic sampledb.utils.object_permissions_required
    for use with the http_basic_auth object from this module.

    :param permissions: the required object permissions
    """
    return object_permissions_required_generic(permissions, multi_auth, lambda: flask.g.user.id)
