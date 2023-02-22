"""
Wrapper module for Flask-MonitoringDashboard

This module creates an extension-like interface for Flask-MonitoringDashboard
and ensures that nothing is imported from that package if it should not be
used, as the package already performs some logic on import.

Also, this module defines replacement functions for the authentication process
of the dashboard, so that the existing Flask-Login based authentication system
is used.
"""
import functools
import os
import secrets
import typing

import flask
import flask_login
import werkzeug.exceptions

from . import version

F = typing.TypeVar('F', bound=typing.Callable[..., typing.Any])


def _secure(func: F) -> F:
    @flask_login.login_required
    @functools.wraps(func)
    def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if not _is_admin():
            return flask.abort(403)
        return func(*args, **kwargs)
    return typing.cast(F, wrapper)


def _is_admin() -> bool:
    return bool(flask_login.current_user.is_authenticated and flask_login.current_user.is_admin)


def _on_login(user: typing.Any) -> None:
    if not _is_admin():
        # login via dashboard is disabled
        raise werkzeug.exceptions.Forbidden()


def _on_logout() -> werkzeug.Response:
    flask_login.logout_user()
    return flask.redirect(flask.url_for('frontend.index'))


def _get_current_user_id() -> typing.Optional[int]:
    if flask_login.current_user.is_authenticated:
        return flask_login.current_user.get_id()
    return None


def _get_ip() -> str:
    return flask.request.headers.get('X-Forwarded-For', flask.request.environ['REMOTE_ADDR'])


def init_app(app: flask.Flask) -> None:
    # late import to only create dashboard Blueprint if it should be used
    try:
        import flask_monitoringdashboard as dashboard
    except ImportError:
        # set TZ variable to prevent crash in tzlocal 2.0.0 get_localzone
        if not os.environ.get('TZ'):
            os.environ['TZ'] = 'UTC'
        # try importing again
        import flask_monitoringdashboard as dashboard

    # replace authentication functions to use flask_login instead
    from flask_monitoringdashboard.core import auth
    auth.secure = _secure
    auth.admin_secure = _secure
    auth.is_admin = _is_admin
    auth.on_login = _on_login
    auth.on_logout = _on_logout

    dashboard.config.link = 'admin/dashboard'
    dashboard.config.version = version.__version__
    dashboard.config.brand_name = 'SampleDB Monitoring Dashboard'
    dashboard.config.title_name = 'SampleDB Monitoring Dashboard'
    dashboard.config.description = 'Automatically monitor the evolving performance of SampleDB'
    dashboard.config.show_login_banner = False
    dashboard.config.show_login_footer = False
    dashboard.config.table_prefix = 'dashboard_'
    dashboard.config.security_token = secrets.token_hex(32)
    dashboard.config.password = secrets.token_hex(32)
    dashboard.config.group_by = _get_current_user_id
    dashboard.config.get_ip = _get_ip
    dashboard.config.database_name = app.config['MONITORINGDASHBOARD_DATABASE']
    dashboard.bind(app)
