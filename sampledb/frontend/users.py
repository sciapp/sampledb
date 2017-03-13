# coding: utf-8
"""

"""

import flask
import flask_login

from . import frontend
from sampledb.logic.authentication import login
from .users_forms import SigninForm, SignoutForm

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/users/me/sign_in', methods=['GET', 'POST'])
def sign_in():
    # TODO: handle next
    if flask_login.current_user.is_authenticated:
        return flask.redirect(flask.url_for('.index'))
    form = SigninForm()
    has_errors = False
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember_me = form.remember_me.data
        # TODO: handle remember_me
        if login(username, password):
            return flask.redirect(flask.url_for('.index'))
        has_errors = True
    elif form.errors:
        has_errors = True
    return flask.render_template('sign_in.html', form=form, has_errors=has_errors)


@frontend.route('/users/me/sign_out', methods=['GET', 'POST'])
@flask_login.login_required
def sign_out():
    form = SignoutForm()
    if form.validate_on_submit():
        flask_login.logout_user()
        return flask.redirect(flask.url_for('.index'))
    return flask.render_template('sign_out.html')


@frontend.route('/users/invitation', methods=['GET', 'POST'])
def invitation():
    # TODO: initial instrument permissions?
    # TODO: implement GET (invitation dialog or confirmation dialog)
    # TODO: implement POST (send invitation and redirect or register user and redirect)
    return flask.render_template('index.html')


@frontend.route('/users/me')
@frontend.route('/users/<int:user_id>')
@flask_login.login_required
def user_profile(user_id=None):
    if user_id is None:
        return flask.redirect(flask.url_for('.user_profile', user_id=flask_login.current_user.id))
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/users/me/preferences')
@frontend.route('/users/<int:user_id>/preferences')
@flask_login.login_required
def user_preferences(user_id=None):
    if user_id is None:
        return flask.redirect(flask.url_for('.user_preferences', user_id=flask_login.current_user.id))
    if user_id != flask_login.current_user.id:
        return flask.abort(403)
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/users/me/activity')
@frontend.route('/users/<int:user_id>/activity')
@flask_login.login_required
def user_activity(user_id=None):
    if user_id is None:
        return flask.redirect(flask.url_for('.user_activity', user_id=flask_login.current_user.id))
    # TODO: implement this
    return flask.render_template('index.html')
