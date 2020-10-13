# coding: utf-8
"""

"""

import flask
import flask_login
from flask_wtf import FlaskForm
from wtforms.fields import StringField, BooleanField
from wtforms.validators import InputRequired

from . import frontend
from .. import logic
from .utils import check_current_user_is_not_readonly

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/action_types/')
@flask_login.login_required
def action_types():
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    return flask.render_template(
        'action_types/action_types.html',
        action_types=logic.actions.get_action_types()
    )


@frontend.route('/action_types/<int(signed=True):type_id>', methods=['GET', 'POST'])
@flask_login.login_required
def action_type(type_id):
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    if flask.request.args.get('mode') == 'edit':
        return show_action_type_form(type_id)
    try:
        action_type = logic.actions.get_action_type(type_id)
    except logic.errors.ActionTypeDoesNotExistError:
        return flask.abort(404)
    return flask.render_template(
        'action_types/action_type.html',
        action_type=action_type
    )


@frontend.route('/action_types/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_action_type():
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    return show_action_type_form(None)


class ActionTypeForm(FlaskForm):
    name = StringField(validators=[InputRequired()])
    description = StringField()
    object_name = StringField(validators=[InputRequired()])
    object_name_plural = StringField(validators=[InputRequired()])
    view_text = StringField(validators=[InputRequired()])
    perform_text = StringField(validators=[InputRequired()])
    admin_only = BooleanField()
    show_on_frontpage = BooleanField()
    show_in_navbar = BooleanField()
    enable_labels = BooleanField()
    enable_files = BooleanField()
    enable_locations = BooleanField()
    enable_publications = BooleanField()
    enable_comments = BooleanField()
    enable_activity_log = BooleanField()
    enable_related_objects = BooleanField()


def show_action_type_form(type_id):
    check_current_user_is_not_readonly()

    action_type_form = ActionTypeForm()

    if type_id is not None:
        try:
            action_type = logic.actions.get_action_type(type_id)
        except logic.errors.ActionTypeDoesNotExistError:
            return flask.abort(404)
        if 'action_submit' not in flask.request.form:
            action_type_form.name.data = action_type.name
            action_type_form.description.data = action_type.description
            action_type_form.object_name.data = action_type.object_name
            action_type_form.object_name_plural.data = action_type.object_name_plural
            action_type_form.view_text.data = action_type.view_text
            action_type_form.perform_text.data = action_type.perform_text
            action_type_form.admin_only.data = action_type.admin_only
            action_type_form.show_on_frontpage.data = action_type.show_on_frontpage
            action_type_form.show_in_navbar.data = action_type.show_in_navbar
            action_type_form.enable_labels.data = action_type.enable_labels
            action_type_form.enable_files.data = action_type.enable_files
            action_type_form.enable_locations.data = action_type.enable_locations
            action_type_form.enable_publications.data = action_type.enable_publications
            action_type_form.enable_comments.data = action_type.enable_comments
            action_type_form.enable_activity_log.data = action_type.enable_activity_log
            action_type_form.enable_related_objects.data = action_type.enable_related_objects

    if action_type_form.validate_on_submit():
        if type_id is None:
            action_type = logic.actions.create_action_type(
                name=action_type_form.name.data.strip(),
                description=action_type_form.description.data.strip(),
                object_name=action_type_form.object_name.data.strip(),
                object_name_plural=action_type_form.object_name_plural.data.strip(),
                view_text=action_type_form.view_text.data.strip(),
                perform_text=action_type_form.perform_text.data.strip(),
                admin_only=action_type_form.admin_only.data,
                show_on_frontpage=action_type_form.show_on_frontpage.data,
                show_in_navbar=action_type_form.show_in_navbar.data,
                enable_labels=action_type_form.enable_labels.data,
                enable_files=action_type_form.enable_files.data,
                enable_locations=action_type_form.enable_locations.data,
                enable_publications=action_type_form.enable_publications.data,
                enable_comments=action_type_form.enable_comments.data,
                enable_activity_log=action_type_form.enable_activity_log.data,
                enable_related_objects=action_type_form.enable_related_objects.data

            )
        else:
            action_type = logic.actions.update_action_type(
                action_type_id=type_id,
                name=action_type_form.name.data,
                description=action_type_form.description.data,
                object_name=action_type_form.object_name.data,
                object_name_plural=action_type_form.object_name_plural.data,
                view_text=action_type_form.view_text.data,
                perform_text=action_type_form.perform_text.data,
                admin_only=action_type_form.admin_only.data,
                show_on_frontpage=action_type_form.show_on_frontpage.data,
                show_in_navbar=action_type_form.show_in_navbar.data,
                enable_labels=action_type_form.enable_labels.data,
                enable_files=action_type_form.enable_files.data,
                enable_locations=action_type_form.enable_locations.data,
                enable_publications=action_type_form.enable_publications.data,
                enable_comments=action_type_form.enable_comments.data,
                enable_activity_log=action_type_form.enable_activity_log.data,
                enable_related_objects=action_type_form.enable_related_objects.data
            )
        return flask.redirect(flask.url_for('.action_type', type_id=action_type.id))

    return flask.render_template(
        'action_types/action_type_form.html',
        action_type_form=action_type_form,
        submit_text='Create' if type_id is None else 'Save'
    )
