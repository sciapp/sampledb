import inspect
import typing
from collections.abc import Sequence
from http import HTTPStatus

import flask
import werkzeug
from pydantic import BaseModel, TypeAdapter, Field, field_validator, HttpUrl

from ...utils import make_json_response
from .validation import generate_example


class NoContentModel(BaseModel):
    STATUS_CODE: typing.ClassVar[int] = HTTPStatus.NO_CONTENT


class RedirectResponseModel(BaseModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.FOUND

    location: str = Field(description="the URL to redirect to", examples=["https://example.com"])
    status: int = Field(
        description="the HTTP status code of the redirect",
        examples=[302],
        default_factory=lambda: RedirectResponseModel.STATUS,
        validate_default=True
    )

    @field_validator('status', mode='before')
    @classmethod
    def set_status(cls, value: int) -> int:
        assert value in (RedirectResponseModel.STATUS, cls.STATUS)
        return cls.STATUS


class CreatedResponseModel(RedirectResponseModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.CREATED


class FoundResponseModel(RedirectResponseModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.FOUND


class PathErrorDetailModel(BaseModel):
    detail: str = Field(
        description="a detailed description for a specific error related to a path parameter",
        examples=["Field required."]
    )
    path_parameter: str = Field(
        description="the name of the path parameter that is the source of error",
        examples=["id"],
    )
    input: typing.Any = Field(
        description="the input that caused validation to fail",
        examples=["invalid"]
    )


class QueryErrorDetailModel(BaseModel):
    detail: str = Field(
        description="a detailed description for a specific error related to a query parameter",
        examples=["Field required."]
    )
    query_parameter: str = Field(
        description="the name of the query parameter that is the source of error",
        examples=["q"],
    )
    input: typing.Any = Field(
        description="the input that caused validation to fail",
        examples=["invalid"]
    )


class RequestBodyErrorDetailModel(BaseModel):
    detail: str = Field(
        description="a detailed description for a specific error related to the request body",
        examples=["Field required."]
    )
    json_pointer: str = Field(
        description="the JSON Pointer to a specific request body property that is the source of error",
        examples=["/user_id"],
    )
    input: typing.Any = Field(
        description="the input that caused validation to fail",
        examples=["invalid"]
    )


class ErrorDetailsModel(BaseModel):
    """
    Error Details as per RFC 9457

    Subclasses should define their own STATUS and TITLE class variables, which
    will be used as defaults for status and title. type will be constructed
    from the class name, with the suffix "Model" removed.
    """
    STATUS: typing.ClassVar[int] = 0
    TITLE: typing.ClassVar[str] = ""

    type: str = Field(
        description="the type of the error",
        examples=["http://example.com/api/v2/errors/ErrorDetails"],
        default_factory=lambda: "",
        validate_default=True
    )
    title: str = Field(
        description="the title of the error",
        examples=["The operation failed for demo purposes."],
        default_factory=lambda: ErrorDetailsModel.TITLE,
        validate_default=True
    )
    status: int = Field(
        description="the HTTP status code of the error",
        examples=[400],
        default_factory=lambda: ErrorDetailsModel.STATUS,
        validate_default=True
    )
    detail: str = Field(
        description="a detailed description of the error",
        examples=["Operation #1 failed to demonstrate the ErrorDetailsModel."]
    )
    errors: Sequence[PathErrorDetailModel | QueryErrorDetailModel | RequestBodyErrorDetailModel] = Field(
        description="an array of specific errors related to a path parameter, query parameter or the request body",
        examples=[[generate_example(PathErrorDetailModel)]],
        default=[]
    )

    @field_validator('type', mode='before')
    @classmethod
    def set_type(cls, value: str) -> str:
        assert cls.__name__.endswith('Model')
        type_name = cls.__name__.removesuffix('Model')
        type_url = flask.url_for('.error', error_name=type_name, _external=True)
        assert value in ("", type_name, type_url)
        assert type_url == str(TypeAdapter(HttpUrl).validate_python(type_url))
        return type_url

    @field_validator('title', mode='before')
    @classmethod
    def set_title(cls, value: str) -> str:
        assert value in (ErrorDetailsModel.TITLE, cls.TITLE)
        return cls.TITLE

    @field_validator('status', mode='before')
    @classmethod
    def set_status(cls, value: int) -> int:
        assert value in (ErrorDetailsModel.STATUS, cls.STATUS)
        return cls.STATUS


class ReturnValue[T]:
    def __init__(self, value: T) -> None:
        self.value: T = value


type ResourceMethodResult = BaseModel | Sequence[BaseModel] | ReturnValue[typing.Any] | ErrorDetailsModel | RedirectResponseModel | NoContentModel


def make_response(
        result: ResourceMethodResult,
        default_status_code: int,
        return_type_hint: typing.Any
) -> werkzeug.Response:
    if isinstance(result, ErrorDetailsModel):
        return make_json_response(
            result.model_dump(by_alias=True),
            status=result.STATUS,
            mimetype='application/problem+json',
        )
    if isinstance(result, RedirectResponseModel):
        return make_json_response(
            result.model_dump(by_alias=True),
            status=result.STATUS,
            headers={
                "Location": result.location
            }
        )
    if isinstance(result, NoContentModel):
        return flask.current_app.response_class(
            b"",
            status=result.STATUS_CODE
        )
    if isinstance(result, list):
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
    if typing.get_origin(return_type_hint) is not typing.Union:  # pylint: disable=consider-alternative-union-syntax
        assert typing.get_origin(return_type_hint) is ReturnValue
        return typing.get_args(return_type_hint)[0]
    return_type_hint_options = set(typing.get_args(return_type_hint))
    return_value_return_type_hint_options = {
        return_type_hint_option
        for return_type_hint_option in return_type_hint_options
        if typing.get_origin(return_type_hint_option) is ReturnValue
    }
    assert all(
        inspect.isclass(return_type_hint_option) and issubclass(return_type_hint_option, (BaseModel, ErrorDetailsModel, NoContentModel, RedirectResponseModel)) or
        typing.get_origin(return_type_hint_option) is list and inspect.isclass(typing.get_args(return_type_hint_option)[0]) and issubclass(typing.get_args(return_type_hint_option)[0], BaseModel)
        for return_type_hint_option in (
            return_type_hint_options - return_value_return_type_hint_options
        )
    ), "API routes should only return instances of Pydantic models, lists of those instances or instances of ReturnValue"
    assert len(return_value_return_type_hint_options) == 1, "API routes should specify at most one ReturnValue type as part of their return value"
    return_value = list(return_value_return_type_hint_options)[0]
    return typing.get_args(return_value)[0]
