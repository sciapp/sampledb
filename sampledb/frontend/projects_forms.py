# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField
from wtforms.validators import Length, InputRequired


class CreateProjectForm(FlaskForm):
    name = StringField(validators=[Length(min=1, max=100)])
    description = StringField()


class EditProjectForm(FlaskForm):
    name = StringField(validators=[Length(min=1, max=100)])
    description = StringField()


class LeaveProjectForm(FlaskForm):
    pass


class InviteUserToProjectForm(FlaskForm):
    user_id = IntegerField(validators=[InputRequired()])


class InviteGroupToProjectForm(FlaskForm):
    group_id = IntegerField(validators=[InputRequired()])
