# coding: utf-8
"""

"""
import typing

from .. import db

__author__ = 'Du Kim Nguyen <k.nguyen@fz-juelich.de>'


class InstrumentTranslation(db.Model):  # type: ignore
    __tablename__ = 'instrument_translations'

    id = db.Column(db.Integer, primary_key=True)

    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'))

    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'))
    language = db.relationship('Language')

    name = db.Column(db.String, nullable=True, default='')
    description = db.Column(db.String, nullable=True, default='')
    notes = db.Column(db.String, nullable=True, default='')
    short_description = db.Column(db.String, nullable=True, default='')

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
        self.instrument_id = instrument_id
        self.language_id = language_id
        self.name = name
        self.description = description
        self.notes = notes
        self.short_description = short_description

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
        return '<{0}(id={1.id}, name={1.language_id})>'.format(type(self).__name__, self)
