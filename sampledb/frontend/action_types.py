# coding: utf-8
"""

"""
import json
import typing

import flask
import flask_login
from flask_wtf import FlaskForm
from wtforms.fields import StringField, BooleanField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, ValidationError
from flask_babel import _

from . import frontend
from .. import logic
from .utils import check_current_user_is_not_readonly
from ..utils import FlaskResponseT
from ..logic.utils import get_translated_text
from ..logic.components import get_component_or_none
from ..models import SciCatExportType


class ActionTypesSortingForm(FlaskForm):
    encoded_order = StringField("Order-String", [DataRequired()])

    def validate_encoded_order(form, field: StringField) -> None:
        valid_action_type_ids = [action_type.id for action_type in logic.action_types.get_action_types()]

        try:
            split_string = field.data.split(",")
            sorted_action_type_ids = list(map(int, split_string))
            for action_type_id in sorted_action_type_ids:
                if action_type_id not in valid_action_type_ids:
                    raise ValidationError(f"{action_type_id} is not a valid id")
        except ValueError:
            raise ValidationError("Invalid IDs.")

        field.data = sorted_action_type_ids


@frontend.route('/action_types/', methods=['GET', 'POST'])
@flask_login.login_required
def action_types() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(403)

    sorting_form = ActionTypesSortingForm()

    if sorting_form.validate_on_submit():
        check_current_user_is_not_readonly()

        logic.action_types.set_action_types_order(sorting_form.encoded_order.data)

    return flask.render_template(
        'action_types/action_types.html',
        action_types=logic.action_types.get_action_types(),
        sorting_form=sorting_form
    )


@frontend.route('/action_types/<int(signed=True):type_id>', methods=['GET', 'POST'])
@flask_login.login_required
def action_type(type_id: int) -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(403)

    try:
        action_type = logic.action_types.get_action_type(
            action_type_id=type_id
        )
    except logic.errors.ActionTypeDoesNotExistError:
        return flask.abort(404)

    if flask.request.args.get('mode') == 'edit':
        if action_type.fed_id is not None:
            flask.flash(_('Editing imported action types is not yet supported.'), 'error')
            return flask.abort(403)
        else:
            return show_action_type_form(type_id)

    try:
        translations = logic.action_type_translations.get_action_type_translations_for_action_type(action_type.id)
    except logic.errors.ActionTypeTranslationDoesNotExistError:
        return flask.abort(404)

    return flask.render_template(
        'action_types/action_type.html',
        action_type=action_type,
        translations=translations,
        component=get_component_or_none(action_type.component_id)
    )


@frontend.route('/action_types/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_action_type() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    return show_action_type_form(None)


class ActionTypeForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])

    admin_only = BooleanField()
    show_on_frontpage = BooleanField()
    show_in_navbar = BooleanField()
    show_in_object_filters = BooleanField()
    enable_labels = BooleanField()
    enable_files = BooleanField()
    enable_locations = BooleanField()
    enable_publications = BooleanField()
    enable_comments = BooleanField()
    enable_activity_log = BooleanField()
    enable_related_objects = BooleanField()
    enable_project_link = BooleanField()
    enable_instrument_link = BooleanField()
    disable_create_objects = BooleanField()
    is_template = BooleanField()
    select_usable_in_action_types = SelectMultipleField(coerce=int)
    scicat_export_type = SelectField(choices=[
        ('none', '—'),
        (SciCatExportType.SAMPLE.name.lower(), _('Sample')),
        (SciCatExportType.RAW_DATASET.name.lower(), _('Raw Dataset')),
        (SciCatExportType.DERIVED_DATASET.name.lower(), _('Derived Dataset')),
    ])

    def set_select_usable_in_action_types_attributes(self) -> None:
        self.select_usable_in_action_types.choices = [
            (action_type.id, get_translated_text(action_type.name, default=_('Unnamed Action Type')))
            for action_type in logic.action_types.get_action_types()
            if not action_type.disable_create_objects
        ]

        self.select_usable_in_action_types.shared_action_types = [action_type.id
                                                                  for action_type in logic.action_types.get_action_types()
                                                                  if action_type.component_id is not None]


def show_action_type_form(type_id: typing.Optional[int]) -> FlaskResponseT:
    check_current_user_is_not_readonly()
    action_type_translations = []
    action_type_language_ids = []
    action_type_form = ActionTypeForm()
    action_type_form.set_select_usable_in_action_types_attributes()

    english = logic.languages.get_language(logic.languages.Language.ENGLISH)

    def validate_string(string: str) -> bool:
        try:
            return 0 < len(string) < 100
        except Exception:
            return False

    def validate_strings(strings: typing.Sequence[str]) -> bool:
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
            action_type = logic.action_types.get_action_type(type_id)
        except logic.errors.ActionTypeDoesNotExistError:
            return flask.abort(404)
        if 'action_submit' not in flask.request.form:
            action_type_translations = logic.action_type_translations.get_action_type_translations_for_action_type(action_type.id)
            action_type_language_ids = [translation.language_id for translation in action_type_translations]
            action_type_form.admin_only.data = action_type.admin_only
            action_type_form.show_on_frontpage.data = action_type.show_on_frontpage
            action_type_form.show_in_navbar.data = action_type.show_in_navbar
            action_type_form.show_in_object_filters.data = action_type.show_in_object_filters
            action_type_form.enable_labels.data = action_type.enable_labels
            action_type_form.enable_files.data = action_type.enable_files
            action_type_form.enable_locations.data = action_type.enable_locations
            action_type_form.enable_publications.data = action_type.enable_publications
            action_type_form.enable_comments.data = action_type.enable_comments
            action_type_form.enable_activity_log.data = action_type.enable_activity_log
            action_type_form.enable_related_objects.data = action_type.enable_related_objects
            action_type_form.enable_project_link.data = action_type.enable_project_link
            action_type_form.enable_instrument_link.data = action_type.enable_instrument_link
            action_type_form.disable_create_objects.data = action_type.disable_create_objects
            action_type_form.select_usable_in_action_types.data = [element.id for element in action_type.usable_in_action_types]
            action_type_form.is_template.data = action_type.is_template
            if action_type.scicat_export_type is None:
                action_type_form.scicat_export_type.data = 'none'
            else:
                action_type_form.scicat_export_type.data = action_type.scicat_export_type.name.lower()

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

                    name = translation['name'].strip()
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

                action_type = logic.action_types.create_action_type(
                    admin_only=action_type_form.admin_only.data,
                    show_on_frontpage=action_type_form.show_on_frontpage.data,
                    show_in_navbar=action_type_form.show_in_navbar.data,
                    show_in_object_filters=action_type_form.show_in_object_filters.data,
                    enable_labels=action_type_form.enable_labels.data,
                    enable_files=action_type_form.enable_files.data,
                    enable_locations=action_type_form.enable_locations.data,
                    enable_publications=action_type_form.enable_publications.data,
                    enable_comments=action_type_form.enable_comments.data,
                    enable_activity_log=action_type_form.enable_activity_log.data,
                    enable_related_objects=action_type_form.enable_related_objects.data,
                    enable_project_link=action_type_form.enable_project_link.data,
                    enable_instrument_link=action_type_form.enable_instrument_link.data,
                    disable_create_objects=action_type_form.disable_create_objects.data,
                    is_template=action_type_form.is_template.data,
                    usable_in_action_type_ids=action_type_form.select_usable_in_action_types.data,
                    scicat_export_type={
                        type.name.lower(): type
                        for type in [
                            SciCatExportType.SAMPLE,
                            SciCatExportType.RAW_DATASET,
                            SciCatExportType.DERIVED_DATASET
                        ]
                    }.get(action_type_form.scicat_export_type.data)
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
                # load action type with new translations
                action_type = logic.action_types.get_action_type(action_type.id)
                logic.action_types.add_action_type_to_order(action_type)
        else:

            action_type = logic.action_types.update_action_type(
                action_type_id=type_id,
                admin_only=action_type_form.admin_only.data,
                show_on_frontpage=action_type_form.show_on_frontpage.data,
                show_in_navbar=action_type_form.show_in_navbar.data,
                show_in_object_filters=action_type_form.show_in_object_filters.data,
                enable_labels=action_type_form.enable_labels.data,
                enable_files=action_type_form.enable_files.data,
                enable_locations=action_type_form.enable_locations.data,
                enable_publications=action_type_form.enable_publications.data,
                enable_comments=action_type_form.enable_comments.data,
                enable_activity_log=action_type_form.enable_activity_log.data,
                enable_related_objects=action_type_form.enable_related_objects.data,
                enable_project_link=action_type_form.enable_project_link.data,
                enable_instrument_link=action_type_form.enable_instrument_link.data,
                disable_create_objects=action_type_form.disable_create_objects.data,
                is_template=action_type_form.is_template.data,
                usable_in_action_type_ids=action_type_form.select_usable_in_action_types.data,
                scicat_export_type={
                    'sample': SciCatExportType.SAMPLE,
                    'raw_dataset': SciCatExportType.RAW_DATASET,
                    'derived_dataset': SciCatExportType.DERIVED_DATASET
                }.get(action_type_form.scicat_export_type.data)
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
