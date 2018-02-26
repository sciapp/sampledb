# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, FieldList, FormField
from wtforms.validators import Length, InputRequired

from ..logic.permissions import Permissions


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


class ProjectUserPermissionsForm(FlaskForm):
    user_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ProjectGroupPermissionsForm(FlaskForm):
    group_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ProjectPermissionsForm(FlaskForm):
    user_permissions = FieldList(FormField(ProjectUserPermissionsForm), min_entries=0)
    group_permissions = FieldList(FormField(ProjectGroupPermissionsForm), min_entries=0)
