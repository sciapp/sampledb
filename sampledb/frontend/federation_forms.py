# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import Length, DataRequired


class CreateAPITokenForm(FlaskForm):
    description = StringField('description', validators=[Length(min=1, max=100)])


class AddOwnAPITokenForm(FlaskForm):
    token = StringField('token', validators=[Length(min=1, max=100)])
    description = StringField('description', validators=[Length(min=1, max=100)])


class AuthenticationMethodForm(FlaskForm):
    id = IntegerField('Authentication_method_id', validators=[DataRequired()])
    submit = SubmitField('Remove')


class AddComponentForm(FlaskForm):
    address = StringField(validators=[Length(min=0, max=100)])
    uuid = StringField(validators=[Length(min=1, max=100)])
    name = StringField(validators=[Length(min=0, max=100)])
    description = StringField()


class EditComponentForm(FlaskForm):
    address = StringField(validators=[Length(min=0, max=100)])
    name = StringField(validators=[Length(min=0, max=100)])
    description = StringField()


class SyncComponentForm(FlaskForm):
    pass
