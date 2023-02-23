import base64
import typing

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_bool, _get_str, _get_dict
from ..languages import get_languages, get_language, get_language_by_lang_code
from ..instruments import get_instrument, get_mutable_instrument, create_instrument, Instrument
from ..instrument_translations import set_instrument_translation, get_instrument_translations_for_instrument
from ..markdown_images import get_markdown_image, find_referenced_markdown_images
from ..components import Component
from .. import errors, fed_logs, markdown_to_html
from ... import db


class InstrumentRef(typing.TypedDict):
    instrument_id: int
    component_uuid: str


class InstrumentTranslationData(typing.TypedDict):
    language_id: int
    name: str
    description: str
    short_description: str
    notes: str


class InstrumentData(typing.TypedDict):
    fed_id: int
    component_uuid: str
    description_is_markdown: bool
    short_description_is_markdown: bool
    notes_is_markdown: bool
    is_hidden: bool
    users_can_create_log_entries: bool
    users_can_view_log_entries: bool
    create_log_entry_default: bool
    translations: typing.List[InstrumentTranslationData]


class SharedInstrumentTranslationData(typing.TypedDict):
    name: str
    description: str
    short_description: str
    notes: str


class SharedInstrumentData(typing.TypedDict):
    instrument_id: int
    component_uuid: str
    description_is_markdown: bool
    short_description_is_markdown: bool
    notes_is_markdown: bool
    is_hidden: bool
    translations: typing.Optional[typing.Dict[str, SharedInstrumentTranslationData]]


def parse_instrument(
        instrument_data: typing.Dict[str, typing.Any]
) -> InstrumentData:
    fed_id = _get_id(instrument_data.get('instrument_id'))
    uuid = _get_uuid(instrument_data.get('component_uuid'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError(f'Invalid update for local instrument {fed_id}')
    result = InstrumentData(
        fed_id=fed_id,
        component_uuid=uuid,
        description_is_markdown=_get_bool(instrument_data.get('description_is_markdown'), default=False),
        is_hidden=_get_bool(instrument_data.get('is_hidden'), default=False),
        short_description_is_markdown=_get_bool(instrument_data.get('short_description_is_markdown'), default=False),
        notes_is_markdown=_get_bool(instrument_data.get('notes_is_markdown'), default=False),
        users_can_create_log_entries=False,
        users_can_view_log_entries=False,
        create_log_entry_default=False,
        translations=[]
    )

    allowed_language_ids = [language.id for language in get_languages(only_enabled_for_input=False)]

    translation_data = _get_dict(instrument_data.get('translations'))
    if translation_data is not None:
        for lang_code, translation in translation_data.items():
            try:
                language = get_language_by_lang_code(lang_code.lower())
            except errors.LanguageDoesNotExistError:
                continue
            language_id = language.id
            if language_id not in allowed_language_ids:
                continue

            result['translations'].append(InstrumentTranslationData(
                language_id=language_id,
                name=_get_str(translation.get('name'), default=''),
                description=_get_str(translation.get('description'), default=''),
                short_description=_get_str(translation.get('short_description'), default=''),
                notes=_get_str(translation.get('notes'), default='')
            ))
    return result


def import_instrument(
        instrument_data: InstrumentData,
        component: Component
) -> Instrument:
    component_id = _get_or_create_component_id(instrument_data['component_uuid'])
    # component_id will only be None if this would import a local instrument
    assert component_id is not None
    try:
        mutable_instrument = get_mutable_instrument(instrument_data['fed_id'], component_id)

        ignored_keys = {
            'fed_id',
            'component_uuid',
            'translations'
        }
        if any(
                value != getattr(mutable_instrument, key)
                for key, value in instrument_data.items()
                if key not in ignored_keys
        ):
            mutable_instrument.description_is_markdown = instrument_data['description_is_markdown']
            mutable_instrument.is_hidden = instrument_data['is_hidden']
            mutable_instrument.short_description_is_markdown = instrument_data['short_description_is_markdown']
            db.session.commit()
            fed_logs.update_instrument(mutable_instrument.id, component.id)
        instrument = Instrument.from_database(mutable_instrument)
    except errors.InstrumentDoesNotExistError:
        instrument = create_instrument(
            fed_id=instrument_data['fed_id'],
            component_id=component_id,
            description_is_markdown=instrument_data['description_is_markdown'],
            is_hidden=instrument_data['is_hidden'],
            short_description_is_markdown=instrument_data['short_description_is_markdown'],
            notes_is_markdown=instrument_data['notes_is_markdown'],
            users_can_create_log_entries=instrument_data['users_can_create_log_entries'],
            users_can_view_log_entries=instrument_data['users_can_view_log_entries'],
            create_log_entry_default=instrument_data['create_log_entry_default']
        )
        fed_logs.import_instrument(instrument.id, component.id)

    for instrument_translation in instrument_data['translations']:
        set_instrument_translation(
            instrument_id=instrument.id,
            language_id=instrument_translation['language_id'],
            name=instrument_translation['name'],
            description=instrument_translation['description'],
            short_description=instrument_translation['short_description'],
            notes=instrument_translation['notes']
        )

    return instrument


def parse_import_instrument(
        instrument_data: typing.Dict[str, typing.Any],
        component: Component
) -> Instrument:
    return import_instrument(parse_instrument(instrument_data), component)


def _get_or_create_instrument_id(
        instrument_data: typing.Optional[InstrumentRef]
) -> typing.Optional[int]:
    if instrument_data is None:
        return None
    component_id = _get_or_create_component_id(instrument_data['component_uuid'])
    try:
        instrument = get_instrument(instrument_data['instrument_id'], component_id)
    except errors.InstrumentDoesNotExistError:
        assert component_id is not None
        instrument = create_instrument(fed_id=instrument_data['instrument_id'], component_id=component_id)
        fed_logs.create_ref_instrument(instrument.id, component_id)
    return instrument.id


def _parse_instrument_ref(
        instrument_data: typing.Optional[typing.Union[InstrumentRef, typing.Dict[str, typing.Any]]]
) -> typing.Optional[InstrumentRef]:
    if instrument_data is None:
        return None
    instrument_id = _get_id(instrument_data.get('instrument_id'))
    component_uuid = _get_uuid(instrument_data.get('component_uuid'))
    return InstrumentRef(
        instrument_id=instrument_id,
        component_uuid=component_uuid
    )


def shared_instrument_preprocessor(
        instrument_id: int,
        _component: Component,
        _refs: typing.List[typing.Tuple[str, int]],
        markdown_images: typing.Dict[str, str]
) -> typing.Optional[SharedInstrumentData]:
    instrument = get_instrument(instrument_id)
    if instrument.component_id is not None:
        return None
    translations_data = {}
    try:
        translations = get_instrument_translations_for_instrument(instrument_id)
        for translation in translations:
            lang_code = get_language(translation.language_id).lang_code

            description = translation.description
            markdown_as_html = markdown_to_html.markdown_to_safe_html(description)
            for file_name in find_referenced_markdown_images(markdown_as_html):
                markdown_image_b = get_markdown_image(file_name, None)
                description = description.replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                if markdown_image_b is not None and file_name not in markdown_images:
                    markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')

            short_description = translation.short_description
            markdown_as_html = markdown_to_html.markdown_to_safe_html(short_description)
            for file_name in find_referenced_markdown_images(markdown_as_html):
                markdown_image_b = get_markdown_image(file_name, None)
                short_description = short_description.replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                if markdown_image_b is not None and file_name not in markdown_images:
                    markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')

            notes = translation.notes
            markdown_as_html = markdown_to_html.markdown_to_safe_html(notes)
            for file_name in find_referenced_markdown_images(markdown_as_html):
                markdown_image_b = get_markdown_image(file_name, None)
                notes = notes.replace('/markdown_images/' + file_name, '/markdown_images/' + flask.current_app.config['FEDERATION_UUID'] + '/' + file_name)
                if markdown_image_b is not None and file_name not in markdown_images:
                    markdown_images[file_name] = base64.b64encode(markdown_image_b).decode('utf-8')

            translations_data[lang_code] = SharedInstrumentTranslationData(
                name=translation.name,
                description=description,
                short_description=short_description,
                notes=notes
            )
    except errors.InstrumentTranslationDoesNotExistError:
        translations_data = {}
    return SharedInstrumentData(
        instrument_id=instrument.id if instrument.fed_id is None else instrument.fed_id,
        component_uuid=flask.current_app.config['FEDERATION_UUID'] if instrument.component is None else instrument.component.uuid,
        description_is_markdown=instrument.description_is_markdown,
        notes_is_markdown=instrument.notes_is_markdown,
        is_hidden=instrument.is_hidden,
        short_description_is_markdown=instrument.short_description_is_markdown,
        translations=translations_data if translations_data else None
    )
