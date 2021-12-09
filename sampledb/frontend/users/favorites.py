# coding: utf-8
"""

"""

import flask
import flask_login
from flask_babel import _

from .. import frontend
from .forms import ToggleFavoriteActionForm, ToggleFavoriteInstrumentForm
from ...logic.favorites import add_favorite_action, remove_favorite_action, get_user_favorite_action_ids, add_favorite_instrument, remove_favorite_instrument, get_user_favorite_instrument_ids
from ..utils import check_current_user_is_not_readonly


@frontend.route('/users/me/favorite_actions/', methods=['POST'])
@flask_login.login_required
def toggle_favorite_action():
    check_current_user_is_not_readonly()
    toggle_favorite_action_form = ToggleFavoriteActionForm()
    if toggle_favorite_action_form.validate():
        action_id = toggle_favorite_action_form.action_id.data
        user_id = flask_login.current_user.id
        if action_id not in get_user_favorite_action_ids(user_id=user_id):
            add_favorite_action(action_id=action_id, user_id=user_id)
            flask.flash(_('The action has been added to your favorites.'), 'success')
        else:
            remove_favorite_action(action_id=action_id, user_id=user_id)
            flask.flash(_('The action has been removed from your favorites.'), 'success')
    else:
        flask.flash(_('An error occurred while editing your favorite actions. Please try again.'), 'error')
    return flask.redirect(flask.url_for(
        '.actions',
        sample_id=flask.request.args.get('sample_id', None),
        t=flask.request.args.get('t', None)
    ))


@frontend.route('/users/me/favorite_instruments/', methods=['POST'])
@flask_login.login_required
def toggle_favorite_instrument():
    check_current_user_is_not_readonly()
    toggle_favorite_instrument_form = ToggleFavoriteInstrumentForm()
    if toggle_favorite_instrument_form.validate():
        instrument_id = toggle_favorite_instrument_form.instrument_id.data
        user_id = flask_login.current_user.id
        if instrument_id not in get_user_favorite_instrument_ids(user_id=user_id):
            add_favorite_instrument(instrument_id=instrument_id, user_id=user_id)
            flask.flash(_('The instrument has been added to your favorites.'), 'success')
        else:
            remove_favorite_instrument(instrument_id=instrument_id, user_id=user_id)
            flask.flash(_('The instrument has been removed from your favorites.'), 'success')
    else:
        print(toggle_favorite_instrument_form.errors)
        flask.flash(_('An error occurred while editing your favorite instruments. Please try again.'), 'error')
    return flask.redirect(flask.url_for('.instruments'))
