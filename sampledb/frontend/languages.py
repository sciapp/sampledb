# coding: utf-8
"""

"""

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms.fields import StringField, BooleanField
from wtforms.validators import InputRequired

from . import frontend
from .. import logic
from .utils import check_current_user_is_not_readonly

from flask_babel import gettext


@frontend.route('/languages/')
@flask_login.login_required
def languages():
    if not flask_login.current_user.is_admin:
        return flask.abort(403)

    return flask.render_template(
        'languages/languages.html',
        languages=logic.languages.get_languages()
    )


@frontend.route('/languages/<int(signed=True):language_id>', methods=['GET', 'POST'])
@flask_login.login_required
def language(language_id):
    if not flask_login.current_user.is_admin:
        return flask.abort(403)

    try:
        language = logic.languages.get_language(language_id)
    except logic.errors.LanguageDoesNotExistError:
        return flask.abort(404)

    mode = flask.request.args.get('mode', None)
    if mode == 'edit':
        return show_language_form(language_id)

    all_languages = logic.languages.get_languages()

    return flask.render_template(
        'languages/language.html',
        language=language,
        all_languages=all_languages
    )


@frontend.route('/language/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_language():
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    return show_language_form(None)


class LanguageForm(FlaskForm):
    name_english = StringField(validators=[InputRequired()])
    lang_code = StringField(validators=[InputRequired()])
    datetime_format_datetime = StringField(validators=[InputRequired()])
    datetime_format_moment = StringField(validators=[InputRequired()])
    enabled_for_input = BooleanField()
    enabled_for_user_interface = BooleanField()


def show_language_form(language_id):
    check_current_user_is_not_readonly()
    language_form = LanguageForm()

    if language_id is not None:
        try:
            language = logic.languages.get_language(language_id)
        except logic.errors.LanguageDoesNotExistError:
            return flask.abort(404)
        if 'language_submit' not in flask.request.form:
            language_form.name_english.data = language.names.get('en', '')
            language_form.lang_code.data = language.lang_code
            language_form.datetime_format_datetime.data = language.datetime_format_datetime
            language_form.datetime_format_moment.data = language.datetime_format_moment
            language_form.enabled_for_input.data = language.enabled_for_input
            language_form.enabled_for_user_interface.data = language.enabled_for_user_interface
    else:
        language = None

    if language_form.validate_on_submit():
        try:
            existing_language_for_code = logic.languages.get_language_by_lang_code(
                lang_code=language_form.lang_code.data.strip().lower()
            )
        except logic.errors.LanguageDoesNotExistError:
            existing_language_for_code = None
        names = {}
        for key in flask.request.form:
            for lang in logic.languages.get_languages():
                if key == 'name_' + str(lang.id):
                    if flask.request.form.get(key).strip():
                        names[lang.lang_code] = flask.request.form.get(key).strip()
        names['en'] = language_form.name_english.data.strip()
        if language_id is None and existing_language_for_code is None:
            names[language_form.lang_code.data.strip().lower()] = flask.request.form.get('name_new').strip()
            language = logic.languages.create_language(
                names=names,
                lang_code=language_form.lang_code.data.strip().lower(),
                datetime_format_datetime=language_form.datetime_format_datetime.data.strip(),
                datetime_format_moment=language_form.datetime_format_moment.data.strip(),
                enabled_for_input=bool(language_form.enabled_for_input.data),
                enabled_for_user_interface=bool(language_form.enabled_for_user_interface.data)
            )
            return flask.redirect(flask.url_for('.language', language_id=language.id))
        elif language_id is None or (existing_language_for_code is not None and language_id != existing_language_for_code.id):
            flask.flash(_('This language code is already in use.'), 'error')
        elif language_id == logic.languages.Language.ENGLISH and not bool(language_form.enabled_for_input.data):
            flask.flash(_('The English language cannot be disabled for input.'), 'error')
        elif language_id == logic.languages.Language.ENGLISH and not bool(language_form.enabled_for_user_interface.data):
            flask.flash(_('The English language cannot be disabled for the user interface.'), 'error')
        elif language is not None and language.lang_code != language_form.lang_code.data and language.lang_code in logic.locale.SUPPORTED_LOCALES:
            flask.flash(_('The language code must stay "%(lang_code)s".', lang_code=language.lang_code), 'error')
        else:
            try:
                logic.languages.update_language(
                    language_id=language_id,
                    names=names,
                    lang_code=language_form.lang_code.data.strip().lower(),
                    datetime_format_datetime=language_form.datetime_format_datetime.data.strip(),
                    datetime_format_moment=language_form.datetime_format_moment.data.strip(),
                    enabled_for_input=bool(language_form.enabled_for_input.data),
                    enabled_for_user_interface=bool(language_form.enabled_for_user_interface.data)
                )
                return flask.redirect(flask.url_for('.language', language_id=language_id))
            except Exception:
                flask.flash(_('Something went wrong while updating the language. Please try again.'), 'error')

    return flask.render_template(
        'languages/language_form.html',
        language_form=language_form,
        existing_language=language,
        all_languages=logic.languages.get_languages(),
        keep_language_code=language is not None and language.lang_code in logic.locale.SUPPORTED_LOCALES,
        submit_text=gettext('Create') if language_id is None else gettext('Save')
    )
