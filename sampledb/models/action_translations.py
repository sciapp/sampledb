# coding: utf-8
"""

"""
import typing

from sqlalchemy.orm import Mapped, Query, relationship

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .languages import Language


class ActionTypeTranslation(Model):
    __tablename__ = 'action_type_translations'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)

    language_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('languages.id'), nullable=False)
    language: Mapped['Language'] = relationship('Language')

    action_type_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('action_types.id'), nullable=False)

    name: Mapped[str] = db.Column(db.String, nullable=False)
    description: Mapped[str] = db.Column(db.String, nullable=False)
    object_name: Mapped[str] = db.Column(db.String, nullable=False)
    object_name_plural: Mapped[str] = db.Column(db.String, nullable=False)
    view_text: Mapped[str] = db.Column(db.String, nullable=False)
    perform_text: Mapped[str] = db.Column(db.String, nullable=False)

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ActionTypeTranslation"]]

    __table_args__ = (
        db.UniqueConstraint('language_id', 'action_type_id', name='_language_id_action_type_id_uc'),
        # TODO: action translation and instrument translation have not-null contraints, but this doesn't
    )

    def __init__(
            self,
            language_id: int,
            action_type_id: int,
            name: str,
            description: str,
            object_name: str,
            object_name_plural: str,
            view_text: str,
            perform_text: str
    ) -> None:
        super().__init__(
            language_id=language_id,
            action_type_id=action_type_id,
            name=name,
            description=description,
            object_name=object_name,
            object_name_plural=object_name_plural,
            view_text=view_text,
            perform_text=perform_text
        )

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, ActionTypeTranslation):
            return bool(
                self.id == other.id and
                self.language_id == other.language_id and
                self.action_type_id == other.action_type_id and
                self.name == other.name and
                self.description == other.description and
                self.object_name == other.object_name and
                self.object_name_plural == other.object_name_plural and
                self.view_text == other.view_text and
                self.perform_text == other.perform_text
            )
        return NotImplemented

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id!r}, name={self.name!r})>'


class ActionTranslation(Model):
    __tablename__ = 'action_translations'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)

    language_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('languages.id'), nullable=False)
    language: Mapped['Language'] = relationship('Language')

    action_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('actions.id'), nullable=False)

    name: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True)
    description: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True, default='')
    short_description: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True, default='')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["ActionTranslation"]]

    __table_args__ = (
        db.UniqueConstraint('language_id', 'action_id', name='_language_id_action_id_uc'),
        db.CheckConstraint(
            'NOT (name IS NULL AND description IS NULL AND short_description IS NULL)',
            name='action_translations_not_empty_check'
        )
    )

    def __init__(
            self,
            action_id: int,
            language_id: int,
            name: str,
            description: str = '',
            short_description: str = '',
    ) -> None:
        super().__init__(
            action_id=action_id,
            language_id=language_id,
            name=name,
            description=description,
            short_description=short_description
        )

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, ActionTranslation):
            return bool(
                self.id == other.id and
                self.action_id == other.action_id and
                self.language_id == other.language_id and
                self.name == other.name and
                self.description == other.description and
                self.short_description == other.short_description
            )
        return NotImplemented

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id!r})>'
