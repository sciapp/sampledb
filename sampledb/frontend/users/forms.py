# coding: utf-8
"""

"""


from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectMultipleField
from wtforms.validators import InputRequired, Length, DataRequired


class EditGroupForm(FlaskForm):  # type: ignore[misc]
    translations = StringField(validators=[DataRequired()])
    categories = SelectMultipleField()


class CreateGroupForm(FlaskForm):  # type: ignore[misc]
    translations = StringField(validators=[DataRequired()])
    categories = SelectMultipleField()


class LeaveGroupForm(FlaskForm):  # type: ignore[misc]
    pass


class DeleteGroupForm(FlaskForm):  # type: ignore[misc]
    pass


class RemoveGroupMemberForm(FlaskForm):  # type: ignore[misc]
    pass


class InviteUserForm(FlaskForm):  # type: ignore[misc]
    user_id = IntegerField(validators=[InputRequired()])


class ToggleFavoriteActionForm(FlaskForm):  # type: ignore[misc]
    action_id = IntegerField(validators=[InputRequired()])


class ToggleFavoriteInstrumentForm(FlaskForm):  # type: ignore[misc]
    instrument_id = IntegerField(validators=[InputRequired()])


class NotificationModeForm(FlaskForm):  # type: ignore[misc]
    pass


class OtherSettingsForm(FlaskForm):  # type: ignore[misc]
    pass


class CreateAPITokenForm(FlaskForm):  # type: ignore[misc]
    description = StringField('description', validators=[Length(min=1, max=100)])


class ManageTwoFactorAuthenticationMethodForm(FlaskForm):  # type: ignore[misc]
    method_id = IntegerField(validators=[InputRequired()])
    action = StringField(validators=[InputRequired()])
