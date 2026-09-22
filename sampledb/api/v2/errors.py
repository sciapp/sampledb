import typing
from functools import cached_property
from http import HTTPStatus

import flask
from pydantic import BaseModel, Field
from werkzeug.exceptions import HTTPException

from .authentication import http_basic_auth, http_api_token_or_access_token_auth, http_api_token_or_refresh_token_auth, multi_auth
from .utils.responses import ErrorDetailsModel
from .utils.openapi import method, PathValidationFailedModel
from ..utils import Resource
from ...utils import FlaskResponseT
from ..errors import handle_api_error


@http_basic_auth.error_handler
@http_api_token_or_access_token_auth.error_handler
@http_api_token_or_refresh_token_auth.error_handler
def auth_error(status: int) -> FlaskResponseT:
    try:
        flask.abort(status)
    except HTTPException as e:
        return handle_api_error(e)
    else:
        return handle_api_error(None)


class ErrorNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested error does not exist."


class ErrorTypeModel(BaseModel):
    name: str = Field(description="the name of the error type.", examples=["PathValidationFailed"])
    status: int = Field(description="the HTTP status code of the error type.", examples=[HTTPStatus.BAD_REQUEST])
    title: str = Field(description="the title of the error type.", examples=[PathValidationFailedModel.TITLE])
    href: str = Field(description="the URL of the error type.", examples=['http://example.org/api/v2/errors/PathValidationFailed'])


class Error(Resource):
    @cached_property
    def _error_models_map(self) -> dict[str, type[ErrorDetailsModel]]:
        return {
            subclass.__name__.removesuffix('Model'): subclass
            for subclass in ErrorDetailsModel.__subclasses__()
        }

    class PathModel(BaseModel):
        error_name: str = Field(description="the name of the error type.", examples=["PathValidationFailed"])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ErrorTypeModel | ErrorNotFoundModel:
        """
        Get an error type.
        """
        if path.error_name not in self._error_models_map:
            return ErrorNotFoundModel(
                detail=f"The error '{path.error_name}' does not exist."
            )
        error_model_class = self._error_models_map[path.error_name]
        return ErrorTypeModel(
            name=path.error_name,
            status=error_model_class.STATUS,
            title=error_model_class.TITLE,
            href=flask.url_for('.error', _external=True, error_name=path.error_name),
        )
