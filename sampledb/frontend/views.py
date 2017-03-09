# coding: utf-8
"""

"""

import flask
import flask_login

from ..permissions.utils import object_permissions_required, Permissions

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

frontend = flask.Blueprint('frontend', __name__)


@frontend.route('/')
def index():
    return flask.render_template('index.html')


@frontend.route('/users/me/sign_in', methods=['GET', 'POST'])
def sign_in():
    # TODO: implement POST (sign in user or show error message and mark input fields as erroneous)
    return flask.render_template('signin.html')


@frontend.route('/users/me/sign_out', methods=['GET', 'POST'])
def sign_out():
    # TODO: implement GET (confirmation dialog)
    # TODO: implement POST (sign out and redirect)
    return flask.render_template('index.html')


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


@frontend.route('/instruments/')
def instruments():
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/instruments/<int:instrument_id>')
def instrument(instrument_id):
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/actions/')
def actions():
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/actions/<int:action_id>')
def action(action_id):
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/objects/')
def objects():
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/objects/<int:object_id>')
@object_permissions_required(Permissions.READ)
def object(object_id):
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/objects/<int:object_id>/versions')
@object_permissions_required(Permissions.READ)
def object_versions(object_id):
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/objects/<int:object_id>/versions/<int:version_id>')
@object_permissions_required(Permissions.READ)
def object_version(object_id, version_id):
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.route('/objects/<int:object_id>/permissions')
@object_permissions_required(Permissions.READ)
def object_permissions(object_id):
    # TODO: implement this
    return flask.render_template('index.html')


@frontend.errorhandler(403)
def forbidden(error):
    return flask.render_template('403.html'), 403


@frontend.errorhandler(404)
def file_not_found(error):
    return flask.render_template('404.html'), 404


@frontend.errorhandler(500)
def internal_server_error(error):
    return flask.render_template('500.html'), 500
