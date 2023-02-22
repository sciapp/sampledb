# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FieldList, FormField, BooleanField, SelectMultipleField
from wtforms.validators import InputRequired, NumberRange, DataRequired

from ..models import Permissions


class CreateProjectForm(FlaskForm):  # type: ignore[misc]
    translations = StringField(validators=[DataRequired()])
    categories = SelectMultipleField()


class EditProjectForm(FlaskForm):  # type: ignore[misc]
    translations = StringField(validators=[DataRequired()])
    categories = SelectMultipleField()


class LeaveProjectForm(FlaskForm):  # type: ignore[misc]
    pass


class DeleteProjectForm(FlaskForm):  # type: ignore[misc]
    pass


class RemoveProjectMemberForm(FlaskForm):  # type: ignore[misc]
    pass


class RemoveProjectGroupForm(FlaskForm):  # type: ignore[misc]
    pass


class OtherProjectIdForm(FlaskForm):  # type: ignore[misc]
    project_id = IntegerField(
        validators=[InputRequired()]
    )
    add_user = BooleanField(default=False)


class InviteUserToProjectForm(FlaskForm):  # type: ignore[misc]
    user_id = IntegerField(validators=[InputRequired()])
    other_project_ids = FieldList(FormField(OtherProjectIdForm), min_entries=0)
    permissions = IntegerField(validators=[InputRequired(), NumberRange(min=Permissions.READ.value, max=Permissions.GRANT.value)])


class InviteGroupToProjectForm(FlaskForm):  # type: ignore[misc]
    group_id = IntegerField(validators=[InputRequired()])


class AddSubprojectForm(FlaskForm):  # type: ignore[misc]
    child_project_id = IntegerField(validators=[InputRequired()])
    child_can_add_users_to_parent = BooleanField(default=False)


class RemoveSubprojectForm(FlaskForm):  # type: ignore[misc]
    child_project_id = IntegerField(validators=[InputRequired()])


class ObjectLinkForm(FlaskForm):  # type: ignore[misc]
    object_id = IntegerField(validators=[InputRequired()])
