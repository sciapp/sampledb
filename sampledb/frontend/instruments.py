# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from ..logic.instruments import get_instruments, get_instrument
from ..logic.actions import ActionType
from ..logic.errors import InstrumentDoesNotExistError

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/instruments/')
@flask_login.login_required
def instruments():
    instruments = get_instruments()
    # TODO: check instrument permissions
    return flask.render_template('instruments/instruments.html', instruments=instruments)


@frontend.route('/instruments/<int:instrument_id>')
@flask_login.login_required
def instrument(instrument_id):
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    # TODO: check instrument permissions
    return flask.render_template('instruments/instrument.html', instrument=instrument, ActionType=ActionType)

