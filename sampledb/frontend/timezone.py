# coding: utf-8
"""

"""
import flask_login
import flask_wtf
import wtforms.fields
import wtforms.validators
import pytz

from . import frontend
from ..logic import settings
from ..utils import FlaskResponseT


class TimezoneForm(flask_wtf.FlaskForm):
    timezone = wtforms.fields.StringField(
        validators=[
            wtforms.validators.InputRequired()
        ]
    )

    def validate_timezone(self, field: wtforms.fields.StringField) -> None:
        try:
            pytz.timezone(field.data)
        except Exception:
            raise wtforms.validators.ValidationError("unknown time zone")


@frontend.route('/set-timezone', methods=["POST"])
@flask_login.login_required
def set_timezone() -> FlaskResponseT:
    if not settings.get_user_setting(flask_login.current_user.id, 'AUTO_TZ'):
        return '', 200
    form = TimezoneForm()
    if form.validate_on_submit():
        settings.set_user_settings(flask_login.current_user.id, {
            'TIMEZONE': form.timezone.data
        })
        return '', 200
    return '', 400
