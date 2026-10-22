import typing

import flask

from ..utils import FlaskResponseT


def is_api_error() -> bool:
    return flask.request.blueprint in ('api_v1', 'api_v2') or flask.request.blueprint is None and flask.request.path.startswith('/api/')


def handle_api_error(error: typing.Any) -> FlaskResponseT:
    return flask.jsonify({
        "message": getattr(error, 'description', "The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.")
    }), int(getattr(error, 'code', 500))
