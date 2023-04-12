# coding: utf-8
"""
RESTful API for SampleDB
"""
import typing

import flask

from .authentication import multi_auth
from ..utils import Resource, ResponseData
from ...logic.instruments import get_instrument, get_instruments
from ...logic import errors, utils, instruments

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def instrument_to_json(instrument: instruments.Instrument) -> typing.Dict[str, typing.Any]:
    return {
        'instrument_id': instrument.id,
        'name': utils.get_translated_text(instrument.name, 'en'),
        'description': utils.get_translated_text(instrument.description, 'en'),
        'is_hidden': instrument.is_hidden,
        'instrument_scientists': [user.id for user in instrument.responsible_users],
        'location_id': instrument.location_id
    }


class Instrument(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        try:
            instrument = get_instrument(
                instrument_id=instrument_id
            )
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        return instrument_to_json(instrument)


class Instruments(Resource):
    @multi_auth.login_required
    def get(self) -> ResponseData:
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return []
        instruments = get_instruments()
        return [
            instrument_to_json(instrument)
            for instrument in instruments
        ]
