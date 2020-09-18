# coding: utf-8
"""
RESTful API for iffSamples
"""

from flask_restful import Resource

from sampledb.api.server.authentication import multi_auth
from sampledb.logic.instruments import get_instrument, get_instruments
from sampledb.logic import errors

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def instrument_to_json(instrument):
    return {
        'instrument_id': instrument.id,
        'name': instrument.name,
        'description': instrument.description,
        'is_hidden': instrument.is_hidden,
        'instrument_scientists': [user.id for user in instrument.responsible_users]
    }


class Instrument(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int):
        try:
            instrument = get_instrument(instrument_id=instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": "instrument {} does not exist".format(instrument_id)
            }, 404
        return instrument_to_json(instrument)


class Instruments(Resource):
    @multi_auth.login_required
    def get(self):
        instruments = get_instruments()
        return [instrument_to_json(instrument) for instrument in instruments]
