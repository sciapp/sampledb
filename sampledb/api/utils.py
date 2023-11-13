from functools import wraps
import json
import traceback
import typing

import cherrypy
import flask
from flask.views import MethodView
import werkzeug
import werkzeug.exceptions


ResponseContent = typing.Optional[typing.Union[typing.Dict[str, typing.Any], typing.Dict[int, typing.Any], typing.List[typing.Any], str, bool, int]]
ResponseData = typing.Union[werkzeug.Response, ResponseContent, typing.Tuple[ResponseContent], typing.Tuple[ResponseContent, int], typing.Tuple[ResponseContent, int, typing.Dict[str, str]]]


class Resource(MethodView):
    @classmethod
    def as_view(cls, name: typing.Any, *class_args: typing.Any, **class_kwargs: typing.Any) -> typing.Any:
        return super(Resource, _resource_decorator(cls)).as_view(name, *class_args, **class_kwargs)


def _resource_decorator(cls: typing.Type[Resource]) -> typing.Type[Resource]:
    for method in ['get', 'head', 'post', 'put', 'delete']:
        if hasattr(cls, method) and callable(getattr(cls, method)):
            setattr(cls, method, _resource_method_decorator(getattr(cls, method)))
    return cls


def _resource_method_decorator(f: typing.Callable[[typing.Any], ResponseData]) -> typing.Callable[[typing.Any], typing.Any]:
    @wraps(f)
    def decorator(*args: typing.Any, **kwargs: typing.Any) -> werkzeug.Response:
        flask.request.on_json_loading_failed = _on_json_loading_failed_replacement  # type: ignore
        try:
            response_data = f(*args, **kwargs)
            if isinstance(response_data, werkzeug.Response):
                response = response_data
            else:
                message: ResponseContent
                status = 200
                headers: typing.Dict[str, str] = {}
                if isinstance(response_data, tuple):
                    if len(response_data) == 1:
                        message, = response_data
                    elif len(response_data) == 2:
                        message, status = response_data
                    elif len(response_data) == 3:
                        message, status, headers = response_data
                    else:
                        message = None
                else:
                    message = response_data
                if message is None:
                    response = flask.current_app.response_class(
                        message,
                        status=status,
                        headers=headers
                    )
                else:
                    response = _make_json_response(
                        message,
                        status=status,
                        headers=headers
                    )
        except werkzeug.exceptions.HTTPException:
            raise
        except Exception as e:
            cherrypy.log(''.join(traceback.format_exception(e)))
            response = _make_json_response(
                obj={'message': 'Internal Server Error'},
                status=500
            )
        return response
    return decorator


def _make_json_response(
        obj: typing.Any,
        status: int = 200,
        headers: typing.Optional[typing.Dict[str, typing.Any]] = None
) -> werkzeug.Response:
    if headers is None:
        headers = {}

    indent = None
    separators = (",", ":")

    compact_notation = getattr(flask.current_app.json, 'compact', None)
    if compact_notation is False or (compact_notation is None and flask.current_app.debug):
        indent = 2
        separators = (", ", ": ")

    return typing.cast(werkzeug.Response, flask.current_app.response_class(
        response=f"{json.dumps(obj=obj, indent=indent, separators=separators)}\n",
        mimetype=getattr(flask.current_app.json, 'mimetype', 'application/json'),
        status=status,
        headers=headers
    ))


def _on_json_loading_failed_replacement(_e: Exception) -> typing.NoReturn:
    flask.abort(_make_json_response(
        obj={'message': 'Failed to decode JSON object'},
        status=400
    ))
