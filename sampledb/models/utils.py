import typing

if typing.TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase

    Model = DeclarativeBase
else:
    from .. import db

    Model = db.Model
