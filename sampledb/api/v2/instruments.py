# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask
from pydantic import BaseModel, Field

from .authentication import multi_auth
from .utils.validation import method
from ..utils import Resource, ResponseData
from ...logic.instruments import get_instrument, get_instruments
from ...logic import errors, utils, instruments

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def instrument_to_json(instrument: instruments.Instrument) -> typing.Dict[str, typing.Any]:
    return {
        'instrument_id': instrument.id,
        'name': utils.get_translated_text(instrument.name, 'en'),
        'short_description': utils.get_translated_text(instrument.short_description, 'en'),
        'description': utils.get_translated_text(instrument.description, 'en'),
        'is_hidden': instrument.is_hidden,
        'instrument_scientists': [user.id for user in instrument.responsible_users],
        'location_id': instrument.location_id,
        'fed_id': instrument.fed_id,
        'component_id': instrument.component_id,
    }


class Instrument(Resource):
    class PathModel(BaseModel):
        instrument_id: int = Field(description="the ID of an existing instrument", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get an instrument.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {path.instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(
                instrument_id=path.instrument_id
            )
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {path.instrument_id} does not exist"
            }, 404
        return instrument_to_json(instrument)


class Instruments(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> ResponseData:
        """
        List all instruments.
        """
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return []
        instruments = get_instruments()
        return [
            instrument_to_json(instrument)
            for instrument in instruments
        ]
