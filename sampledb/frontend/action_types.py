# coding: utf-8
"""

"""

import flask
import flask_login
import json
from flask_wtf import FlaskForm
from wtforms.fields import StringField, BooleanField
from wtforms.validators import DataRequired
from flask_babel import _

from . import frontend
from .. import logic
from .utils import check_current_user_is_not_readonly

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/action_types/')
@flask_login.login_required
def action_types():
    if not flask_login.current_user.is_admin:
        return flask.abort(403)

    user_language_id = logic.languages.get_user_language(flask_login.current_user).id
    action_types_with_translations = logic.action_type_translations.get_action_types_with_translations_in_language(user_language_id)
    return flask.render_template(
        'action_types/action_types.html',
        action_types=action_types_with_translations,
    )


@frontend.route('/action_types/<int(signed=True):type_id>', methods=['GET', 'POST'])
@flask_login.login_required
def action_type(type_id):
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    if flask.request.args.get('mode') == 'edit':
        return show_action_type_form(type_id)

    try:
        action_type = logic.action_type_translations.get_action_type_with_translation_in_language(
            action_type_id=type_id,
            language_id=logic.languages.get_user_language(flask_login.current_user).id
        )
    except logic.errors.ActionTypeDoesNotExistError:
        return flask.abort(404)

    try:
        translations = logic.action_type_translations.get_action_type_translations_for_action_type(action_type.id)
    except logic.errors.ActionTypeTranslationDoesNotExistError:
        return flask.abort(404)

    return flask.render_template(
        'action_types/action_type.html',
        action_type=action_type,
        translations=translations,
    )


@frontend.route('/action_types/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_action_type():
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    return show_action_type_form(None)


class ActionTypeForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])

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
    enable_project_link = BooleanField()


def show_action_type_form(type_id):
    check_current_user_is_not_readonly()
    action_type_translations = []
    action_type_language_ids = []
    action_type_form = ActionTypeForm()

    english = logic.languages.get_language(logic.languages.Language.ENGLISH)

    def validate_string(string):
        try:
            if len(string) > 0 and len(string) < 100:
                return True
            else:
                return False
        except Exception:
            return False

    def validate_strings(strings):
        try:
            result = [validate_string(string) for string in strings]
            for temp in result:
                if temp is False:
                    return False
        except Exception:
            return False

        return True

    if type_id is not None:
        try:
            action_type = logic.actions.get_action_type(type_id)
        except logic.errors.ActionTypeDoesNotExistError:
            return flask.abort(404)
        if 'action_submit' not in flask.request.form:
            action_type_translations = logic.action_type_translations.get_action_type_translations_for_action_type(action_type.id)
            action_type_language_ids = [translation.language_id for translation in action_type_translations]
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
            action_type_form.enable_project_link.data = action_type.enable_project_link

    if action_type_form.validate_on_submit():
        if type_id is None:

            try:
                translation_data = json.loads(action_type_form.translations.data)
            except Exception:
                pass
            else:
                translation_keys = {'language_id', 'name', 'description',
                                    'object_name', 'object_name_plural', 'view_text', 'perform_text'}
                if not isinstance(translation_data, list):
                    translation_data = ()
                for translation in translation_data:
                    if not isinstance(translation, dict):
                        flask.flash(_('Please fill out the form.'), 'error')
                        return show_action_type_form(type_id)

                    if set(translation.keys()) != translation_keys:
                        flask.flash(_('Please fill out the form.'), 'error')
                        return show_action_type_form(type_id)

                    language_id = int(translation['language_id'])
                    name = translation['name'].strip()
                    description = translation['description'].strip()
                    object_name = translation['object_name'].strip()
                    object_name_plural = translation['object_name_plural'].strip()
                    view_text = translation['view_text'].strip()
                    perform_text = translation['perform_text'].strip()

                    if not validate_strings([name, object_name, object_name_plural, view_text, perform_text]):
                        flask.flash(_('The fields for name, object name (singular and plural), view text and perform text are required.'))
                        return flask.render_template(
                            'action_types/action_type_form.html',
                            action_type_form=action_type_form,
                            action_type_translations=action_type_translations,
                            languages=logic.languages.get_languages(),
                            ENGLISH=english,
                            submit_text=_('Create') if type_id is None else _('Save')
                        )

                action_type = logic.actions.create_action_type(
                    admin_only=action_type_form.admin_only.data,
                    show_on_frontpage=action_type_form.show_on_frontpage.data,
                    show_in_navbar=action_type_form.show_in_navbar.data,
                    enable_labels=action_type_form.enable_labels.data,
                    enable_files=action_type_form.enable_files.data,
                    enable_locations=action_type_form.enable_locations.data,
                    enable_publications=action_type_form.enable_publications.data,
                    enable_comments=action_type_form.enable_comments.data,
                    enable_activity_log=action_type_form.enable_activity_log.data,
                    enable_related_objects=action_type_form.enable_related_objects.data,
                    enable_project_link=action_type_form.enable_project_link.data
                )

                for translation in translation_data:

                    language_id = int(translation['language_id'])
                    name = translation['name'].strip()
                    description = translation['description'].strip()
                    object_name = translation['object_name'].strip()
                    object_name_plural = translation['object_name_plural'].strip()
                    view_text = translation['view_text'].strip()
                    perform_text = translation['perform_text'].strip()

                    logic.action_type_translations.set_action_type_translation(
                        action_type_id=action_type.id,
                        language_id=language_id,
                        name=name,
                        description=description,
                        object_name=object_name,
                        object_name_plural=object_name_plural,
                        view_text=view_text,
                        perform_text=perform_text
                    )

        else:
            action_type = logic.actions.update_action_type(
                action_type_id=type_id,
                admin_only=action_type_form.admin_only.data,
                show_on_frontpage=action_type_form.show_on_frontpage.data,
                show_in_navbar=action_type_form.show_in_navbar.data,
                enable_labels=action_type_form.enable_labels.data,
                enable_files=action_type_form.enable_files.data,
                enable_locations=action_type_form.enable_locations.data,
                enable_publications=action_type_form.enable_publications.data,
                enable_comments=action_type_form.enable_comments.data,
                enable_activity_log=action_type_form.enable_activity_log.data,
                enable_related_objects=action_type_form.enable_related_objects.data,
                enable_project_link=action_type_form.enable_project_link.data
            )

            try:
                translation_data = json.loads(action_type_form.translations.data)
            except Exception:
                pass
            else:
                translation_keys = {'language_id', 'name', 'description',
                                    'object_name', 'object_name_plural', 'view_text', 'perform_text'}
                if not isinstance(translation_data, list):
                    translation_data = ()

                valid_translations = set()
                for translation in translation_data:
                    if not isinstance(translation, dict):
                        continue
                    if set(translation.keys()) != translation_keys:
                        continue

                    language_id = int(translation['language_id'])
                    name = translation['name'].strip()
                    description = translation['description'].strip()
                    object_name = translation['object_name'].strip()
                    object_name_plural = translation['object_name_plural'].strip()
                    view_text = translation['view_text'].strip()
                    perform_text = translation['perform_text'].strip()

                    if not validate_strings([name, object_name, object_name_plural, view_text, perform_text]):
                        flask.flash(_('The fields for name, object name (singular and plural), view text and perform text are required.'))
                        return flask.render_template(
                            'action_types/action_type_form.html',
                            action_type_form=action_type_form,
                            action_type_translations=action_type_translations,
                            action_type_language_ids=action_type_language_ids,
                            languages=logic.languages.get_languages(),
                            ENGLISH=english,
                            submit_text=_('Create') if type_id is None else _('Save')
                        )

                    translation = logic.action_type_translations.set_action_type_translation(
                        action_type_id=action_type.id,
                        language_id=language_id,
                        name=name,
                        description=description,
                        object_name=object_name,
                        object_name_plural=object_name_plural,
                        view_text=view_text,
                        perform_text=perform_text)
                    valid_translations.add((translation.language_id, translation.action_type_id))
                # delete translations:
                for existing_translation in logic.action_type_translations.get_action_type_translations_for_action_type(action_type.id):
                    if (existing_translation.language_id, existing_translation.action_type_id) not in valid_translations:
                        logic.action_type_translations.delete_action_type_translation(
                            language_id=existing_translation.language_id,
                            action_type_id=existing_translation.action_type_id
                        )

        return flask.redirect(flask.url_for('.action_type', type_id=action_type.id))

    return flask.render_template(
        'action_types/action_type_form.html',
        action_type_form=action_type_form,
        action_type_translations=action_type_translations,
        action_type_language_ids=action_type_language_ids,
        languages=logic.languages.get_languages(),
        ENGLISH=english,
        submit_text=_('Create') if type_id is None else _('Save')
    )
