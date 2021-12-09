# coding: utf-8
"""

"""

import typing

from .. import db

__author__ = 'Du Kim Nguyen <k.nguyen@fz-juelich.de>'


class Language(db.Model):
    __tablename__ = 'languages'

    # default language IDs
    # offset to -100 to allow later addition of new default languages
    # see: migrations/languages_create_default_languages.py
    ENGLISH = -100 + 1
    GERMAN = -100 + 2

    id = db.Column(db.Integer, primary_key=True)
    lang_code = db.Column(db.String, nullable=False, unique=True)
    names = db.Column(db.JSON, nullable=False)
    datetime_format_datetime = db.Column(db.String)
    datetime_format_moment = db.Column(db.String)
    enabled_for_input = db.Column(db.Boolean, nullable=False)
    enabled_for_user_interface = db.Column(db.Boolean, nullable=False, default=False, server_default='FALSE')

    def __init__(
            self,
            names: typing.Dict[str, str],
            lang_code: str,
            datetime_format_datetime: str,
            datetime_format_moment: str,
            enabled_for_input: bool,
            enabled_for_user_interface: bool
    ):
        self.names = names
        self.lang_code = lang_code
        self.datetime_format_datetime = datetime_format_datetime
        self.datetime_format_moment = datetime_format_moment
        self.enabled_for_input = enabled_for_input
        self.enabled_for_user_interface = enabled_for_user_interface

    def __eq__(self, other):
        return (
            self.names == other.nams and
            self.lang_code == other.lang_code and
            self.datetime_format_datetime == other.datetime_format_datetime and
            self.datetime_format_moment == other.datetime_format_moment and
            self.enabled_for_input == other.enabled_for_input and
            self.enabled_for_user_interface == other.enabled_for_user_interface
        )

    def __repr__(self):
        return '<{0}(id={1.id}, name={1.names.get("en", "Unknown")})>'.format(type(self).__name__, self)
