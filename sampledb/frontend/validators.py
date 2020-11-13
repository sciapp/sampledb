from wtforms.validators import ValidationError

import flask
import flask_login

from ..models import Permissions
from ..logic.object_permissions import get_user_object_permissions


def ObjectIdValidator(required_perm: Permissions, allow_self: bool = False):
    def validate(form, field):
        user_id = flask_login.current_user.id
        object_id = field.data

        try:
            object_id = int(object_id)
        except ValueError:
            raise ValidationError("Object_id is not an int.")

        if "object_id" in flask.request.view_args and not allow_self:
            if object_id == flask.request.view_args["object_id"]:
                raise ValidationError("You can not select the same object.")

        perm = get_user_object_permissions(object_id=object_id, user_id=user_id)
        if required_perm > perm:
            raise ValidationError("No such object or no access to object")

    return validate


def MultipleObjectIdValidator(required_perm: Permissions, allow_self: bool = False):
    def validate(form, field):
        user_id = flask_login.current_user.id
        object_ids = field.data
        for object_id in object_ids:
            try:
                object_id = int(object_id)
            except ValueError:
                raise ValidationError("Object_id is not an int.")

            if "object_id" in flask.request.view_args and not allow_self:
                if object_id == flask.request.view_args["object_id"]:
                    raise ValidationError("You can not select the same object.")

            perm = get_user_object_permissions(object_id=object_id, user_id=user_id)
            if required_perm > perm:
                raise ValidationError("No such object or no access to object")

    return validate
