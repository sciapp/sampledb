# coding: utf-8
"""
RESTful API for the SampleDB frontend
"""

from flask import Blueprint

frontend_api = Blueprint('frontend_api', __name__)

from . import favorites

frontend_api.add_url_rule('/api/frontend/favorite_actions/<int:action_id>', endpoint='favorite_actions', view_func=favorites.FavoriteAction.as_view('favorite_action'))
frontend_api.add_url_rule('/api/frontend/favorite_instruments/<int:instrument_id>', endpoint='favorite_instruments', view_func=favorites.FavoriteInstrument.as_view('favorite_instrument'))
