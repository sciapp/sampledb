import typing
import datetime

import babel
import flask
from flask_babel.speaklater import LazyString


def get_locale() -> typing.Optional[babel.Locale]:
    ...


def format_datetime(
        datetime: typing.Optional[datetime.datetime] = None,
        format: typing.Optional[str] = None,
        rebase: bool = True
) -> str:
    ...


def format_time(
        time: typing.Optional[datetime.datetime] = None,
        format: typing.Optional[str] = None,
        rebase: bool = True
) -> str:
    ...


def format_date(
        date: typing.Optional[datetime.date] = None,
        format: typing.Optional[str] = None,
        rebase: bool = True
) -> str:
    ...


def gettext(
        string: str,
        **variables: typing.Any
) -> str:
    ...


def _(
        string: str,
        **variables: typing.Any
) -> str:
    ...


def lazy_gettext(
        string: str,
        **variables: typing.Any
) -> LazyString:
    ...


def refresh() -> None:
    ...


class Babel:
    def __init__(
            self,
            app: typing.Optional[flask.Flask] = None,
            *,
            locale_selector: typing.Callable[[], str],
            timezone_selector: typing.Callable[[], typing.Optional[str]],
    ) -> None:
        ...

    def init_app(
            self,
            app: flask.Flask
    ) -> None:
        ...