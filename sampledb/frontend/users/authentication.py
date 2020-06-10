# coding: utf-8
"""

"""

import flask
import flask_login

from .. import frontend
from ...logic.authentication import login
from ...logic.users import get_user
from ...frontend.users_forms import SigninForm, SignoutForm
from ... import login_manager


@login_manager.user_loader
def load_user(user_id):
    try:
        user_id = int(user_id)
    except ValueError:
        return None
    return get_user(user_id)


def _is_url_safe_for_redirect(url: str) -> bool:
    """
    Checks whether a URL is safe for redirecting a user to it.

    URLs are deemed safe if they are absolute URLs on the current domain and
    server path. This is enforced by only allowing URLs that start with the
    absolute server path and only consist of alphanumerical characters or the
    following characters: /=?&_.+-

    :param url: the URL to check
    :return: whether it is safe to redirect to or not
    """
    server_path = flask.current_app.config.get('SERVER_PATH', '/')
    # ensure the server path starts with a / to avoid relative paths or non-local paths
    if not server_path.startswith('/'):
        server_path = '/' + server_path
    # ensure the server path ends with a / to avoid paths with it as a prefix
    if not server_path.endswith('/'):
        server_path = server_path + '/'
    # prevent double slashes that would change the domain
    if url.startswith('//'):
        return False
    return url.startswith(server_path) and all(c in '/=?&_.+-' or c.isalnum() for c in url)


def _redirect_to_next_url():
    next_url = flask.request.args.get('next', flask.url_for('.index'))
    index_url = flask.url_for('.index')
    if not _is_url_safe_for_redirect(next_url):
        next_url = index_url
    return flask.redirect(next_url)


def _sign_in_impl(is_for_refresh):
    form = SigninForm()
    has_errors = False
    if form.validate_on_submit():
        username = form.username.data
        # enforce lowercase for username to ensure case insensitivity
        # TODO: move this to the model and logic layer
        username = username.lower()
        password = form.password.data
        user = login(username, password)
        if is_for_refresh:
            if user and user == flask_login.current_user:
                flask_login.confirm_login()
                return _redirect_to_next_url()
        else:
            if user:
                remember_me = form.remember_me.data
                flask_login.login_user(user, remember=remember_me)
                if user.is_admin and password == 'password':
                    flask.flash(
                        'You are using the default admin password from the '
                        'SampleDB documentation. Please change your password '
                        'before making this SampleDB instance available to '
                        'other users.',
                        'warning'
                    )
                return _redirect_to_next_url()
        has_errors = True
    elif form.errors:
        has_errors = True
    return flask.render_template('sign_in.html', form=form, is_for_refresh=is_for_refresh, has_errors=has_errors)


@frontend.route('/users/me/sign_in', methods=['GET', 'POST'])
def sign_in():
    if flask_login.current_user.is_authenticated:
        # if the user was already authenticated, redirect to the index.
        return flask.redirect(flask.url_for('.index'))
    return _sign_in_impl(is_for_refresh=False)


@frontend.route('/users/me/refresh_sign_in', methods=['GET', 'POST'])
@flask_login.login_required
def refresh_sign_in():
    if flask_login.current_user.is_authenticated and flask_login.login_fresh():
        # if the login was already fresh, redirect to the next_url or index.
        return _redirect_to_next_url()
    return _sign_in_impl(is_for_refresh=True)


@frontend.route('/users/me/sign_out', methods=['GET', 'POST'])
@flask_login.login_required
def sign_out():
    form = SignoutForm()
    if form.validate_on_submit():
        flask_login.logout_user()
        return flask.redirect(flask.url_for('.index'))
    return flask.render_template('sign_out.html')
