# coding: utf-8
"""

"""

from http import HTTPStatus
import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField
from wtforms import validators

from .. import frontend
from ...logic import users, errors


class UserReadOnlyForm(FlaskForm):
    action = StringField(validators=[validators.AnyOf(['toggle_read_only'])])
    should_be_read_only = BooleanField()


class UserHiddenForm(FlaskForm):
    action = StringField(validators=[validators.AnyOf(['toggle_hidden'])])
    should_be_hidden = BooleanField()


class UserActiveForm(FlaskForm):
    action = StringField(validators=[validators.AnyOf(['toggle_active'])])
    should_be_active = BooleanField()


@frontend.route('/users/me')
@flask_login.login_required
def current_user_profile():
    return flask.redirect(flask.url_for('.user_profile', user_id=flask_login.current_user.id))


@frontend.route('/users/<int:user_id>', methods=['GET', 'POST'])
@flask_login.login_required
def user_profile(user_id):
    try:
        user = users.get_user(user_id)
    except errors.UserDoesNotExistError:
        return flask.abort(404)
    if flask_login.current_user.is_admin and not flask_login.current_user.is_readonly:
        user_read_only_form = UserReadOnlyForm()
        user_read_only_form.should_be_read_only.default = not user.is_readonly
        if user_read_only_form.validate_on_submit():
            users.set_user_readonly(user.id, user_read_only_form.should_be_read_only.data)
            if user_read_only_form.should_be_read_only.data:
                flask.flash(_('The user has been marked as read only.'), 'success')
            else:
                flask.flash(_('The user has been unmarked as read only.'), 'success')
            return flask.redirect(flask.url_for('.user_profile', user_id=user.id))
        user_hidden_form = UserHiddenForm()
        user_hidden_form.should_be_hidden.default = not user.is_hidden
        if user_hidden_form.validate_on_submit():
            users.set_user_hidden(user.id, user_hidden_form.should_be_hidden.data)
            if user_hidden_form.should_be_hidden.data:
                flask.flash(_('The user has been marked as hidden.'), 'success')
            else:
                flask.flash(_('The user has been unmarked as hidden.'), 'success')
            return flask.redirect(flask.url_for('.user_profile', user_id=user.id))
        user_active_form = UserActiveForm()
        user_active_form.should_be_active.default = not user.is_active
        if user_active_form.validate_on_submit():
            users.set_user_active(user.id, user_active_form.should_be_active.data)
            if user_active_form.should_be_active.data:
                flask.flash(_('The user has been activated.'), 'success')
            else:
                flask.flash(_('The user has been deactivated.'), 'success')
            return flask.redirect(flask.url_for('.user_profile', user_id=user.id))
    elif flask.request.method.lower() == 'post':
        return flask.abort(HTTPStatus.METHOD_NOT_ALLOWED)
    else:
        user_read_only_form = None
        user_hidden_form = None
        user_active_form = None
    return flask.render_template(
        'profile.html',
        user_read_only_form=user_read_only_form,
        user_hidden_form=user_hidden_form,
        user_active_form=user_active_form,
        user=user,
        EXTRA_USER_FIELDS=flask.current_app.config['EXTRA_USER_FIELDS'],
    )
