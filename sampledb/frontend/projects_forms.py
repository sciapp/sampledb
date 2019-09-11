# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, FieldList, FormField, BooleanField
from wtforms.validators import Length, InputRequired

from ..logic.object_permissions import Permissions


class CreateProjectForm(FlaskForm):
    name = StringField(validators=[Length(min=1, max=100)])
    description = StringField()


class EditProjectForm(FlaskForm):
    name = StringField(validators=[Length(min=1, max=100)])
    description = StringField()


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


class AddSubprojectForm(FlaskForm):
    child_project_id = IntegerField(validators=[InputRequired()])
    child_can_add_users_to_parent = BooleanField(default=False)


class RemoveSubprojectForm(FlaskForm):
    child_project_id = IntegerField(validators=[InputRequired()])
