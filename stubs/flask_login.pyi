"""
Minimalist type hint stub file for Flask-Login to enable proper type checking with mypy.
"""
import datetime
import typing

import flask

import sampledb

current_user: sampledb.logic.users.User

# TODO: require this to be a callable returning a FlaskResponseT
FlaskRouteT = typing.TypeVar('FlaskRouteT')

# class FlaskRouteT(typing.Protocol):
#     def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> sampledb.utils.FlaskResponseT: ...


def login_required(
        f: FlaskRouteT
) -> FlaskRouteT:
    ...

def login_user(
        user: sampledb.logic.users.User,
        remember: bool = False,
        duration: typing.Optional[datetime.timedelta] = None,
        force: bool = False,
        fresh: bool = True
) -> bool:
    ...

def logout_user() -> bool:
    ...

def confirm_login() -> None:
    ...

def login_fresh() -> bool:
    ...


class UserMixin:
    @property
    def is_active(self) -> bool:
        ...

    @property
    def is_authenticated(self) -> bool:
        ...

    @property
    def is_anonymous(self) -> bool:
        ...

    def get_id(self) -> str:
        ...


class AnonymousUserMixin:
    ...


class LoginManager:
    def __init__(
            self,
            app: typing.Optional[flask.Flask] = None,
            add_context_processor: bool =True
        ) -> None:
            self.anonymous_user: typing.Type[typing.Any] = AnonymousUserMixin
            self.login_view: typing.Optional[str] = None
            self.session_protection: str = "basic"

    def init_app(
            self,
            app: typing.Optional[flask.Flask] = None,
            add_context_processor: bool =True
    ) -> None:
        ...

    UserLoaderT = typing.TypeVar('UserLoaderT')

    def user_loader(
            self,
            callback: UserLoaderT
    ) -> UserLoaderT:
        ...