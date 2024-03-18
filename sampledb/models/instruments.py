# coding: utf-8
"""

"""

import typing

from sqlalchemy.orm import relationship, Mapped, Query

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .components import Component
    from .locations import Location
    from .instrument_translation import InstrumentTranslation
    from .users import User
    from .topics import Topic

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

instrument_user_association_table = db.Table(
    'association',
    db.metadata,
    db.Column('instrument_id', db.Integer, db.ForeignKey('instruments.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
)

topic_instrument_association_table = db.Table(
    'instrument_topics',
    db.metadata,
    db.Column('instrument_id', db.Integer, db.ForeignKey('instruments.id')),
    db.Column('topic_id', db.Integer, db.ForeignKey('topics.id'))
)


class Instrument(Model):
    __tablename__ = 'instruments'
    __table_args__ = (
        db.UniqueConstraint('fed_id', 'component_id', name='instruments_fed_id_component_id_key'),
    )

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    responsible_users: Mapped[typing.List['User']] = relationship("User", secondary=instrument_user_association_table, order_by="User.name", lazy='selectin')
    users_can_create_log_entries: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    users_can_view_log_entries: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    create_log_entry_default: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    is_hidden: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    notes_is_markdown: Mapped[typing.Optional[bool]] = db.Column(db.Boolean, nullable=True, default=False)
    description_is_markdown: Mapped[typing.Optional[bool]] = db.Column(db.Boolean, nullable=True, default=False)
    short_description_is_markdown: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False)
    fed_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, nullable=True)
    component_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component: Mapped[typing.Optional['Component']] = relationship('Component')
    translations: Mapped[typing.List['InstrumentTranslation']] = relationship('InstrumentTranslation', lazy='selectin')
    location_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    location: Mapped[typing.Optional['Location']] = relationship('Location')
    object_id: Mapped[typing.Optional[int]] = db.Column(db.Integer, db.ForeignKey('objects_current.object_id'), nullable=True)
    show_linked_object_data: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    topics: Mapped[typing.List['Topic']] = relationship('Topic', secondary=topic_instrument_association_table, back_populates='instruments')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Instrument"]]

    def __init__(
            self,
            description_is_markdown: bool = False,
            short_description_is_markdown: bool = False,
            notes_is_markdown: bool = False,
            users_can_create_log_entries: bool = False,
            users_can_view_log_entries: bool = False,
            create_log_entry_default: bool = False,
            is_hidden: bool = False,
            fed_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None,
            show_linked_object_data: bool = True
    ) -> None:
        super().__init__(
            description_is_markdown=description_is_markdown,
            short_description_is_markdown=short_description_is_markdown,
            notes_is_markdown=notes_is_markdown,
            users_can_create_log_entries=users_can_create_log_entries,
            users_can_view_log_entries=users_can_view_log_entries,
            create_log_entry_default=create_log_entry_default,
            is_hidden=is_hidden,
            fed_id=fed_id,
            component_id=component_id,
            show_linked_object_data=show_linked_object_data,
        )

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, Instrument):
            return bool(
                self.id == other.id and
                self.description_is_markdown == other.description_is_markdown and
                self.short_description_is_markdown == other.short_description_is_markdown and
                self.notes_is_markdown == other.notes_is_markdown and
                self.users_can_create_log_entries == other.users_can_create_log_entries and
                self.users_can_view_log_entries == other.users_can_view_log_entries and
                self.create_log_entry_default == other.create_log_entry_default and
                self.is_hidden == other.is_hidden and
                self.responsible_users == other.responsible_users and
                self.fed_id == other.fed_id and
                self.component_id == other.component_id
            )
        return NotImplemented

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id})>'

    @property
    def name(self) -> typing.Dict[str, str]:
        return {
            translation.language.lang_code: translation.name
            for translation in self.translations
            if translation.name
        }

    @property
    def notes(self) -> typing.Dict[str, str]:
        return {
            translation.language.lang_code: translation.notes
            for translation in self.translations
            if translation.notes
        }

    @property
    def description(self) -> typing.Dict[str, str]:
        return {
            translation.language.lang_code: translation.description
            for translation in self.translations
            if translation.description
        }

    @property
    def short_description(self) -> typing.Dict[str, str]:
        return {
            translation.language.lang_code: translation.short_description
            for translation in self.translations
            if translation.short_description
        }
