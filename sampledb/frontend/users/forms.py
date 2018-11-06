# coding: utf-8
"""

"""


from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField
from wtforms.validators import InputRequired, Length


class EditGroupForm(FlaskForm):
    name = StringField(validators=[Length(min=1, max=100)])
    description = StringField()


class CreateGroupForm(FlaskForm):
    name = StringField(validators=[Length(min=1, max=100)])
    description = StringField()


class LeaveGroupForm(FlaskForm):
    pass


class InviteUserForm(FlaskForm):
    user_id = IntegerField(validators=[InputRequired()])


class ToggleFavoriteActionForm(FlaskForm):
    action_id = IntegerField(validators=[InputRequired()])


class ToggleFavoriteInstrumentForm(FlaskForm):
    instrument_id = IntegerField(validators=[InputRequired()])
