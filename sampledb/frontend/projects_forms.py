# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FieldList, FormField, BooleanField, SelectMultipleField
from wtforms.validators import InputRequired, NumberRange, DataRequired

from ..models import Permissions


class CreateProjectForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])
    categories = SelectMultipleField()


class EditProjectForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])
    categories = SelectMultipleField()


class LeaveProjectForm(FlaskForm):
    pass


class DeleteProjectForm(FlaskForm):
    pass


class RemoveProjectMemberForm(FlaskForm):
    pass


class RemoveProjectGroupForm(FlaskForm):
    pass


class OtherProjectIdForm(FlaskForm):
    project_id = IntegerField(
        validators=[InputRequired()]
    )
    add_user = BooleanField(default=False)


class InviteUserToProjectForm(FlaskForm):
    user_id = IntegerField(validators=[InputRequired()])
    other_project_ids = FieldList(FormField(OtherProjectIdForm), min_entries=0)
    permissions = IntegerField(validators=[InputRequired(), NumberRange(min=Permissions.READ.value, max=Permissions.GRANT.value)])
    add_directly = BooleanField(default=False)


class InviteGroupToProjectForm(FlaskForm):
    group_id = IntegerField(validators=[InputRequired()])


class AddSubprojectForm(FlaskForm):
    child_project_id = IntegerField(validators=[InputRequired()])
    child_can_add_users_to_parent = BooleanField(default=False)


class RemoveSubprojectForm(FlaskForm):
    child_project_id = IntegerField(validators=[InputRequired()])


class ObjectLinkForm(FlaskForm):
    object_id = IntegerField(validators=[InputRequired()])
