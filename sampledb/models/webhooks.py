# coding: utf-8
"""

"""

import enum
import typing
import datetime

from sqlalchemy.orm import Query, Mapped

from .. import db
from .utils import Model


class WebhookType(enum.Enum):
    OBJECT_LOG = 1


class Webhook(Model):
    __tablename__ = "webhooks"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type: Mapped[WebhookType] = db.Column(db.Enum(WebhookType), nullable=False)
    target_url: Mapped[str] = db.Column(db.String, nullable=False)
    name: Mapped[typing.Optional[str]] = db.Column(db.String, default=None, nullable=True)
    secret: Mapped[str] = db.Column(db.String, nullable=False)
    last_contact: Mapped[typing.Optional[datetime.datetime]] = db.Column(db.DateTime, default=None, nullable=True)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'type', 'target_url', name='_user_id_type_target_url_uc'),
    )

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Webhook"]]

    def __init__(
        self,
        user_id: int,
        type: WebhookType,
        target_url: str,
        secret: str,
        name: typing.Optional[str],
        last_contact: typing.Optional[datetime.datetime] = None
    ) -> None:
        super().__init__(
            user_id=user_id,
            type=type,
            target_url=target_url,
            name=name,
            secret=secret,
            last_contact=last_contact
        )

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id})>'
