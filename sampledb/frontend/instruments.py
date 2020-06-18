# coding: utf-8
"""

"""

import flask
import flask_login
from flask_wtf import FlaskForm
from wtforms import StringField, SelectMultipleField, BooleanField
from wtforms.validators import Length

from . import frontend
from ..logic.instruments import get_instruments, get_instrument, create_instrument, update_instrument, set_instrument_responsible_users
from ..logic.actions import ActionType
from ..logic.errors import InstrumentDoesNotExistError
from ..logic.favorites import get_user_favorite_instrument_ids
from ..logic.users import get_users
from .users.forms import ToggleFavoriteInstrumentForm
from .utils import check_current_user_is_not_readonly, markdown_to_safe_html

__author__ = 'Florian Rhiem <f.rhiem@fz-juelich.de>'


@frontend.route('/instruments/')
@flask_login.login_required
def instruments():
    instruments = get_instruments()
    # TODO: check instrument permissions
    user_favorite_instrument_ids = get_user_favorite_instrument_ids(flask_login.current_user.id)
    # Sort by: favorite / not favorite, instrument name
    instruments.sort(key=lambda instrument: (
        0 if instrument.id in user_favorite_instrument_ids else 1,
        instrument.name.lower()
    ))
    toggle_favorite_instrument_form = ToggleFavoriteInstrumentForm()
    return flask.render_template(
        'instruments/instruments.html',
        instruments=instruments,
        user_favorite_instrument_ids=user_favorite_instrument_ids,
        toggle_favorite_instrument_form=toggle_favorite_instrument_form
    )


@frontend.route('/instruments/<int:instrument_id>')
@flask_login.login_required
def instrument(instrument_id):
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    # TODO: check instrument permissions
    return flask.render_template('instruments/instrument.html', instrument=instrument, ActionType=ActionType)


class InstrumentForm(FlaskForm):
    name = StringField(validators=[Length(min=1, max=100)])
    description = StringField()
    instrument_responsible_users = SelectMultipleField()
    is_markdown = BooleanField(default=None)


@frontend.route('/instruments/new', methods=['GET', 'POST'])
@flask_login.login_required
def new_instrument():
    if not flask_login.current_user.is_admin:
        return flask.abort(401)
    check_current_user_is_not_readonly()
    instrument_form = InstrumentForm()
    instrument_form.instrument_responsible_users.choices = [
        (str(user.id), user.name)
        for user in get_users()
    ]
    if instrument_form.validate_on_submit():
        if instrument_form.is_markdown.data:
            description_as_html = markdown_to_safe_html(instrument_form.description.data)
        else:
            description_as_html = None
        instrument = create_instrument(
            instrument_form.name.data,
            instrument_form.description.data,
            description_as_html=description_as_html
        )
        flask.flash('The instrument was created successfully.', 'success')
        instrument_responsible_user_ids = [
            int(user_id)
            for user_id in instrument_form.instrument_responsible_users.data
        ]
        set_instrument_responsible_users(instrument.id, instrument_responsible_user_ids)
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument.id))
    return flask.render_template(
        'instruments/instrument_form.html',
        submit_text='Create Instrument',
        instrument_form=instrument_form
    )


@frontend.route('/instruments/<int:instrument_id>/edit', methods=['GET', 'POST'])
@flask_login.login_required
def edit_instrument(instrument_id):
    try:
        instrument = get_instrument(instrument_id)
    except InstrumentDoesNotExistError:
        return flask.abort(404)
    check_current_user_is_not_readonly()
    if not flask_login.current_user.is_admin and flask_login.current_user not in instrument.responsible_users:
        return flask.abort(401)
    instrument_form = InstrumentForm()
    instrument_form.name.default = instrument.name
    instrument_form.description.default = instrument.description
    instrument_form.instrument_responsible_users.choices = [
        (str(user.id), user.name)
        for user in get_users()
    ]
    instrument_form.instrument_responsible_users.default = [
        str(user.id)
        for user in instrument.responsible_users
    ]

    if not instrument_form.is_submitted():
        instrument_form.is_markdown.data = (instrument.description_as_html is not None)
    if instrument_form.validate_on_submit():
        if instrument_form.is_markdown.data:
            description_as_html = markdown_to_safe_html(instrument_form.description.data)
        else:
            description_as_html = None
        update_instrument(
            instrument.id,
            instrument_form.name.data,
            instrument_form.description.data,
            description_as_html=description_as_html
        )
        flask.flash('The instrument was updated successfully.', 'success')
        instrument_responsible_user_ids = [
            int(user_id)
            for user_id in instrument_form.instrument_responsible_users.data
        ]
        set_instrument_responsible_users(instrument.id, instrument_responsible_user_ids)
        return flask.redirect(flask.url_for('.instrument', instrument_id=instrument.id))
    return flask.render_template(
        'instruments/instrument_form.html',
        submit_text='Update Instrument',
        instrument_form=instrument_form
    )
