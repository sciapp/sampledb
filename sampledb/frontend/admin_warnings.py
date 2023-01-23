
from http import HTTPStatus

import flask
import flask_login

from . import frontend
from ..logic.utils import show_load_objects_in_background_warning, show_admin_local_storage_warning, show_numeric_tags_warning, do_numeric_tags_exist


@frontend.route('/admin/warnings/')
@flask_login.login_required
def admin_warnings():
    if not flask_login.current_user.is_admin:
        return flask.abort(HTTPStatus.FORBIDDEN)
    warnings = {}
    for deprecation_warning_check in [
        show_load_objects_in_background_warning,
        show_admin_local_storage_warning,
        show_numeric_tags_warning,
    ]:
        warnings[deprecation_warning_check.__name__] = deprecation_warning_check()

    has_warnings = any(warnings.values())
    return flask.render_template(
        'admin/warnings.html',
        has_warnings=has_warnings,
        do_numeric_tags_exist=do_numeric_tags_exist() if show_numeric_tags_warning() else False,
        **warnings
    )
