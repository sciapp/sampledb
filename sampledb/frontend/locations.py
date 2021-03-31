# coding: utf-8
"""

"""

import typing
import json

import flask
import flask_login
from flask_babel import _
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired

from . import frontend
from ..logic import errors
from ..logic.locations import Location, create_location, get_location, get_locations_tree, update_location, get_object_location_assignment, confirm_object_responsibility
from ..logic.languages import Language, get_language, get_languages, get_language_by_lang_code
from ..logic.security_tokens import verify_token
from ..logic.notifications import mark_notification_for_being_assigned_as_responsible_user_as_read
from .utils import check_current_user_is_not_readonly
from ..logic.utils import get_translated_text


class LocationForm(FlaskForm):
    translations = StringField(validators=[DataRequired()])
    parent_location = SelectField()


@frontend.route('/locations/')
@flask_login.login_required
def locations():
    locations_map, locations_tree = get_locations_tree()
    return flask.render_template(
        'locations/locations.html',
        locations_map=locations_map,
        locations_tree=locations_tree,
        sort_location_ids_by_name=_sort_location_ids_by_name
    )


@frontend.route('/locations/<int:location_id>', methods=['GET', 'POST'])
@flask_login.login_required
def location(location_id):
    try:
        location = get_location(location_id)
    except errors.LocationDoesNotExistError:
        return flask.abort(404)
    mode = flask.request.args.get('mode', None)
    if mode == 'edit':
        if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask_login.current_user.is_admin:
            flask.flash(_('Only administrators can edit locations.'), 'error')
            return flask.abort(403)
        check_current_user_is_not_readonly()
        return _show_location_form(location, None)
    locations_map, locations_tree = get_locations_tree()
    ancestors = []
    parent_location = location
    while parent_location.parent_location_id is not None:
        parent_location = get_location(parent_location.parent_location_id)
        ancestors.insert(0, (parent_location.id, parent_location.name))
    for ancestor_id, ancestor_name in ancestors:
        locations_tree = locations_tree[ancestor_id]
    locations_tree = locations_tree[location_id]
    return flask.render_template(
        'locations/location.html',
        locations_map=locations_map,
        locations_tree=locations_tree,
        location=location,
        ancestors=ancestors,
        sort_location_ids_by_name=_sort_location_ids_by_name
    )


@frontend.route('/locations/new/', methods=['GET', 'POST'])
@flask_login.login_required
def new_location():
    if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask_login.current_user.is_admin:
        flask.flash(_('Only administrators can create locations.'), 'error')
        return flask.abort(403)
    check_current_user_is_not_readonly()
    parent_location = None
    parent_location_id = flask.request.args.get('parent_location_id', None)
    if parent_location_id is not None:
        try:
            parent_location_id = int(parent_location_id)
        except ValueError:
            parent_location_id = None
    if parent_location_id:
        try:
            parent_location = get_location(parent_location_id)
        except errors.LocationDoesNotExistError:
            flask.flash(_('The requested parent location does not exist.'), 'error')
    return _show_location_form(None, parent_location)


@frontend.route('/locations/confirm_responsibility')
@flask_login.login_required
def accept_responsibility_for_object():
    token = flask.request.args.get('t', None)
    if token is None:
        flask.flash(_('The confirmation token is missing.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    object_location_assignment_id = verify_token(token, salt='confirm_responsibility', secret_key=flask.current_app.config['SECRET_KEY'], expiration=None)
    if object_location_assignment_id is None:
        flask.flash(_('The confirmation token is invalid.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    try:
        object_location_assignment = get_object_location_assignment(object_location_assignment_id)
    except errors.ObjectLocationAssignmentDoesNotExistError:
        flask.flash(_('This responsibility assignment does not exist.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    if object_location_assignment.responsible_user_id != flask_login.current_user.id:
        flask.flash(_('This responsibility assignment belongs to another user.'), 'error')
        return flask.redirect(flask.url_for('.index'))
    if object_location_assignment.confirmed:
        flask.flash(_('This responsibility assignment has already been confirmed.'), 'success')
    else:
        confirm_object_responsibility(object_location_assignment_id)
        flask.flash(_('You have successfully confirmed this responsibility assignment.'), 'success')
        mark_notification_for_being_assigned_as_responsible_user_as_read(
            user_id=flask_login.current_user.id,
            object_location_assignment_id=object_location_assignment_id
        )
    return flask.redirect(flask.url_for('.object', object_id=object_location_assignment.object_id))


def _sort_location_ids_by_name(location_ids: typing.Iterable[int], location_map: typing.Dict[int, Location]) -> typing.List[int]:
    location_ids = list(location_ids)
    location_ids.sort(key=lambda location_id: get_translated_text(location_map[location_id].name))
    return location_ids


def _show_location_form(location: typing.Optional[Location], parent_location: typing.Optional[Location]):
    english = get_language(Language.ENGLISH)
    name_language_ids = []
    description_language_ids = []
    location_translations = []
    if location is not None:
        submit_text = "Save"
    elif parent_location is not None:
        submit_text = "Create"
    else:
        submit_text = "Create"

    locations_map, locations_tree = get_locations_tree()
    invalid_location_ids = []
    if location is not None:
        invalid_location_ids.append(location.id)
        ancestor_ids = []
        _parent_location = location
        while _parent_location.parent_location_id is not None:
            _parent_location = get_location(_parent_location.parent_location_id)
            ancestor_ids.insert(0, _parent_location.id)
        locations_subtree = locations_tree
        for ancestor_id in ancestor_ids:
            locations_subtree = locations_subtree[ancestor_id]
        locations_subtree = locations_subtree[location.id]
        unhandled_descendent_ids_and_subtrees = [(descendent_id, locations_subtree) for descendent_id in locations_subtree]
        while unhandled_descendent_ids_and_subtrees:
            descendent_id, locations_subtree = unhandled_descendent_ids_and_subtrees.pop(0)
            invalid_location_ids.append(descendent_id)
            locations_subtree = locations_subtree[descendent_id]
            for descendent_id in locations_subtree:
                unhandled_descendent_ids_and_subtrees.append((descendent_id, locations_subtree))

    location_form = LocationForm()
    location_form.parent_location.choices = [('-1', '-')] + [
        (str(location_id), locations_map[location_id].name)
        for location_id in locations_map
        if location_id not in invalid_location_ids
    ]
    if not location_form.is_submitted():
        if location is not None and location.parent_location_id:
            location_form.parent_location.data = str(location.parent_location_id)
        elif parent_location is not None:
            location_form.parent_location.data = str(parent_location.id)
        else:
            location_form.parent_location.data = str(-1)

    form_is_valid = False
    if location_form.validate_on_submit():
        form_is_valid = True

    if location is not None:
        name_language_ids = []
        description_language_ids = []
        for language_code, name in location.name.items():
            language = get_language_by_lang_code(language_code)
            if not language.enabled_for_input:
                continue
            name_language_ids.append(language.id)
            location_translations.append({
                'language_id': language.id,
                'lang_name': get_translated_text(language.names),
                'name': name,
                'description': ''
            })

        for language_code, description in location.description.items():
            language = get_language_by_lang_code(language_code)
            if not language.enabled_for_input:
                continue
            description_language_ids.append(language.id)
            for translation in location_translations:
                if language.id == translation['language_id']:
                    translation['description'] = description
                    break
            else:
                location_translations.append({
                    'language_id': language.id,
                    'lang_name': get_translated_text(language.names),
                    'name': '',
                    'description': description
                })

    if form_is_valid:
        try:
            translations = json.loads(location_form.translations.data)
            if not translations:
                raise ValueError(_('Please enter at least an english name.'))
            names = {}
            descriptions = {}
            for translation in translations:
                name = translation['name'].strip()
                description = translation['description'].strip()
                language_id = int(translation['language_id'])
                if language_id == Language.ENGLISH:
                    if name == '':
                        raise ValueError(_('Please enter at least an english name.'))
                elif name == '' and description == '':
                    continue
                language = get_language(language_id)
                if language.enabled_for_input:
                    names[language.lang_code] = name
                    descriptions[language.lang_code] = description
                else:
                    location_form.translations.errors.append(_('One of these languages is not supported.'))
        except errors.LanguageDoesNotExistError:
            location_form.translations.errors.append(_('One of these languages is not supported.'))
        except Exception as e:
            location_form.translations.errors.append(str(e))
        parent_location_id = location_form.parent_location.data

        if len(location_form.translations.errors) == 0:
            try:
                parent_location_id = int(parent_location_id)
            except ValueError:
                parent_location_id = None
            if parent_location_id < 0:
                parent_location_id = None
            if location is None:
                location = create_location(names, descriptions, parent_location_id, flask_login.current_user.id)
                flask.flash(_('The location was created successfully.'), 'success')
            else:
                update_location(location.id, names, descriptions, parent_location_id, flask_login.current_user.id)
                flask.flash(_('The location was updated successfully.'), 'success')
            return flask.redirect(flask.url_for('.location', location_id=location.id))
    if english.id not in description_language_ids:
        description_language_ids.append(english.id)
    return flask.render_template(
        'locations/location_form.html',
        location_form=location_form,
        submit_text=submit_text,
        ENGLISH=english,
        languages=get_languages(only_enabled_for_input=True),
        translations=location_translations,
        name_language_ids=name_language_ids,
        description_language_ids=description_language_ids
    )
