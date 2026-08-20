import http
import inspect
import typing
from http import HTTPStatus

import flask
import werkzeug
from pydantic import BaseModel, TypeAdapter, Field

from ...utils import make_json_response


class NoContentModel(BaseModel):
    STATUS_CODE: typing.ClassVar[int] = HTTPStatus.NO_CONTENT


class RedirectResponseModel(BaseModel):
    STATUS_CODE: typing.ClassVar[int]

    location: str = Field(description="the URL to redirect to", examples=["https://example.com"])


class CreatedResponseModel(RedirectResponseModel):
    STATUS_CODE: typing.ClassVar[int] = HTTPStatus.CREATED


class FoundResponseModel(RedirectResponseModel):
    STATUS_CODE: typing.ClassVar[int] = HTTPStatus.FOUND


class ErrorModel(BaseModel):
    STATUS_CODE: typing.ClassVar[int]

    error: str = Field(description="the HTTP error phrase", examples=[http.HTTPStatus.BAD_REQUEST.phrase])
    message: str = Field(description="the error message", examples=["Unable to perform operation"])


class BadRequestErrorModel(ErrorModel):
    STATUS_CODE: typing.ClassVar[int] = HTTPStatus.BAD_REQUEST
    error_details: typing.Annotated[
        dict[str, typing.Any] | None,
        Field(
            description="the details of the error",
            examples=[
                {
                    "input": None,
                    "msg": "Input should be an object"
                }
            ]
        )
    ] = None


class ForbiddenErrorModel(ErrorModel):
    STATUS_CODE: typing.ClassVar[int] = HTTPStatus.FORBIDDEN


class NotFoundErrorModel(ErrorModel):
    STATUS_CODE: typing.ClassVar[int] = HTTPStatus.NOT_FOUND


class ReturnValue[T]:
    def __init__(self, value: T) -> None:
        self.value: T = value


ResultUnion = typing.Union[BaseModel, typing.Sequence[BaseModel], ReturnValue[typing.Any], ErrorModel, RedirectResponseModel, NoContentModel]


def make_response(
        result: ResultUnion,
        default_status_code: int,
        return_type_hint: typing.Any
) -> werkzeug.Response:
    if isinstance(result, ErrorModel):
        return make_json_response(
            result.model_dump(by_alias=True),
            status=result.STATUS_CODE,
        )
    if isinstance(result, RedirectResponseModel):
        return flask.current_app.response_class(
            b"",
            status=result.STATUS_CODE,
            headers={
                "Location": result.location
            }
        )
    if isinstance(result, NoContentModel):
        return flask.current_app.response_class(
            b"",
            status=result.STATUS_CODE
        )
    if isinstance(result, typing.Sequence):
        return make_json_response(
            [
                item.model_dump(by_alias=True) if isinstance(item, BaseModel) else item
                for item in result
            ],
            status=default_status_code
        )
    if isinstance(result, BaseModel):
        return make_json_response(
            result.model_dump(by_alias=True),
            status=default_status_code
        )
    if isinstance(result, ReturnValue):
        return_value_type = _get_return_value_type(return_type_hint)
        return flask.current_app.response_class(
            TypeAdapter(return_value_type).dump_json(result.value, by_alias=True),
            mimetype=getattr(flask.current_app.json, 'mimetype', 'application/json'),
            status=default_status_code,
        )
    assert False


def _get_return_value_type(
        return_type_hint: typing.Any
) -> typing.Any:
    if typing.get_origin(return_type_hint) is not typing.Union:
        assert typing.get_origin(return_type_hint) is ReturnValue
        return typing.get_args(return_type_hint)[0]
    return_type_hint_options = set(typing.get_args(return_type_hint))
    return_value_return_type_hint_options = {
        return_type_hint_option
        for return_type_hint_option in return_type_hint_options
        if typing.get_origin(return_type_hint_option) is ReturnValue
    }
    assert all(
        inspect.isclass(return_type_hint_option) and issubclass(return_type_hint_option, (BaseModel, ErrorModel, NoContentModel, RedirectResponseModel)) or
        typing.get_origin(return_type_hint_option) is typing.List and inspect.isclass(typing.get_args(return_type_hint_option)[0]) and issubclass(typing.get_args(return_type_hint_option)[0], BaseModel)
        for return_type_hint_option in (
            return_type_hint_options - return_value_return_type_hint_options
        )
    ), "API routes should only return instances of Pydantic models, lists of those instances or instances of ReturnValue"
    assert len(return_value_return_type_hint_options) == 1, "API routes should specify at most one ReturnValue type as part of their return value"
    return_value = list(return_value_return_type_hint_options)[0]
    return typing.get_args(return_value)[0]
