# coding: utf-8
"""

"""
import typing

import flask
import flask_login
from flask_wtf import FlaskForm
from wtforms.fields import BooleanField
from flask_babel import _

from . import frontend
from .. import logic
from .utils import check_current_user_is_not_readonly
from ..utils import FlaskResponseT

from ..logic.components import get_component_or_none


@frontend.route('/location_types/')
@flask_login.login_required
def location_types() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(403)

    location_types = logic.locations.get_location_types()
    return flask.render_template(
        'location_types/location_types.html',
        location_types=location_types
    )


@frontend.route('/location_types/<int(signed=True):type_id>', methods=['GET', 'POST'])
@flask_login.login_required
def location_type(type_id: int) -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(403)

    try:
        location_type = logic.locations.get_location_type(
            location_type_id=type_id
        )
    except logic.errors.LocationTypeDoesNotExistError:
        return flask.abort(404)

    if flask.request.args.get('mode') == 'edit':
        if location_type.fed_id is not None:
            flask.flash(_('Editing imported location types is not yet supported.'), 'error')
            return flask.abort(403)
        else:
            return show_location_type_form(type_id)

    return flask.render_template(
        'location_types/location_type.html',
        location_type=location_type,
        component=get_component_or_none(location_type.component_id)
    )


@frontend.route('/location_types/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_location_type() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    return show_location_type_form(None)


class LocationTypeForm(FlaskForm):
    admin_only = BooleanField()
    enable_parent_location = BooleanField()
    enable_sub_locations = BooleanField()
    enable_object_assignments = BooleanField()
    enable_responsible_users = BooleanField()
    enable_instruments = BooleanField()
    show_location_log = BooleanField()
    enable_capacities = BooleanField()


def show_location_type_form(
        type_id: typing.Optional[int]
) -> FlaskResponseT:
    check_current_user_is_not_readonly()
    location_type_form = LocationTypeForm()

    has_error = False
    languages = logic.languages.get_languages()
    location_language_ids = set()
    language_id_by_lang_code = {
        language.lang_code: language.id
        for language in languages
    }
    english_id = logic.languages.Language.ENGLISH
    translation_language_ids = {english_id}
    translated_texts = {
        text_name: {
            'en': ''
        }
        for text_name in ('name', 'location_name_singular', 'location_name_plural')
    }

    if not location_type_form.is_submitted():
        if type_id is not None:
            try:
                location_type = logic.locations.get_location_type(type_id)
            except logic.errors.LocationTypeDoesNotExistError:
                return flask.abort(404)
            # set boolean fields from existing location type
            location_type_form.admin_only.data = location_type.admin_only
            location_type_form.enable_parent_location.data = location_type.enable_parent_location
            location_type_form.enable_sub_locations.data = location_type.enable_sub_locations
            location_type_form.enable_object_assignments.data = location_type.enable_object_assignments
            location_type_form.enable_responsible_users.data = location_type.enable_responsible_users
            location_type_form.enable_instruments.data = location_type.enable_instruments
            location_type_form.enable_capacities.data = location_type.enable_capacities
            location_type_form.show_location_log.data = location_type.show_location_log
            # set translated texts from existing location type
            for text_name in translated_texts:
                existing_translations = getattr(location_type, text_name)
                if existing_translations is not None:
                    for lang_code, translated_text in existing_translations.items():
                        translated_texts[text_name][lang_code] = translated_text
                        if lang_code in language_id_by_lang_code:
                            translation_language_ids.add(language_id_by_lang_code[lang_code])
        else:
            # set boolean field default values
            location_type_form.admin_only.data = False
            location_type_form.enable_parent_location.data = True
            location_type_form.enable_sub_locations.data = True
            location_type_form.enable_object_assignments.data = True
            location_type_form.enable_responsible_users.data = False
            location_type_form.show_location_log.data = False
            location_type_form.enable_instruments.data = True
            location_type_form.enable_capacities.data = False
    else:
        translation_language_id_strs = flask.request.form.getlist('translation-languages')
        translation_language_ids = {
            language_id
            for language_id in language_id_by_lang_code.values()
            if str(language_id) in translation_language_id_strs or language_id == english_id
        }
        # set translated texts from form
        for text_name in translated_texts:
            for language in languages:
                if language.id in translation_language_ids:
                    translated_text = flask.request.form.get(f'{text_name}_{language.id}', '')
                    translated_texts[text_name][language.lang_code] = translated_text
                    location_language_ids.add(language.id)
                    if len(translated_text) == 0 or len(translated_text) > 100:
                        has_error = True

    if not has_error and location_type_form.validate_on_submit():
        if type_id is None:
            type_id = logic.locations.create_location_type(
                admin_only=location_type_form.admin_only.data,
                enable_parent_location=location_type_form.enable_parent_location.data,
                enable_sub_locations=location_type_form.enable_sub_locations.data,
                enable_object_assignments=location_type_form.enable_object_assignments.data,
                enable_responsible_users=location_type_form.enable_responsible_users.data,
                enable_instruments=location_type_form.enable_instruments.data,
                enable_capacities=location_type_form.enable_capacities.data,
                show_location_log=location_type_form.show_location_log.data,
                name=translated_texts['name'],
                location_name_singular=translated_texts['location_name_singular'],
                location_name_plural=translated_texts['location_name_plural']
            ).id
        else:
            logic.locations.update_location_type(
                location_type_id=type_id,
                admin_only=location_type_form.admin_only.data,
                enable_parent_location=location_type_form.enable_parent_location.data,
                enable_sub_locations=location_type_form.enable_sub_locations.data,
                enable_object_assignments=location_type_form.enable_object_assignments.data,
                enable_responsible_users=location_type_form.enable_responsible_users.data,
                enable_instruments=location_type_form.enable_instruments.data,
                enable_capacities=location_type_form.enable_capacities.data,
                show_location_log=location_type_form.show_location_log.data,
                name=translated_texts['name'],
                location_name_singular=translated_texts['location_name_singular'],
                location_name_plural=translated_texts['location_name_plural']
            )
        return flask.redirect(flask.url_for('.location_type', type_id=type_id))

    return flask.render_template(
        'location_types/location_type_form.html',
        location_type_form=location_type_form,
        translation_language_ids=list(translation_language_ids),
        translated_texts=translated_texts,
        ENGLISH=logic.languages.get_language(logic.languages.Language.ENGLISH),
        languages=languages,
        submit_text=_('Create') if type_id is None else _('Save')
    )
