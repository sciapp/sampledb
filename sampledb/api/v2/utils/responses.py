import base64
import binascii
import inspect
import typing
from collections.abc import Sequence, Callable
from http import HTTPStatus
from functools import cached_property

import flask
import werkzeug
from pydantic import BaseModel, TypeAdapter, Field, field_validator, HttpUrl
from pydantic_core import PydanticCustomError

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


class PaginationQueryModel(BaseModel):
    limit: int | None = Field(None, description='the maximum number of items to return, or null to return all items', examples=[10], gt=0, lt=int(1e15))
    cursor: str | None = Field(None, description='an opaque cursor used for pagination', examples=["MQ=="])

    @cached_property
    def previous_id(self) -> int | None:
        if self.cursor is None:
            return None
        else:
            return int(base64.urlsafe_b64decode(self.cursor).decode('utf-8'))

    @field_validator('cursor', mode='after')
    @classmethod
    def validate_cursor(cls, value: str | None) -> str | None:
        if not PaginationQueryModel.is_valid_cursor(value):
            raise PydanticCustomError("invalid_pagination_cursor", "Input is not a valid pagination cursor")
        return value

    @staticmethod
    def is_valid_cursor(cursor: str | None) -> bool:
        if cursor is None:
            return True
        try:
            decoded_cursor = base64.urlsafe_b64decode(cursor).decode('utf-8')
        except binascii.Error:
            return False
        except UnicodeEncodeError:
            return False
        try:
            int_cursor = int(decoded_cursor)
        except ValueError:
            return False
        if not 0 <= int_cursor < 1e15:
            return False
        return True

    @staticmethod
    def build_cursor(id: int) -> str:
        """
        Build an opaque cursor containing an ID.

        :param id: the ID to create the cursor for

        Currently, this is simply urlsafe base64 of the IDs string
        representation encoded as utf8 (or ASCII, due to the character set
        used by (urlsafe) base64). However, this could change in the future.
        """
        return base64.urlsafe_b64encode(str(id).encode('utf8')).decode('utf8')


T_co = typing.TypeVar('T_co', bound=BaseModel, covariant=True)


class PaginatedSequence(typing.Generic[T_co]):
    def __init__(
            self,
            items: Sequence[T_co],
            id_getter: Callable[[T_co], int],
            query: PaginationQueryModel,
            path: BaseModel | None = None,
    ) -> None:
        assert query.limit is None or len(items) <= query.limit
        self.items: Sequence[T_co] = items
        self._endpoint = flask.request.endpoint
        self._limit = query.limit
        self._self_cursor = query.cursor
        self._next_cursor = None
        if query.limit is not None and len(items) == query.limit:
            self._next_cursor = PaginationQueryModel.build_cursor(id_getter(items[-1]))
        extra_url_for_args = query.model_dump()
        if path is not None:
            extra_url_for_args.update(path.model_dump())
        del extra_url_for_args["limit"]
        del extra_url_for_args["cursor"]
        self._extra_url_for_args = extra_url_for_args if extra_url_for_args is not None else {}

    @classmethod
    def apply_pagination(
            cls,
            items: list[T_co],
            id_getter: Callable[[T_co], int],
            query: PaginationQueryModel,
            path: BaseModel | None = None,
    ) -> typing.Self:
        """
        Return a PaginatedSequence based on the pagination query parameters
        and the full set of items. As this uses all items, using this only
        makes sense when there is no need for an in-database implementation
        of pagination, or when that still needs to be done.

        :param items: the items to paginate
        :param id_getter: a callable to get the item ID to use for sorting and filtering
        :param query: the pagination query parameters, and any extra query parameters to include in links
        :param path: the URL path parameters to use for link generation
        """
        if query.previous_id is not None:
            items = [
                item
                for item in items
                if id_getter(item) > query.previous_id
            ]
        items.sort(key=id_getter)
        if query.limit is not None:
            items = items[:query.limit]
        return cls(
            items=items,
            id_getter=id_getter,
            query=query,
            path=path,
        )

    @property
    def link_header(self) -> str:
        if self._endpoint is None:
            return ""
        links = [
            "<" + flask.url_for(self._endpoint, _external=True, limit=self._limit, **self._extra_url_for_args) + ">; rel=\"start\""
        ]
        if self._self_cursor is None:
            links.append(
                "<" + flask.url_for(self._endpoint, _external=True, limit=self._limit, **self._extra_url_for_args) + ">; rel=\"self\""
            )
        else:
            links.append(
                "<" + flask.url_for(self._endpoint, _external=True, limit=self._limit, cursor=self._self_cursor, **self._extra_url_for_args) + ">; rel=\"self\""
            )
        if self._next_cursor is not None:
            links.append(
                "<" + flask.url_for(self._endpoint, _external=True, limit=self._limit, cursor=self._next_cursor, **self._extra_url_for_args) + ">; rel=\"next\""
            )
        return ", ".join(links)


type ResourceMethodResult = BaseModel | PaginatedSequence[BaseModel] | ReturnValue[typing.Any] | ErrorDetailsModel | RedirectResponseModel | NoContentModel


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
    if isinstance(result, PaginatedSequence):
        return make_json_response(
            [
                item.model_dump(by_alias=True) if isinstance(item, BaseModel) else item
                for item in result.items
            ],
            status=default_status_code,
            headers={
                "Link": result.link_header
            }
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
