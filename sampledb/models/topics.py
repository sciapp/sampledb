# coding: utf-8
"""

"""

import typing

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, Query, Mapped

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .actions import Action
    from .instruments import Instrument
    from .locations import Location


class Topic(Model):
    __tablename__ = 'topics'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[typing.Dict[str, str]] = db.Column(postgresql.JSON, nullable=False)
    description: Mapped[typing.Dict[str, str]] = db.Column(postgresql.JSON, nullable=False)
    show_on_frontpage: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    show_in_navbar: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    order_index: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True)
    actions: Mapped[typing.List['Action']] = relationship('Action', secondary='action_topics', back_populates='topics')
    instruments: Mapped[typing.List['Instrument']] = relationship('Instrument', secondary='instrument_topics', back_populates='topics')
    short_description: Mapped[typing.Dict[str, str]] = db.Column(postgresql.JSON, nullable=False)
    description_is_markdown: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    short_description_is_markdown: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    locations: Mapped[typing.List['Location']] = relationship('Location', secondary='location_topics', back_populates='topics')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Topic"]]

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id!r})>'
