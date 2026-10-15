import typing
from http import HTTPStatus

import flask
from pydantic import BaseModel, Field

from .authentication import multi_auth
from ..utils import Resource
from ...logic import errors, users
from .utils.responses import ErrorDetailsModel, PaginatedSequence, PaginationQueryModel
from .utils.openapi import method


class UserModel(BaseModel):
    user_id: int = Field(description="the ID of the user", examples=[1])
    name: str | None = Field(description="the name of the user", examples=["Example User"])
    orcid: str | None = Field(description="the ORCID iD of the user", examples=["0000-0001-2345-6789"])
    affiliation: str | None = Field(description="the affiliation of the user", examples=["Example Institute"])
    role: str | None = Field(description="the role of the user", examples=["Researcher"])
    email: str | None = Field(None, description="the email address of the user, only set when queried by administrators", examples=["user@example.com"])
    is_hidden: bool | None = Field(None, description="whether the user is hidden from user lists, only set when queried by administrators", examples=[False])
    is_active: bool | None = Field(None, description="whether the user is active, only set when queried by administrators", examples=[True])
    is_readonly: bool | None = Field(None, description="whether the user is readonly, only set when queried by administrators", examples=[False])

    @classmethod
    def from_user(cls, user: users.User) -> typing.Self:
        return cls(
            user_id=user.id,
            name=user.name,
            orcid=user.orcid,
            affiliation=user.affiliation,
            role=user.role,
            email=user.email if flask.g.user.is_admin else None,
            is_hidden=user.is_hidden if flask.g.user.is_admin else None,
            is_active=user.is_active if flask.g.user.is_admin else None,
            is_readonly=user.is_readonly if flask.g.user.is_admin else None,
        )


class UserNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested user does not exist."


class User(Resource):
    class PathModel(BaseModel):
        user_id: int = Field(description="the ID of an existing user", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> UserModel | UserNotFoundModel:
        """
        Get a user.
        """
        try:
            user = users.get_user(user_id=path.user_id)
        except errors.UserDoesNotExistError:
            return UserNotFoundModel(
                detail=f"User #{path.user_id} does not exist.",
            )
        return UserModel.from_user(user)


class CurrentUser(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> UserModel:
        """
        Get the currently authenticated user.
        """
        return UserModel.from_user(flask.g.user)


class Users(Resource):
    class QueryModel(PaginationQueryModel):
        filter_hidden: bool | None = Field(None, description="whether to filter for only hidden or only non-hidden users", examples=[False])
        filter_active: bool | None = Field(None, description="whether to filter for only active or only non-active users", examples=[True])
        filter_readonly: bool | None = Field(None, description="whether to filter for only readonly or only non-readonly users", examples=[False])

    @multi_auth.login_required
    @method()
    def get(self, query: QueryModel) -> PaginatedSequence[UserModel]:
        """
        List all users.
        """
        filtered_users = users.get_users(
            filter_hidden=query.filter_hidden if flask.g.user.is_admin else None,
            filter_active=query.filter_active if flask.g.user.is_admin else None,
            filter_readonly=query.filter_readonly if flask.g.user.is_admin else None,
            sort_by="id",
            after_id=query.previous_id,
            limit=query.limit,
        )
        return PaginatedSequence(
            items=[
                UserModel.from_user(user)
                for user in filtered_users
            ],
            query=query,
            id_getter=lambda user: user.user_id,
        )
