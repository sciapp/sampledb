# coding: utf-8
"""

"""
import typing

from sqlalchemy.orm import relationship, Mapped, Query

from .. import db
from .utils import Model

if typing.TYPE_CHECKING:
    from .languages import Language

__author__ = 'Du Kim Nguyen <k.nguyen@fz-juelich.de>'


class InstrumentTranslation(Model):
    __tablename__ = 'instrument_translations'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)

    instrument_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)

    language_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('languages.id'), nullable=False)
    language: Mapped['Language'] = relationship('Language')

    name: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True, default='')
    description: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True, default='')
    notes: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True, default='')
    short_description: Mapped[typing.Optional[str]] = db.Column(db.String, nullable=True, default='')

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["InstrumentTranslation"]]

    __table_args__ = (
        db.UniqueConstraint('language_id', 'instrument_id', name='_language_id_instrument_id_uc'),
        db.CheckConstraint(
            'NOT (name IS NULL AND description IS NULL AND notes IS NULL AND short_description IS NULL)',
            name='instrument_translations_not_empty_check'
        )
    )

    def __init__(
            self,
            instrument_id: int,
            language_id: int,
            name: str,
            description: str = '',
            notes: str = '',
            short_description: str = ''
    ) -> None:
        super().__init__(
            instrument_id=instrument_id,
            language_id=language_id,
            name=name,
            description=description,
            notes=notes,
            short_description=short_description
        )

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, InstrumentTranslation):
            return bool(
                self.id == other.id and
                self.language_id == other.language_id and
                self.instrument_id == other.instrument_id and
                self.name == other.name and
                self.description == other.description and
                self.notes == other.notes and
                self.short_description == other.short_description
            )
        return NotImplemented

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, name={self.language_id})>'
