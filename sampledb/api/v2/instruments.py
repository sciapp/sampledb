import typing

import flask
from pydantic import BaseModel, Field

from .authentication import multi_auth
from .utils.responses import NotFoundErrorModel
from .utils.openapi import method
from ..utils import Resource
from ...logic.instruments import get_instrument, get_instruments
from ...logic import errors, utils, instruments

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


class InstrumentModel(BaseModel):
    instrument_id: int = Field(description="the ID of the instrument", examples=[1])
    name: str = Field(description="the name of the instrument", examples=["Example Instrument"])
    short_description: str = Field(description="the short description of the instrument, shown in instrument lists", examples=["This is an example instrument."])
    description: str = Field(description="the description of the instrument, shown on the instrument page", examples=["This is an example instrument."])
    is_hidden: bool = Field(description="whether the instrument is hidden from object lists", examples=[False])
    instrument_scientists: list[int] = Field(description="the list of instrument scientists for the instrument", examples=[[1]])
    location_id: int | None = Field(description="the ID of the location of the instrument", examples=[1])
    fed_id: int | None = Field(description="the federated ID of the instrument", examples=[1])
    component_id: int | None = Field(description="the federation component ID of the instrument", examples=[1])

    @classmethod
    def from_instrument(cls, instrument: instruments.Instrument) -> typing.Self:
        return cls(
            instrument_id=instrument.id,
            name=utils.get_translated_text(instrument.name, 'en'),
            short_description=utils.get_translated_text(instrument.short_description, 'en'),
            description=utils.get_translated_text(instrument.description, 'en'),
            is_hidden=instrument.is_hidden,
            instrument_scientists=[user.id for user in instrument.responsible_users],
            location_id=instrument.location_id,
            fed_id=instrument.fed_id,
            component_id=instrument.component_id,
        )


class Instrument(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> InstrumentModel | NotFoundErrorModel:
        """
        Get an instrument.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"instrument {path.instrument_id} does not exist"
            )
        try:
            instrument = get_instrument(
                instrument_id=path.instrument_id
            )
        except errors.InstrumentDoesNotExistError:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"instrument {path.instrument_id} does not exist"
            )
        return InstrumentModel.from_instrument(instrument)


class Instruments(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> list[InstrumentModel]:
        """
        List all instruments.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return []
        instruments = get_instruments()
        return [
            InstrumentModel.from_instrument(instrument)
            for instrument in instruments
        ]
