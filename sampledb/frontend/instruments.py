# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from ..logic.instruments import get_instruments, get_instrument
from ..logic.actions import ActionType
from ..logic.errors import InstrumentDoesNotExistError
from ..logic.favorites import get_user_favorite_instrument_ids
from .users.forms import ToggleFavoriteInstrumentForm

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/instruments/')
@flask_login.login_required
def instruments():
    instruments = get_instruments()
    # TODO: check instrument permissions
    user_favorite_instrument_ids = get_user_favorite_instrument_ids(flask_login.current_user.id)
    # Sort by: favorite / not favorite, instrument name
    instruments.sort(key=lambda instrument: (
        0 if instrument.id in user_favorite_instrument_ids else 1,
        instrument.name.lower()
    ))
    toggle_favorite_instrument_form = ToggleFavoriteInstrumentForm()
    return flask.render_template(
        'instruments/instruments.html',
        instruments=instruments,
        user_favorite_instrument_ids=user_favorite_instrument_ids,
        toggle_favorite_instrument_form=toggle_favorite_instrument_form
    )


@frontend.route('/instruments/<int:instrument_id>')
@flask_login.login_required
def instrument(instrument_id):
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    # TODO: check instrument permissions
    return flask.render_template('instruments/instrument.html', instrument=instrument, ActionType=ActionType)

