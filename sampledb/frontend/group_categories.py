
import typing

import flask
import flask_login
from flask_wtf import FlaskForm
from wtforms.fields import SelectField, IntegerField
from wtforms.validators import InputRequired
from flask_babel import _


from . import frontend
from .. import logic
from .utils import check_current_user_is_not_readonly
from ..utils import FlaskResponseT
from ..logic.utils import get_translated_text


class DeleteCategoryForm(FlaskForm):
    category_id = IntegerField(validators=[InputRequired()])


@frontend.route('/group_categories/')
@flask_login.login_required
def group_categories() -> FlaskResponseT:
    group_categories = list(logic.group_categories.get_group_categories())
    group_categories.sort(key=lambda category: get_translated_text(category.name).lower())
    group_categories_by_id = {
        category.id: category
        for category in group_categories
    }
    group_category_names = logic.group_categories.get_full_group_category_names()
    group_category_tree = logic.group_categories.get_group_category_tree()
    delete_category_form = DeleteCategoryForm()
    return flask.render_template(
        'group_categories/group_categories.html',
        group_categories=group_categories,
        group_categories_by_id=group_categories_by_id,
        group_category_names=group_category_names,
        group_category_tree=group_category_tree,
        delete_category_form=delete_category_form,
    )


@frontend.route('/group_categories/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_group_category() -> FlaskResponseT:
    if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_GROUP_CATEGORIES'] and not flask_login.current_user.is_admin:
        return flask.abort(403)
    return _show_group_category_form(None)


@frontend.route('/group_categories/<int:category_id>', methods=['GET', 'POST'])
@flask_login.login_required
def group_category(category_id: int) -> FlaskResponseT:
    if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_GROUP_CATEGORIES'] and not flask_login.current_user.is_admin:
        return flask.abort(403)

    try:
        logic.group_categories.get_group_category(category_id)
    except logic.errors.GroupCategoryDoesNotExistError:
        return flask.abort(404)

    delete_category_form = DeleteCategoryForm()
    if delete_category_form.validate_on_submit() and delete_category_form.category_id.data == category_id:
        check_current_user_is_not_readonly()
        logic.group_categories.delete_group_category(category_id=category_id)
        flask.flash(_('The group category was deleted successfully.'), 'success')
        return flask.redirect(flask.url_for('.group_categories'))

    return _show_group_category_form(category_id)


class GroupCategoryForm(FlaskForm):
    parent_category_id = SelectField()


def _show_group_category_form(category_id: typing.Optional[int]) -> FlaskResponseT:
    check_current_user_is_not_readonly()
    group_category_form = GroupCategoryForm()

    group_category_names = logic.group_categories.get_full_group_category_names()
    group_category_form.parent_category_id.choices = [('-1', '—')] + [
        (str(category.id), ' / '.join(get_translated_text(name) for name in group_category_names[category.id]))
        for category in logic.group_categories.get_group_categories()
        if category_id is None or (category.id != category_id and not logic.group_categories.category_has_ancestor(category.id, category_id))
    ]

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
        for text_name in ('name',)
    }

    if not group_category_form.is_submitted():
        if category_id is not None:
            try:
                group_category = logic.group_categories.get_group_category(category_id)
            except logic.errors.LocationTypeDoesNotExistError:
                return flask.abort(404)
            # set fields from existing group category
            group_category_form.parent_category_id.data = str(group_category.parent_category_id)
            # set translated texts from existing group category
            for text_name in translated_texts:
                existing_translations = getattr(group_category, text_name)
                if existing_translations is not None:
                    for lang_code, translated_text in existing_translations.items():
                        translated_texts[text_name][lang_code] = translated_text
                        if lang_code in language_id_by_lang_code:
                            translation_language_ids.add(language_id_by_lang_code[lang_code])
        else:
            # set default values
            group_category_form.parent_category_id.data = '-1'
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

    if not has_error and group_category_form.validate_on_submit():
        if group_category_form.parent_category_id.data == '-1':
            parent_category_id = None
        else:
            parent_category_id = int(group_category_form.parent_category_id.data)
        if category_id is None:
            logic.group_categories.create_group_category(
                parent_category_id=parent_category_id,
                **translated_texts
            )
            flask.flash(_('The group category was created successfully.'), 'success')
        else:
            try:
                logic.group_categories.update_group_category(
                    category_id=category_id,
                    parent_category_id=parent_category_id,
                    **translated_texts
                )
            except logic.errors.CyclicGroupCategoryError:
                flask.flash(_('Invalid parent group category.'), 'error')
            else:
                flask.flash(_('The group category was updated successfully.'), 'success')
        return flask.redirect(flask.url_for('.group_categories'))

    return flask.render_template(
        'group_categories/group_category_form.html',
        group_category_form=group_category_form,
        translation_language_ids=list(translation_language_ids),
        translated_texts=translated_texts,
        ENGLISH=logic.languages.get_language(logic.languages.Language.ENGLISH),
        languages=languages,
        submit_text=_('Create') if category_id is None else _('Save')
    )
