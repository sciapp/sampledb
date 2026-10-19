import typing
from http import HTTPStatus

import flask
from pydantic import BaseModel, Field

from .authentication import multi_auth
from .utils.responses import ErrorDetailsModel, PaginatedSequence, PaginationQueryModel
from .utils.openapi import method
from ..utils import Resource
from ...logic.instruments import get_instrument, get_instruments
from ...logic import errors, instruments


class InstrumentModel(BaseModel):
    instrument_id: int = Field(description="the ID of the instrument", examples=[1])
    name: dict[str, str] = Field(description="the name of the instrument", examples=[{"en": "Example Instrument"}])
    short_description: dict[str, str] = Field(description="the short description of the instrument, shown in instrument lists", examples=[{"en": "This is an example instrument."}])
    description: dict[str, str] = Field(description="the description of the instrument, shown on the instrument page", examples=[{"en": "This is an example instrument."}])
    is_hidden: bool = Field(description="whether the instrument is hidden from object lists", examples=[False])
    instrument_scientists: list[int] = Field(description="the list of instrument scientists for the instrument", examples=[[1]])
    location_id: int | None = Field(description="the ID of the location of the instrument", examples=[1])
    fed_id: int | None = Field(description="the federated ID of the instrument", examples=[1])
    component_id: int | None = Field(description="the federation component ID of the instrument", examples=[1])

    @classmethod
    def from_instrument(cls, instrument: instruments.Instrument) -> typing.Self:
        return cls(
            instrument_id=instrument.id,
            name=instrument.name,
            short_description=instrument.short_description,
            description=instrument.description,
            is_hidden=instrument.is_hidden,
            instrument_scientists=[user.id for user in instrument.responsible_users],
            location_id=instrument.location_id,
            fed_id=instrument.fed_id,
            component_id=instrument.component_id,
        )


class InstrumentNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested instrument does not exist."


class Instrument(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> InstrumentModel | InstrumentNotFoundModel:
        """
        Get an instrument.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        try:
            instrument = get_instrument(
                instrument_id=path.instrument_id
            )
        except errors.InstrumentDoesNotExistError:
            return InstrumentNotFoundModel(
                detail=f"Instrument #{path.instrument_id} does not exist."
            )
        return InstrumentModel.from_instrument(instrument)


class Instruments(Resource):
    @multi_auth.login_required
    @method()
    def get(self, query: PaginationQueryModel) -> PaginatedSequence[InstrumentModel]:
        """
        List all instruments.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return PaginatedSequence[InstrumentModel](
                items=[],
                query=query,
                id_getter=lambda instrument: instrument.instrument_id,
            )
        instruments = get_instruments(after_id=query.previous_id, limit=query.limit)
        return PaginatedSequence(
            items=[
                InstrumentModel.from_instrument(instrument)
                for instrument in instruments
            ],
            query=query,
            id_getter=lambda instrument: instrument.instrument_id,
        )
