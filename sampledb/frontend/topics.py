# coding: utf-8
"""

"""
import json
import typing

import flask
import flask_login
from flask_wtf import FlaskForm
from wtforms.fields import StringField, BooleanField
from wtforms.validators import DataRequired, ValidationError
from flask_babel import _

from . import frontend
from .locations import sort_location_ids_by_name, filter_location_tree_by_predicate, user_has_read_permissions_for_location, location_has_topic_ids
from .. import logic
from .utils import check_current_user_is_not_readonly
from ..logic.languages import get_language, get_language_by_lang_code
from ..logic.locations import Location, get_locations_tree
from ..logic.location_permissions import get_user_location_permissions
from ..logic.utils import get_translated_text
from ..logic.markdown_to_html import markdown_to_safe_html
from ..logic.markdown_images import mark_referenced_markdown_images_as_permanent
from ..utils import FlaskResponseT
from ..models import Permissions


class TopicsSortingForm(FlaskForm):
    encoded_order = StringField("Order-String", [DataRequired()])

    def validate_encoded_order(form, field: StringField) -> None:
        valid_topic_ids = [topic.id for topic in logic.topics.get_topics()]

        try:
            split_string = field.data.split(",")
            sorted_topic_ids = list(map(int, split_string))
            for topic_id in sorted_topic_ids:
                if topic_id not in valid_topic_ids:
                    raise ValidationError(f"{topic_id} is not a valid id")
        except ValueError:
            raise ValidationError("Invalid IDs.")

        field.data = sorted_topic_ids


@frontend.route('/topics/', methods=['GET', 'POST'])
@flask_login.login_required
def topics() -> FlaskResponseT:
    sorting_form = TopicsSortingForm()
    if sorting_form.validate_on_submit():
        check_current_user_is_not_readonly()
        logic.topics.set_topics_order(sorting_form.encoded_order.data)
    return flask.render_template(
        'topics/topics.html',
        topics=logic.topics.get_topics(),
        sorting_form=sorting_form
    )


@frontend.route('/topics/<int:topic_id>', methods=['GET', 'POST'])
@flask_login.login_required
def topic(topic_id: int) -> FlaskResponseT:
    try:
        topic = logic.topics.get_topic(
            topic_id=topic_id
        )
    except logic.errors.TopicDoesNotExistError:
        return flask.abort(404)

    if flask.request.args.get('mode') == 'edit':
        return show_topic_form(topic_id)

    if flask.current_app.config['DISABLE_INSTRUMENTS']:
        topic_instruments = []
    else:
        topic_instruments = logic.instruments.get_instruments_for_topic(topic_id=topic_id)
    topic_instruments.sort(key=lambda instrument: (
        0 if instrument.fed_id is None else 1,
        get_translated_text(instrument.name).lower()
    ))
    topic_actions = [
        action
        for action in logic.actions.get_actions_for_topic(topic_id=topic_id)
        if Permissions.READ in logic.action_permissions.get_user_action_permissions(action.id, flask_login.current_user.id) and (not action.is_hidden or flask_login.current_user.is_admin)
    ]
    topic_actions = logic.actions.sort_actions_for_user(
        actions=topic_actions,
        user_id=flask_login.current_user.id,
        sort_by_favorite=False
    )
    locations_map, locations_tree = get_locations_tree()
    location_permissions_by_id = {
        location_id: get_user_location_permissions(location_id, flask_login.current_user.id)
        for location_id in locations_map
    }

    def locations_filter(location: Location) -> bool:
        return location_has_topic_ids(location, frozenset({topic_id}))
    locations_tree = filter_location_tree_by_predicate(locations_tree, locations_map, locations_filter)
    locations_tree = filter_location_tree_by_predicate(locations_tree, locations_map, lambda location: user_has_read_permissions_for_location(location, location_permissions_by_id))
    return flask.render_template(
        'topics/topic.html',
        topic=topic,
        topic_instruments=topic_instruments,
        topic_actions=topic_actions,
        locations_map=locations_map,
        locations_tree=locations_tree,
        Permissions=Permissions,
        permissions_by_id=location_permissions_by_id,
        sort_location_ids_by_name=sort_location_ids_by_name,
        locations_filter=locations_filter
    )


@frontend.route('/topics/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_topic() -> FlaskResponseT:
    if not flask_login.current_user.is_admin:
        return flask.abort(403)
    return show_topic_form(None)


class TopicForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])

    show_on_frontpage = BooleanField()
    show_in_navbar = BooleanField()
    description_is_markdown = BooleanField()
    short_description_is_markdown = BooleanField()


def show_topic_form(topic_id: typing.Optional[int]) -> FlaskResponseT:
    check_current_user_is_not_readonly()
    topic_language_ids = []
    topic_form = TopicForm()

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

    class TopicTranslation(typing.TypedDict):
        language_id: typing.Union[int, str]
        lang_name: str
        name: str
        description: str
        short_description: str

    translations: typing.List[TopicTranslation] = []

    if topic_id is not None:
        try:
            topic = logic.topics.get_topic(topic_id)
        except logic.errors.TopicDoesNotExistError:
            return flask.abort(404)
        for lang_code, name in topic.name.items():
            lang_id = get_language_by_lang_code(lang_code).id
            translation: TopicTranslation = {
                'language_id': str(lang_id),
                'lang_name': get_translated_text(get_language(lang_id).names),
                'name': name,
                'description': '',
                'short_description': ''
            }
            translations.append(translation)

        for lang_code, description in topic.description.items():
            if lang_code == '':
                continue
            lang_id = get_language_by_lang_code(lang_code).id
            for translation in translations:
                if str(lang_id) == translation['language_id']:
                    translation['description'] = description
                    break
            else:
                translation = {
                    'language_id': str(lang_id),
                    'lang_name': get_translated_text(get_language(lang_id).names),
                    'name': '',
                    'description': description,
                    'short_description': ''
                }
                translations.append(translation)

        for lang_code, short_description in topic.short_description.items():
            if lang_code == '':
                continue
            lang_id = get_language_by_lang_code(lang_code).id
            for translation in translations:
                if str(lang_id) == translation['language_id']:
                    translation['short_description'] = short_description
                    break
            else:
                translation = {
                    'language_id': str(lang_id),
                    'lang_name': get_translated_text(get_language(lang_id).names),
                    'name': '',
                    'description': '',
                    'short_description': short_description
                }
                translations.append(translation)
        if 'action_submit' not in flask.request.form:
            topic_language_ids = [int(translation['language_id']) for translation in translations]
            topic_form.show_on_frontpage.data = topic.show_on_frontpage
            topic_form.show_in_navbar.data = topic.show_in_navbar
            topic_form.description_is_markdown.data = topic.description_is_markdown
            topic_form.short_description_is_markdown.data = topic.short_description_is_markdown

    if topic_form.validate_on_submit():
        try:
            translation_data = json.loads(topic_form.translations.data)
        except Exception:
            flask.flash(_('There was a problem saving the topic data.'), 'error')
            return flask.render_template(
                'topics/topic_form.html',
                topic_form=topic_form,
                topic_translations=translations,
                languages=logic.languages.get_languages(),
                ENGLISH=english,
                submit_text=_('Create') if topic_id is None else _('Save')
            )
        else:
            valid_translation_keys = {'language_id', 'name', 'description', 'short_description'}
            if not isinstance(translation_data, list):
                translation_data = ()
            for translation in translation_data:
                if not isinstance(translation, dict):
                    flask.flash(_('Please fill out the form.'), 'error')
                    return flask.render_template(
                        'topics/topic_form.html',
                        topic_form=topic_form,
                        topic_translations=translations,
                        languages=logic.languages.get_languages(),
                        ENGLISH=english,
                        submit_text=_('Create') if topic_id is None else _('Save')
                    )

                translation_keys = set(translation.keys())
                translation_keys -= {'lang_name'}
                if translation_keys != valid_translation_keys:
                    flask.flash(_('Please fill out the form.'), 'error')
                    return flask.render_template(
                        'topics/topic_form.html',
                        topic_form=topic_form,
                        topic_translations=translations,
                        languages=logic.languages.get_languages(),
                        ENGLISH=english,
                        submit_text=_('Create') if topic_id is None else _('Save')
                    )

                name = translation['name'].strip()

                if not validate_strings([name]):
                    flask.flash(_('The name is required.'), 'error')
                    return flask.render_template(
                        'topics/topic_form.html',
                        topic_form=topic_form,
                        topic_translations=translations,
                        languages=logic.languages.get_languages(),
                        ENGLISH=english,
                        submit_text=_('Create') if topic_id is None else _('Save')
                    )

            names: typing.Dict[str, str] = {}
            descriptions: typing.Dict[str, str] = {}
            short_descriptions: typing.Dict[str, str] = {}

            for translation in translation_data:
                language_id = int(translation['language_id'])
                language_code = get_language(language_id).lang_code
                names[language_code] = translation['name'].strip()
                descriptions[language_code] = translation['description'].strip()
                short_descriptions[language_code] = translation['short_description'].strip()

                if topic_form.description_is_markdown.data:
                    description_as_html = markdown_to_safe_html(descriptions[language_code], anchor_prefix="topic-description")
                    mark_referenced_markdown_images_as_permanent(description_as_html)
                if topic_form.short_description_is_markdown.data:
                    short_description_as_html = markdown_to_safe_html(short_descriptions[language_code], anchor_prefix="topic-short-description")
                    mark_referenced_markdown_images_as_permanent(short_description_as_html)

            if topic_id is None:
                topic = logic.topics.create_topic(
                    name=names,
                    description=descriptions,
                    short_description=short_descriptions,
                    show_on_frontpage=topic_form.show_on_frontpage.data,
                    show_in_navbar=topic_form.show_in_navbar.data,
                    description_is_markdown=topic_form.description_is_markdown.data,
                    short_description_is_markdown=topic_form.short_description_is_markdown.data
                )
                logic.topics.add_topic_to_order(topic)
            else:
                topic = logic.topics.update_topic(
                    topic_id=topic_id,
                    name=names,
                    description=descriptions,
                    short_description=short_descriptions,
                    show_on_frontpage=topic_form.show_on_frontpage.data,
                    show_in_navbar=topic_form.show_in_navbar.data,
                    description_is_markdown=topic_form.description_is_markdown.data,
                    short_description_is_markdown=topic_form.short_description_is_markdown.data
                )

        return flask.redirect(flask.url_for('.topic', topic_id=topic.id))

    return flask.render_template(
        'topics/topic_form.html',
        topic_form=topic_form,
        topic_translations=translations,
        topic_language_ids=topic_language_ids,
        languages=logic.languages.get_languages(),
        ENGLISH=english,
        submit_text=_('Create') if topic_id is None else _('Save')
    )
