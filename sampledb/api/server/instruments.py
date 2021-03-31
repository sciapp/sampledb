# coding: utf-8
"""
RESTful API for SampleDB
"""

from flask_restful import Resource

from .authentication import multi_auth
from ...logic.instrument_translations import get_instrument_with_translation_in_language, get_instruments_with_translation_in_language
from ...logic.languages import Language
from ...logic import errors

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


def instrument_to_json(instrument):
    return {
        'instrument_id': instrument.id,
        'name': instrument.translation.name,
        'description': instrument.translation.description,
        'is_hidden': instrument.is_hidden,
        'instrument_scientists': [user.id for user in instrument.responsible_users]
    }


class Instrument(Resource):
    @multi_auth.login_required
    def get(self, instrument_id: int):
        try:
            instrument = get_instrument_with_translation_in_language(
                instrument_id=instrument_id,
                language_id=Language.ENGLISH
            )
        except errors.InstrumentDoesNotExistError:
            return {
                "message": "instrument {} does not exist".format(instrument_id)
            }, 404
        return instrument_to_json(instrument)


class Instruments(Resource):
    @multi_auth.login_required
    def get(self):
        instruments = get_instruments_with_translation_in_language(
            language_id=Language.ENGLISH
        )
        return [instrument_to_json(instrument) for instrument in instruments]
