# coding: utf-8
"""

"""

from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, SelectField, IntegerField, TextAreaField
from wtforms.validators import InputRequired

from ..logic.permissions import Permissions


class ObjectUserPermissionsForm(FlaskForm):
    user_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ObjectGroupPermissionsForm(FlaskForm):
    group_id = IntegerField(
        validators=[InputRequired()]
    )
    permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ, Permissions.WRITE, Permissions.GRANT)],
        validators=[InputRequired()]
    )


class ObjectPermissionsForm(FlaskForm):
    public_permissions = SelectField(
        choices=[(p.name.lower(), p.name.lower()) for p in (Permissions.NONE, Permissions.READ)],
        validators=[InputRequired()]
    )
    user_permissions = FieldList(FormField(ObjectUserPermissionsForm), min_entries=0)
    group_permissions = FieldList(FormField(ObjectGroupPermissionsForm), min_entries=0)


class ObjectForm(FlaskForm):
    pass


class ObjectVersionRestoreForm(FlaskForm):
    pass


class CommentForm(FlaskForm):
    content = TextAreaField(validators=[InputRequired()])
