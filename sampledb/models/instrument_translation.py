# coding: utf-8
"""

"""

from .. import db

__author__ = 'Du Kim Nguyen <k.nguyen@fz-juelich.de>'


class InstrumentTranslation(db.Model):
    __tablename__ = 'instrument_translations'

    id = db.Column(db.Integer, primary_key=True)

    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'))
    instruments = db.relationship("Instrument", back_populates='instrument_translations')

    language_id = db.Column(db.Integer, db.ForeignKey('languages.id'))
    language = db.relationship('Language')

    name = db.Column(db.String, nullable=False, default='')
    description = db.Column(db.String, nullable=False, default='')
    notes = db.Column(db.String, nullable=False, default='')
    short_description = db.Column(db.String, nullable=False, default='')

    __table_args__ = (
        db.UniqueConstraint('language_id', 'instrument_id', name='_language_id_instrument_id_uc'),
    )

    def __init__(
            self,
            instrument_id: int,
            language_id: int,
            name: str,
            description: str = '',
            notes: str = '',
            short_description: str = '',
    ):
        self.instrument_id = instrument_id
        self.language_id = language_id
        self.name = name
        self.description = description
        self.notes = notes
        self.short_description = short_description

    def __eq__(self, other):
        return (
            self.id == other.id and
            self.language_id == other.language_id and
            self.instrument_id == other.instrument_id and
            self.name == other.name and
            self.description == other.description and
            self.notes == other.notes and
            self.short_description == other.short_description
        )

    def __repr__(self):
        return '<{0}(id={1.id}, name={1.language_id})>'.format(type(self).__name__, self)
