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
    name = db.Column(db.String, nullable=False, unique=True)
    description = db.Column(db.String, nullable=False, default='')
    responsible_users = db.relationship("User", secondary=instrument_user_association_table, order_by="User.name")
    description_is_markdown = db.Column(db.Boolean, nullable=False, default=False)
    users_can_create_log_entries = db.Column(db.Boolean, nullable=False, default=False)
    users_can_view_log_entries = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.String, nullable=False, default='')
    notes_is_markdown = db.Column(db.Boolean, nullable=False, default=False)
    create_log_entry_default = db.Column(db.Boolean, nullable=False, default=False)
    is_hidden = db.Column(db.Boolean, nullable=False, default=False)
    short_description = db.Column(db.String, nullable=False, default='')
    short_description_is_markdown = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(
            self,
            name: str,
            description: str = '',
            description_is_markdown: bool = False,
            users_can_create_log_entries: bool = False,
            users_can_view_log_entries: bool = False,
            notes: str = '',
            notes_is_markdown: bool = False,
            create_log_entry_default: bool = False,
            is_hidden: bool = False,
            short_description: str = '',
            short_description_is_markdown: bool = False
    ):
        self.name = name
        self.description = description
        self.description_is_markdown = description_is_markdown
        self.users_can_create_log_entries = users_can_create_log_entries
        self.users_can_view_log_entries = users_can_view_log_entries
        self.notes = notes
        self.notes_is_markdown = notes_is_markdown
        self.create_log_entry_default = create_log_entry_default
        self.is_hidden = is_hidden
        self.short_description = short_description
        self.short_description_is_markdown = short_description_is_markdown

    def __eq__(self, other):
        return (
            self.id == other.id and
            self.name == other.name and
            self.description == other.description and
            self.description_is_markdown == other.description_is_markdown and
            self.users_can_create_log_entries == other.users_can_create_log_entries and
            self.users_can_view_log_entries == other.users_can_view_log_entries and
            self.notes == other.notes and
            self.notes_is_markdown == other.notes_is_markdown and
            self.short_description == other.short_description and
            self.short_description_is_markdown == other.short_description_is_markdown and
            self.create_log_entry_default == other.create_log_entry_default and
            self.is_hidden == other.is_hidden and
            self.responsible_users == other.responsible_users
        )

    def __repr__(self):
        return '<{0}(id={1.id}, name={1.name})>'.format(type(self).__name__, self)
