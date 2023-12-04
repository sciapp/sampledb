# coding: utf-8
"""

"""

import enum
import datetime
import typing

from sqlalchemy.orm import relationship, Query, Mapped

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .authentication import Authentication


@enum.unique
class HTTPMethod(enum.Enum):
    GET = 0
    POST = 1
    PUT = 2
    PATCH = 3
    DELETE = 4
    HEAD = 5
    OPTIONS = 6
    OTHER = 7

    @staticmethod
    def from_name(
            name: str
    ) -> 'HTTPMethod':
        for member in HTTPMethod:
            if member.name.lower() == name.lower():
                return member
        return HTTPMethod.OTHER


class APILogEntry(Model):
    __tablename__ = 'api_log_entries'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    api_token_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('authentications.id'), nullable=False)
    method: Mapped[HTTPMethod] = db.Column(db.Enum(HTTPMethod), nullable=False)
    route: Mapped[str] = db.Column(db.String, nullable=False)
    utc_datetime: Mapped[datetime.datetime] = db.Column(db.TIMESTAMP(timezone=True), nullable=False)
    api_token: Mapped['Authentication'] = relationship('Authentication', backref=db.backref("api_log_entries", cascade="all,delete"))

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["APILogEntry"]]

    def __init__(
            self,
            api_token_id: int,
            method: HTTPMethod,
            route: str,
            utc_datetime: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            api_token_id=api_token_id,
            method=method,
            route=route,
            utc_datetime=utc_datetime if utc_datetime is not None else datetime.datetime.now(datetime.timezone.utc),
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, api_token_id={self.api_token_id}, method={self.method}, route={self.route}, utc_datetime={self.utc_datetime})>'
