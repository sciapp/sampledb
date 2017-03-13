# coding: utf-8
"""

"""

import json
import flask
import flask_login
from .. import db
from ..authentication.models import User
from ..authentication.logic import login
from ..instruments.logic import get_instruments, get_instrument
from ..instruments.models import Action, Instrument
from ..object_database.models import Objects
from ..permissions.logic import get_user_object_permissions, object_is_public, get_object_permissions, set_object_public, set_user_object_permissions
from ..permissions.utils import object_permissions_required, Permissions

from .forms import ObjectPermissionsForm, SigninForm, SignoutForm

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'

frontend = flask.Blueprint('frontend', __name__)



@frontend.route('/')
def index():
    return flask.render_template('index.html')


@frontend.route('/users/me/sign_in', methods=['GET', 'POST'])
def sign_in():
    form = SigninForm()
    has_errors = False
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember_me = form.remember_me.data
        # TODO: remember_me
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


@frontend.route('/instruments/')
def instruments():
    instruments = get_instruments()
    return flask.render_template('instruments.html', instruments=instruments)


@frontend.route('/instruments/<int:instrument_id>')
def instrument(instrument_id):
    instrument = get_instrument(instrument_id)
    if instrument is None:
        return flask.abort(404)
    # TODO: check instrument permissions
    return flask.render_template('instrument.html', instrument=instrument)


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
    objects = Objects.get_current_objects(connection=db.engine)
    if flask_login.current_user.is_authenticated:
        user_id = flask_login.current_user.id
        objects = [obj for obj in objects if Permissions.READ in get_user_object_permissions(user_id=user_id, object_id=obj.object_id)]
    else:
        objects = [obj for obj in objects if object_is_public(obj.object_id)]
    objects = [
        {
            'object_id': obj.object_id,
            'version_id': obj.version_id,
            'user_id': obj.user_id,
            'last_modified': obj.utc_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'data': obj.data,
            'schema': obj.schema
        }
        for obj in objects
    ]
    # TODO implement view
    return flask.render_template('index.html', objects=objects)


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
    object = Objects.get_current_object(object_id, connection=db.engine)
    action = Action.query.get(object.action_id)
    instrument = action.instrument
    object_permissions = get_object_permissions(object_id=object_id, include_instrument_responsible_users=False)
    if Permissions.GRANT in get_user_object_permissions(object_id=object_id, user_id=flask_login.current_user.id):
        public_permissions = 'none'
        if Permissions.READ in object_permissions[None]:
            public_permissions = 'read'
        user_permissions = []
        for user_id, permissions in object_permissions.items():
            if user_id is None:
                continue
            user_permissions.append({'user_id': user_id, 'permissions': permissions.name.lower()})
        form = ObjectPermissionsForm(public_permissions=public_permissions, user_permissions=user_permissions)
    else:
        form = None
    return flask.render_template('object_permissions.html', instrument=instrument, action=action, object=object, object_permissions=object_permissions, User=User, Permissions=Permissions, form=form)


@frontend.route('/objects/<int:object_id>/permissions', methods=['POST'])
@object_permissions_required(Permissions.GRANT)
def update_object_permissions(object_id):
    form = ObjectPermissionsForm()
    if form.validate_on_submit():
        set_object_public(object_id, form.public_permissions.data == 'read')
        for user_permissions_data in form.user_permissions.data:
            user_id = user_permissions_data['user_id']
            user = User.query.get(user_id)
            if user is None:
                continue
            permissions = Permissions.from_name(user_permissions_data['permissions'])
            set_user_object_permissions(object_id=object_id, user_id=user_id, permissions=permissions)
        flask.flash("Successfully updated object permissions.", 'success')
    else:
        flask.flash("A problem occurred while changing the object permissions. Please try again.", 'error')
    return flask.redirect(flask.url_for('.object_permissions', object_id=object_id))


@frontend.errorhandler(403)
def forbidden(error):
    return flask.render_template('403.html'), 403


@frontend.errorhandler(404)
def file_not_found(error):
    return flask.render_template('404.html'), 404


@frontend.errorhandler(500)
def internal_server_error(error):
    return flask.render_template('500.html'), 500
