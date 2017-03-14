# coding: utf-8
"""

"""

import flask

from . import frontend

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/actions/')
def actions():
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/actions/<int:action_id>')
def action(action_id):
    # TODO: implement this
    return flask.render_template('index.html')
