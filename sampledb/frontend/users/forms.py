# coding: utf-8
"""

"""


from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectMultipleField, HiddenField, BooleanField
from wtforms.validators import InputRequired, Length, DataRequired


class EditGroupForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])
    categories = SelectMultipleField()


class CreateGroupForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])
    categories = SelectMultipleField()


class LeaveGroupForm(FlaskForm):
    pass


class DeleteGroupForm(FlaskForm):
    pass


class RemoveGroupMemberForm(FlaskForm):
    pass


class InviteUserForm(FlaskForm):
    user_id = IntegerField(validators=[InputRequired()])
    add_directly = BooleanField(default=False)


class ToggleFavoriteActionForm(FlaskForm):
    action_id = IntegerField(validators=[InputRequired()])


class ToggleFavoriteInstrumentForm(FlaskForm):
    instrument_id = IntegerField(validators=[InputRequired()])


class NotificationModeForm(FlaskForm):
    pass


class OtherSettingsForm(FlaskForm):
    pass


class CreateAPITokenForm(FlaskForm):
    description = StringField('description', validators=[Length(min=1, max=100)])


class ManageTwoFactorAuthenticationMethodForm(FlaskForm):
    method_id = IntegerField(validators=[InputRequired()])
    action = StringField(validators=[InputRequired()])


class AddWebhookForm(FlaskForm):
    name = StringField(validators=[Length(min=0, max=100)])
    address = StringField(validators=[Length(min=1, max=100)])


class RemoveWebhookForm(FlaskForm):
    id = IntegerField('Authentication_method_id', validators=[DataRequired()])


class WebAuthnLoginForm(FlaskForm):
    assertion = HiddenField(validators=[DataRequired()])
    remember_me = BooleanField()
    shared_device = BooleanField()
