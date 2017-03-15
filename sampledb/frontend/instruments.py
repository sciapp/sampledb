# coding: utf-8
"""

"""

import flask

from . import frontend
from ..logic.instruments import get_instruments, get_instrument

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/instruments/')
def instruments():
    instruments = get_instruments()
    # TODO: check instrument permissions
    return flask.render_template('instrumens/instruments.html', instruments=instruments)


@frontend.route('/instruments/<int:instrument_id>')
def instrument(instrument_id):
    instrument = get_instrument(instrument_id)
    if instrument is None:
        return flask.abort(404)
    # TODO: check instrument permissions
    return flask.render_template('instrumens/instrument.html', instrument=instrument)

