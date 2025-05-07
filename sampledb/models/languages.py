# coding: utf-8
"""

"""

import typing

from sqlalchemy.orm import Mapped, Query

from .. import db
from .utils import Model

__author__ = 'Du Kim Nguyen <k.nguyen@fz-juelich.de>'


class Language(Model):
    __tablename__ = 'languages'

    __table_args__ = (
        db.UniqueConstraint('lang_code', 'fed_lang_id', 'component_id', name='languages_lang_code_fed_lang_id_component_id_key'),
    )

    # default language IDs
    # offset to -100 to allow later addition of new default languages
    # see: migrations/languages_create_default_languages.py
    ENGLISH: int = -100 + 1
    GERMAN: int = -100 + 2

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    lang_code: Mapped[str] = db.Column(db.String, nullable=False, unique=False)
    names: Mapped[typing.Dict[str, str]] = db.Column(db.JSON, nullable=False)
    datetime_format_datetime: Mapped[str] = db.Column(db.String, nullable=False)
    datetime_format_moment: Mapped[str] = db.Column(db.String, nullable=False)
    enabled_for_input: Mapped[bool] = db.Column(db.Boolean, nullable=False)
    enabled_for_user_interface: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, server_default='FALSE')
    datetime_format_moment_output: Mapped[str] = db.Column(db.String, nullable=False, default='lll', server_default='lll')
    date_format_moment_output: Mapped[str] = db.Column(db.String, nullable=False, default='ll', server_default='ll')
    fed_lang_id: Mapped[int] = db.Column(db.Integer, default=None, server_default=db.null())
    component_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('components.id'), default=None, server_default=db.null())

    if typing.TYPE_CHECKING:
        query: typing.ClassVar[Query["Language"]]

    def __init__(
            self,
            names: typing.Dict[str, str],
            lang_code: str,
            datetime_format_datetime: str,
            datetime_format_moment: str,
            datetime_format_moment_output: str,
            date_format_moment_output: str,
            enabled_for_input: bool,
            enabled_for_user_interface: bool,
            fed_lang_id: typing.Optional[int] = None,
            component_id: typing.Optional[int] = None
    ) -> None:
        super().__init__(
            names=names,
            lang_code=lang_code,
            datetime_format_datetime=datetime_format_datetime,
            datetime_format_moment=datetime_format_moment,
            datetime_format_moment_output=datetime_format_moment_output,
            date_format_moment_output=date_format_moment_output,
            enabled_for_input=enabled_for_input,
            enabled_for_user_interface=enabled_for_user_interface,
            fed_lang_id=fed_lang_id,
            component_id=component_id
        )

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, Language):
            return bool(
                self.names == other.names and
                self.lang_code == other.lang_code and
                self.datetime_format_datetime == other.datetime_format_datetime and
                self.datetime_format_moment == other.datetime_format_moment and
                self.datetime_format_moment_output == other.datetime_format_moment_output and
                self.date_format_moment_output == other.date_format_moment_output and
                self.enabled_for_input == other.enabled_for_input and
                self.enabled_for_user_interface == other.enabled_for_user_interface
            )
        return NotImplemented

    def __repr__(self) -> str:
        return f'<{type(self).__name__}(id={self.id}, name={self.names.get("en", "Unknown")})>'
