import json
import typing
from http import HTTPStatus

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired

from . import frontend, utils
from ..logic import errors, info_pages, users, languages, markdown_to_html, markdown_images
from ..models import User
from ..utils import FlaskResponseT


class InfoPageAcknowledgementForm(FlaskForm):
    info_page_ids = StringField(validators=[DataRequired()])


class SetInfoPageDisabledForm(FlaskForm):
    disabled = BooleanField()
    submit_set_info_page_disabled = SubmitField(validators=[DataRequired()])


class DeleteInfoPageForm(FlaskForm):
    submit_delete_info_page = SubmitField(validators=[DataRequired()])


@frontend.route('/info_pages/acknowledge', methods=['POST'])
@flask_login.login_required
def acknowledge_info_pages() -> FlaskResponseT:
    utils.check_current_user_is_not_readonly()
    form = InfoPageAcknowledgementForm()
    if not form.validate_on_submit():
        return flask.abort(HTTPStatus.BAD_REQUEST)
    existing_info_page_ids = {
        info_page.id
        for info_page in info_pages.get_info_pages()
    }
    info_page_ids = set()
    for info_page_id_str in form.info_page_ids.data.split(','):
        try:
            info_page_id = int(info_page_id_str)
        except ValueError:
            return flask.abort(HTTPStatus.BAD_REQUEST)
        if info_page_id not in existing_info_page_ids:
            return flask.abort(HTTPStatus.BAD_REQUEST)
        info_page_ids.add(info_page_id)
    info_pages.acknowledge_info_pages(
        info_page_ids=info_page_ids,
        user_id=flask_login.current_user.id,
    )
    return '', HTTPStatus.NO_CONTENT


@frontend.route('/admin/info_pages/')
@flask_login.login_required
def admin_info_pages() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(HTTPStatus.FORBIDDEN)
    return flask.render_template(
        "info_pages/info_pages.html",
        info_pages=info_pages.get_info_pages(),
        url_map=flask.current_app.url_map,
        set_info_page_disabled_form=SetInfoPageDisabledForm(),
        delete_info_page_form=DeleteInfoPageForm(),
    )


@frontend.route('/admin/info_pages/<int:info_page_id>', methods=['GET', 'POST'])
@flask_login.login_required
def admin_info_page(info_page_id: int) -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(HTTPStatus.FORBIDDEN)
    if flask.request.args.get('mode') == 'edit':
        return show_info_page_form(info_page_id)
    try:
        info_page = info_pages.get_info_page(info_page_id=info_page_id)
    except errors.InfoPageDoesNotExistError:
        return flask.abort(404)
    delete_info_page_form = DeleteInfoPageForm()
    if delete_info_page_form.validate_on_submit():
        utils.check_current_user_is_not_readonly()
        info_pages.delete_info_page(info_page_id=info_page_id)
        flask.flash(_('The info page has been deleted successfully.'), 'success')
        return flask.redirect(flask.url_for('frontend.admin_info_pages'))
    set_info_page_disabled_form = SetInfoPageDisabledForm()
    if set_info_page_disabled_form.validate_on_submit():
        utils.check_current_user_is_not_readonly()
        should_be_disabled = set_info_page_disabled_form.disabled.data
        if info_page.disabled == should_be_disabled:
            if should_be_disabled:
                flask.flash(_('The info page has already been disabled.'), 'warning')
            else:
                flask.flash(_('The info page has already been enabled.'), 'warning')
        else:
            info_pages.set_info_page_disabled(info_page_id=info_page_id, disabled=should_be_disabled)
            if should_be_disabled:
                flask.flash(_('The info page has been disabled successfully.'), 'success')
            else:
                flask.flash(_('The info page has been enabled successfully.'), 'success')
        return flask.redirect(flask.url_for('frontend.admin_info_page', info_page_id=info_page_id))
    return flask.render_template(
        "info_pages/info_page.html",
        info_page=info_page,
        url_map=flask.current_app.url_map,
        users=users.get_users(exclude_hidden=False, order_by=User.id, exclude_fed=True, exclude_eln_import=True),
        acknowledgements=info_pages.get_acknowledgements_for_info_page(info_page_id=info_page_id),
        set_info_page_disabled_form=set_info_page_disabled_form,
        delete_info_page_form=delete_info_page_form,
    )


class InfoPageForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])
    endpoint = SelectField()
    do_not_show_existing_users = BooleanField()
    clear_acknowledgements = BooleanField()


@frontend.route('/admin/info_pages/new', methods=['GET', 'POST'])
@flask_login.login_required
def admin_new_info_page() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(HTTPStatus.FORBIDDEN)
    return show_info_page_form(None)


def show_info_page_form(info_page_id: typing.Optional[int]) -> FlaskResponseT:
    utils.check_current_user_is_not_readonly()

    class InfoPageTranslation(typing.TypedDict):
        language_id: int
        language: languages.Language
        title: str
        content: str

    info_page_translations: typing.List[InfoPageTranslation] = []
    info_page_language_ids: typing.List[int] = []
    info_page_form = InfoPageForm()
    url_rules_by_endpoint = info_pages.get_url_rules_by_endpoint()
    info_page_form.endpoint.choices = [
        ('', 'All routes')
    ] + sorted([
        (endpoint, ', '.join(rules))
        for endpoint, rules in url_rules_by_endpoint.items()
    ], key=lambda choice: choice[1])

    english = languages.get_language(languages.Language.ENGLISH)

    if info_page_id is not None:
        try:
            info_page = info_pages.get_info_page(info_page_id)
        except errors.InfoPageDoesNotExistError:
            return flask.abort(404)
        if 'action_submit' not in flask.request.form:
            info_page_translations = []
            info_page_language_ids = []
            info_page_language_codes = set()
            for translated_text in [info_page.title, info_page.content]:
                for language_code in translated_text:
                    info_page_language_codes.add(language_code)
            for language_code in info_page_language_codes:
                try:
                    language = languages.get_language_by_lang_code(language_code)
                except errors. LanguageDoesNotExistError:
                    continue
                info_page_language_ids.append(language.id)
                translation: InfoPageTranslation = {
                    'language': language,
                    'language_id': language.id,
                    'title': info_page.title.get(language_code, ''),
                    'content': info_page.content.get(language_code, ''),
                }
                info_page_translations.append(translation)
            info_page_form.endpoint.data = info_page.endpoint

    if info_page_id is None:
        current_page_url = flask.url_for('.admin_new_info_page')
    else:
        current_page_url = flask.url_for('.admin_info_page', info_page_id=info_page_id, mode='edit')
    if info_page_form.validate_on_submit():
        try:
            translation_data = json.loads(info_page_form.translations.data)
        except Exception:
            flask.flash(_('Please fill out the form.'), 'error')
            return flask.redirect(current_page_url)
        translation_keys = {'language_id', 'title', 'content'}
        if not isinstance(translation_data, list):
            translation_data = ()
        translated_title = {}
        translated_content = {}
        for translation in translation_data:
            if not isinstance(translation, dict):
                flask.flash(_('Please fill out the form.'), 'error')
                return flask.redirect(current_page_url)

            if set(translation.keys()) != translation_keys:
                flask.flash(_('Please fill out the form.'), 'error')
                return flask.redirect(current_page_url)

            language_id = int(translation['language_id'])
            try:
                language = languages.get_language(language_id)
            except errors.LanguageDoesNotExistError:
                continue
            title = translation['title'].strip()
            content = translation['content'].strip()
            if not title or not content:
                flask.flash(_('The fields for title and content are required.'), 'error')
                return flask.redirect(current_page_url)
            if len(title) > 100:
                flask.flash(_('Please enter a shorter title (at most 100 characters).'), 'error')
                return flask.redirect(current_page_url)
            translated_title[language.lang_code] = title
            translated_content[language.lang_code] = content
        if 'en' not in translated_title or 'en' not in translated_content:
            flask.flash(_('The fields for title and content are required.'), 'error')
            return flask.redirect(current_page_url)
        if info_page_id is None:
            info_page_id = info_pages.create_info_page(
                title=translated_title,
                content=translated_content,
                endpoint=info_page_form.endpoint.data or None,
                disabled=False
            ).id
            if info_page_form.do_not_show_existing_users.data:
                info_pages.acknowledge_info_page_for_existing_users(info_page_id)
            flask.flash(_('The info page has been created successfully.'), 'success')
        else:
            info_pages.update_info_page(
                info_page_id=info_page_id,
                title=translated_title,
                content=translated_content,
                endpoint=info_page_form.endpoint.data or None
            )
            if info_page_form.clear_acknowledgements.data:
                info_pages.clear_acknowledgements_for_info_page(info_page_id)
            flask.flash(_('The info page has been updated successfully.'), 'success')
        for content in translated_content.values():
            content_as_html = markdown_to_html.markdown_to_safe_html(content, anchor_prefix=f"info-page-content-{info_page_id}")
            markdown_images.mark_referenced_markdown_images_as_permanent(content_as_html)
        return flask.redirect(flask.url_for('.admin_info_page', info_page_id=info_page_id))
    return flask.render_template(
        'info_pages/info_page_form.html',
        info_page_form=info_page_form,
        info_page_translations=info_page_translations,
        info_page_language_ids=info_page_language_ids,
        languages=languages.get_languages(),
        ENGLISH=english,
        submit_text=_('Create') if info_page_id is None else _('Save')
    )
