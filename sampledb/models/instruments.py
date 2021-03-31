# coding: utf-8
"""

"""

from .. import db

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

instrument_user_association_table = db.Table(
    'association',
    db.metadata,
    db.Column('instrument_id', db.Integer, db.ForeignKey('instruments.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
)


class Instrument(db.Model):
    __tablename__ = 'instruments'

    id = db.Column(db.Integer, primary_key=True)
    responsible_users = db.relationship("User", secondary=instrument_user_association_table, order_by="User.name")
    users_can_create_log_entries = db.Column(db.Boolean, nullable=False, default=False)
    users_can_view_log_entries = db.Column(db.Boolean, nullable=False, default=False)
    create_log_entry_default = db.Column(db.Boolean, nullable=False, default=False)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False)
    notes_is_markdown = db.Column(db.Boolean, nullable=True, default=False)
    description_is_markdown = db.Column(db.Boolean, nullable=True, default=False)
    short_description_is_markdown = db.Column(db.Boolean, nullable=False, default=False)

    instrument_translations = db.relationship("InstrumentTranslation", back_populates="instruments")

    def __init__(
            self,
            description_is_markdown: bool = False,
            short_description_is_markdown: bool = False,
            notes_is_markdown: bool = False,
            users_can_create_log_entries: bool = False,
            users_can_view_log_entries: bool = False,
            create_log_entry_default: bool = False,
            is_hidden: bool = False
    ):
        self.description_is_markdown = description_is_markdown
        self.short_description_is_markdown = short_description_is_markdown
        self.notes_is_markdown = notes_is_markdown
        self.users_can_create_log_entries = users_can_create_log_entries
        self.users_can_view_log_entries = users_can_view_log_entries
        self.create_log_entry_default = create_log_entry_default
        self.is_hidden = is_hidden

    def __eq__(self, other):
        return (
            self.id == other.id and
            self.description_is_markdown == other.description_is_markdown and
            self.short_description_is_markdown == other.short_description_is_markdown and
            self.notes_is_markdown == other.notes_is_markdown and
            self.users_can_create_log_entries == other.users_can_create_log_entries and
            self.users_can_view_log_entries == other.users_can_view_log_entries and
            self.create_log_entry_default == other.create_log_entry_default and
            self.is_hidden == other.is_hidden and
            self.responsible_users == other.responsible_users
        )

    def __repr__(self):
        return '<{0}(id={1.id})>'.format(type(self).__name__, self)
