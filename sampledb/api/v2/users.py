# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask
from pydantic import BaseModel, Field

from .authentication import multi_auth
from ..utils import Resource
from ...logic import errors, users
from .utils.validation import method
from .utils.responses import NotFoundErrorModel

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class UserModel(BaseModel):
    user_id: int = Field(description="the ID of the user", examples=[1])
    name: typing.Optional[str] = Field(description="the name of the user", examples=["Example User"])
    orcid: typing.Optional[str] = Field(description="the ORCID iD of the user", examples=["0000-0001-2345-6789"])
    affiliation: typing.Optional[str] = Field(description="the affiliation of the user", examples=["Example Institute"])
    role: typing.Optional[str] = Field(description="the role of the user", examples=["Researcher"])
    email: typing.Optional[str] = Field(None, description="the email address of the user, only set when queried by administrators", examples=["user@example.com"])
    is_hidden: typing.Optional[bool] = Field(None, description="whether the user is hidden from user lists, only set when queried by administrators", examples=[False])
    is_active: typing.Optional[bool] = Field(None, description="whether the user is active, only set when queried by administrators", examples=[True])
    is_readonly: typing.Optional[bool] = Field(None, description="whether the user is readonly, only set when queried by administrators", examples=[False])

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


class User(Resource):
    class PathModel(BaseModel):
        user_id: int = Field(description="the ID of an existing user", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> UserModel | NotFoundErrorModel:
        """
        Get a user.
        """
        try:
            user = users.get_user(user_id=path.user_id)
        except errors.UserDoesNotExistError:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"user {path.user_id} does not exist",
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
    class QueryModel(BaseModel):
        filter_hidden: typing.Optional[bool] = Field(None, description="whether to filter for only hidden or only non-hidden users", examples=[False])
        filter_active: typing.Optional[bool] = Field(None, description="whether to filter for only active or only non-active users", examples=[True])
        filter_readonly: typing.Optional[bool] = Field(None, description="whether to filter for only readonly or only non-readonly users", examples=[False])

    @multi_auth.login_required
    @method()
    def get(self, query: QueryModel) -> typing.List[UserModel]:
        """
        List all users.
        """
        filtered_users = users.get_users()
        if flask.g.user.is_admin:
            for filter_value, filter_attr in [
                (query.filter_hidden, 'is_hidden'),
                (query.filter_active, 'is_active'),
                (query.filter_readonly, 'is_readonly'),
            ]:
                if filter_value is None:
                    continue
                filtered_users = [
                    user
                    for user in filtered_users
                    if getattr(user, filter_attr) == filter_value
                ]
        return [
            UserModel.from_user(user)
            for user in filtered_users
        ]
