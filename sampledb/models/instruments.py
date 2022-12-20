# coding: utf-8
"""

"""

import typing

from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

instrument_user_association_table = db.Table(
    'association',
    db.metadata,
    db.Column('instrument_id', db.Integer, db.ForeignKey('instruments.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
)


class Instrument(db.Model):  # type: ignore
    __tablename__ = 'instruments'
    __table_args__ = (
        db.UniqueConstraint('fed_id', 'component_id', name='instruments_fed_id_component_id_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    responsible_users = db.relationship("User", secondary=instrument_user_association_table, order_by="User.name", lazy='selectin')
    users_can_create_log_entries = db.Column(db.Boolean, nullable=False, default=False)
    users_can_view_log_entries = db.Column(db.Boolean, nullable=False, default=False)
    create_log_entry_default = db.Column(db.Boolean, nullable=False, default=False)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False)
    notes_is_markdown = db.Column(db.Boolean, nullable=True, default=False)
    description_is_markdown = db.Column(db.Boolean, nullable=True, default=False)
    short_description_is_markdown = db.Column(db.Boolean, nullable=False, default=False)
    fed_id = db.Column(db.Integer, nullable=True)
    component_id = db.Column(db.Integer, db.ForeignKey('components.id'), nullable=True)
    component = db.relationship('Component')
    translations = db.relationship('InstrumentTranslation', lazy='selectin')
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    location = db.relationship('Location')

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
            component_id: typing.Optional[int] = None
    ) -> None:
        self.description_is_markdown = description_is_markdown
        self.short_description_is_markdown = short_description_is_markdown
        self.notes_is_markdown = notes_is_markdown
        self.users_can_create_log_entries = users_can_create_log_entries
        self.users_can_view_log_entries = users_can_view_log_entries
        self.create_log_entry_default = create_log_entry_default
        self.is_hidden = is_hidden
        self.fed_id = fed_id
        self.component_id = component_id

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
        return '<{0}(id={1.id})>'.format(type(self).__name__, self)

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
