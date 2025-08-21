import typing
from http import HTTPStatus

import flask
import flask_login
import wtforms
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, SelectMultipleField
from wtforms.fields.numeric import IntegerField
from wtforms.validators import InputRequired, AnyOf, ValidationError

from .. import frontend
from ...utils import FlaskResponseT
from ...logic import errors
from ...logic.topics import get_topics
from ...logic.action_permissions import get_sorted_actions_for_user
from ...logic.automatic_schema_updates import get_updatable_objects_checks, get_updatable_objects_check, start_updatable_objects_checks, get_automatic_schema_updates, start_automatic_schema_updates
from ...logic.objects import get_max_object_id
from ...logic.object_permissions import get_objects_with_permissions
from ...models import UpdatableObjectsCheckStatus, AutomaticSchemaUpdateStatus, Permissions


class CheckForUpdatableObjectsForm(FlaskForm):
    action_ids = SelectMultipleField()
    submit = StringField(validators=[InputRequired(), AnyOf(['check_for_updatable_objects_form'])])


class StartSchemaUpdatesForm(FlaskForm):
    updatable_objects_check_id = IntegerField(validators=[InputRequired()])
    object_ids = SelectMultipleField()
    submit = StringField(validators=[InputRequired(), AnyOf(['start_schema_updates_form'])])

    def validate_updatable_objects_check_id(self, field: wtforms.IntegerField) -> None:
        updatable_objects_check_id = field.data
        try:
            get_updatable_objects_check(updatable_objects_check_id=updatable_objects_check_id)
        except errors.UpdatableObjectsCheckDoesNotExistError:
            raise ValidationError('Invalid updatable_objects_check_id')


@frontend.route('/admin/automatic_schema_updates/', methods=['GET', 'POST'])
@flask_login.login_required
def automatic_schema_updates() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(HTTPStatus.FORBIDDEN)
    updatable_objects_checks = get_updatable_objects_checks()
    automatic_schema_updates = get_automatic_schema_updates()

    checking_in_progress = any(
        updatable_objects_check.status != UpdatableObjectsCheckStatus.DONE
        for updatable_objects_check in updatable_objects_checks
    )
    update_in_progress = any(
        automatic_schema_update.status != AutomaticSchemaUpdateStatus.DONE
        for automatic_schema_update in automatic_schema_updates
    )

    all_actions = None
    sorted_action_topics = None
    if update_in_progress or checking_in_progress or flask_login.current_user.is_readonly:
        check_for_updatable_objects_form = None
    else:
        check_for_updatable_objects_form = CheckForUpdatableObjectsForm()

        all_actions = get_sorted_actions_for_user(
            user_id=flask_login.current_user.id
        )
        check_for_updatable_objects_form.action_ids.choices = [
            (str(action.id), str(action.id))
            for action in all_actions
        ]
        sorted_action_topics = []
        if not flask.current_app.config['DISABLE_TOPICS']:
            sorted_topics = get_topics()
            for topic in sorted_topics:
                for action in all_actions:
                    if topic in action.topics:
                        sorted_action_topics.append(topic)
                        break

        if check_for_updatable_objects_form.validate_on_submit():
            try:
                filter_action_ids: typing.Optional[typing.List[int]] = [
                    int(action_id)
                    for action_id in check_for_updatable_objects_form.action_ids.data
                ]
            except ValueError:
                flask.flash(_('Invalid action ID.'), 'error')
                return flask.redirect(flask.url_for('.automatic_schema_updates'))
            if not filter_action_ids:
                filter_action_ids = None
            try:
                start_updatable_objects_checks(flask_login.current_user.id, filter_action_ids)
                flask.flash(_('An updatable objects check has been started. Please refresh this page in a few minutes.'), 'success')
            except errors.UpdatableObjectsCheckAlreadyInProgressError:
                flask.flash(_('Another updatable objects check is already in progress.'), 'error')
            return flask.redirect(flask.url_for('.automatic_schema_updates'))

    start_schema_updates_form = None
    updatable_objects_by_id = {}
    if not checking_in_progress and not update_in_progress and updatable_objects_checks:
        latest_updatable_objects_check = updatable_objects_checks[0]
        if latest_updatable_objects_check.result and not latest_updatable_objects_check.automatic_schema_update:
            updatable_object_ids = {
                object_id
                for object_id, version_id, messages in latest_updatable_objects_check.result.get('automatically_updatable_objects', [])
            }.union({
                object_id
                for object_id, version_id, messages in latest_updatable_objects_check.result.get('manually_updatable_objects', [])
            })
            updatable_objects = get_objects_with_permissions(
                user_id=flask_login.current_user.id,
                permissions=Permissions.GRANT,
                object_ids=list(updatable_object_ids),
                name_only=True
            )
            updatable_objects_by_id = {
                updatable_object.object_id: updatable_object
                for updatable_object in updatable_objects
            }
            start_schema_updates_form = StartSchemaUpdatesForm()
            start_schema_updates_form.object_ids.choices = [
                (str(object_id), str(object_id))
                for object_id in updatable_objects_by_id
            ]
            if start_schema_updates_form.validate_on_submit():
                object_ids_to_update = {
                    int(object_id_str)
                    for object_id_str in start_schema_updates_form.object_ids.data
                }
                start_automatic_schema_updates(
                    updatable_objects_check_id=start_schema_updates_form.updatable_objects_check_id.data,
                    user_id=flask_login.current_user.id,
                    object_ids=list(object_ids_to_update)
                )
                flask.flash(_('An automatic schema update has been started. Please refresh this page in a few minutes.'), 'success')
                return flask.redirect(flask.url_for('.automatic_schema_updates'))
            if updatable_object_ids != set(updatable_objects_by_id.keys()) and not flask_login.current_user.has_admin_permissions:
                flask.flash(_('Without enabling the setting "Use Admin Permissions" in your preferences, you will not be able to update all updatable objects.'), 'warning')

    max_object_id = get_max_object_id()
    return flask.render_template(
        'admin/automatic_schema_updates.html',
        checking_in_progress=checking_in_progress,
        update_in_progress=update_in_progress,
        check_for_updatable_objects_form=check_for_updatable_objects_form,
        updatable_object_checks=updatable_objects_checks,
        max_object_id=max_object_id,
        UpdatableObjectsCheckStatus=UpdatableObjectsCheckStatus,
        updatable_objects_by_id=updatable_objects_by_id,
        start_schema_updates_form=start_schema_updates_form,
        automatic_schema_updates=automatic_schema_updates,
        AutomaticSchemaUpdateStatus=AutomaticSchemaUpdateStatus,
        all_actions=all_actions,
        sorted_action_topics=sorted_action_topics,
        current_status={
            'updatable_objects_checks': {
                updatable_objects_check.id: updatable_objects_check.status == UpdatableObjectsCheckStatus.DONE
                for updatable_objects_check in updatable_objects_checks
            },
            'automatic_schema_updates': {
                automatic_schema_update.id: automatic_schema_update.status == AutomaticSchemaUpdateStatus.DONE
                for automatic_schema_update in automatic_schema_updates
            }
        }
    )


@frontend.route('/admin/automatic_schema_updates/status', methods=['GET', 'POST'])
@flask_login.login_required
def automatic_schema_updates_status() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(HTTPStatus.FORBIDDEN)
    updatable_objects_checks = get_updatable_objects_checks()
    automatic_schema_updates = get_automatic_schema_updates()
    return flask.jsonify({
        'updatable_objects_checks': {
            updatable_objects_check.id: updatable_objects_check.status == UpdatableObjectsCheckStatus.DONE
            for updatable_objects_check in updatable_objects_checks
        },
        'automatic_schema_updates': {
            automatic_schema_update.id: automatic_schema_update.status == AutomaticSchemaUpdateStatus.DONE
            for automatic_schema_update in automatic_schema_updates
        }
    })
