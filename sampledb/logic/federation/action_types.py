import typing

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_bool, _get_str, _get_dict
from ..languages import get_languages, get_language, get_language_by_lang_code
from ..action_types import ActionType, get_action_type, create_action_type, update_action_type
from ..action_type_translations import set_action_type_translation, get_action_type_translations_for_action_type
from ..components import Component
from .. import errors, fed_logs


class ActionTypeRef(typing.TypedDict):
    action_type_id: int
    component_uuid: str


class ActionTypeTranslationData(typing.TypedDict):
    language_id: int
    name: str
    description: str
    object_name: str
    object_name_plural: str
    view_text: str
    perform_text: str


class ActionTypeData(typing.TypedDict):
    fed_id: int
    component_uuid: str
    admin_only: bool
    enable_labels: bool
    enable_files: bool
    enable_locations: bool
    enable_publications: bool
    enable_comments: bool
    enable_activity_log: bool
    enable_related_objects: bool
    enable_project_link: bool
    enable_instrument_link: bool
    disable_create_objects: bool
    is_template: bool
    translations: typing.List[ActionTypeTranslationData]


class SharedActionTypeTranslationData(typing.TypedDict):
    name: str
    description: str
    object_name: str
    object_name_plural: str
    view_text: str
    perform_text: str


class SharedActionTypeData(typing.TypedDict):
    action_type_id: int
    component_uuid: str
    admin_only: bool
    enable_labels: bool
    enable_files: bool
    enable_locations: bool
    enable_publications: bool
    enable_comments: bool
    enable_activity_log: bool
    enable_related_objects: bool
    enable_project_link: bool
    enable_instrument_link: bool
    disable_create_objects: bool
    is_template: bool
    translations: typing.Optional[typing.Dict[str, SharedActionTypeTranslationData]]


def import_action_type(
        action_type_data: ActionTypeData,
        component: Component
) -> ActionType:
    component_id = _get_or_create_component_id(action_type_data['component_uuid'])
    # component_id will only be None if this would import a local action type
    assert component_id is not None

    try:
        action_type = get_action_type(action_type_data['fed_id'], component_id)

        ignored_keys = {
            'fed_id',
            'component_uuid',
            'translations'
        }
        if any(
                value != getattr(action_type, key)
                for key, value in action_type_data.items()
                if key not in ignored_keys
        ):
            update_action_type(
                action_type_id=action_type.id,
                admin_only=action_type_data['admin_only'],
                show_on_frontpage=False,
                show_in_navbar=False,
                show_in_object_filters=True,
                enable_labels=action_type_data['enable_labels'],
                enable_files=action_type_data['enable_files'],
                enable_locations=action_type_data['enable_locations'],
                enable_publications=action_type_data['enable_publications'],
                enable_comments=action_type_data['enable_comments'],
                enable_activity_log=action_type_data['enable_activity_log'],
                enable_related_objects=action_type_data['enable_related_objects'],
                enable_project_link=action_type_data['enable_project_link'],
                enable_instrument_link=action_type_data['enable_instrument_link'],
                disable_create_objects=action_type_data['disable_create_objects'],
                is_template=action_type_data['is_template'],
                scicat_export_type=None
            )
            fed_logs.update_action_type(action_type.id, component.id)
    except errors.ActionTypeDoesNotExistError:
        action_type = create_action_type(
            fed_id=action_type_data['fed_id'],
            component_id=component_id,
            admin_only=action_type_data['admin_only'],
            show_on_frontpage=False,
            show_in_navbar=False,
            show_in_object_filters=True,
            enable_labels=action_type_data['enable_labels'],
            enable_files=action_type_data['enable_files'],
            enable_locations=action_type_data['enable_locations'],
            enable_publications=action_type_data['enable_publications'],
            enable_comments=action_type_data['enable_comments'],
            enable_activity_log=action_type_data['enable_activity_log'],
            enable_related_objects=action_type_data['enable_related_objects'],
            enable_project_link=action_type_data['enable_project_link'],
            enable_instrument_link=action_type_data['enable_instrument_link'],
            disable_create_objects=action_type_data['disable_create_objects'],
            is_template=action_type_data['is_template'],
            scicat_export_type=None
        )
        fed_logs.import_action_type(action_type.id, component.id)

    for action_type_translation in action_type_data['translations']:
        set_action_type_translation(
            action_type_id=action_type.id,
            language_id=action_type_translation['language_id'],
            name=action_type_translation['name'],
            description=action_type_translation['description'],
            object_name=action_type_translation['object_name'],
            object_name_plural=action_type_translation['object_name_plural'],
            view_text=action_type_translation['view_text'],
            perform_text=action_type_translation['perform_text']
        )
    return action_type


def parse_action_type(
        action_type_data: typing.Dict[str, typing.Any]
) -> ActionTypeData:
    fed_id = _get_id(action_type_data.get('action_type_id'), special_values=[ActionType.SAMPLE_CREATION, ActionType.MEASUREMENT, ActionType.SIMULATION, ActionType.TEMPLATE])
    uuid = _get_uuid(action_type_data.get('component_uuid'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError(f'Invalid update for local action type {fed_id}')
    result = ActionTypeData(
        fed_id=fed_id,
        component_uuid=uuid,
        admin_only=_get_bool(action_type_data.get('admin_only'), default=True),
        enable_labels=_get_bool(action_type_data.get('enable_labels'), default=False),
        enable_files=_get_bool(action_type_data.get('enable_files'), default=False),
        enable_locations=_get_bool(action_type_data.get('enable_locations'), default=False),
        enable_publications=_get_bool(action_type_data.get('enable_publications'), default=False),
        enable_comments=_get_bool(action_type_data.get('enable_comments'), default=False),
        enable_activity_log=_get_bool(action_type_data.get('enable_activity_log'), default=False),
        enable_related_objects=_get_bool(action_type_data.get('enable_related_objects'), default=False),
        enable_project_link=_get_bool(action_type_data.get('enable_project_link'), default=False),
        enable_instrument_link=_get_bool(action_type_data.get('enable_instrument_link'), default=False),
        disable_create_objects=_get_bool(action_type_data.get('disable_create_objects'), default=False),
        is_template=_get_bool(action_type_data.get('is_template'), default=False),
        translations=[]
    )

    allowed_language_ids = [language.id for language in get_languages(only_enabled_for_input=False)]

    translation_data = _get_dict(action_type_data.get('translations'))
    if translation_data is not None:
        for lang_code, translation in translation_data.items():
            try:
                language = get_language_by_lang_code(lang_code.lower())
            except errors.LanguageDoesNotExistError:
                continue
            language_id = language.id
            if language_id not in allowed_language_ids:
                continue

            result['translations'].append(ActionTypeTranslationData(
                language_id=language_id,
                name=_get_str(translation.get('name'), default=''),
                description=_get_str(translation.get('description'), default=''),
                object_name=_get_str(translation.get('object_name'), default=''),
                object_name_plural=_get_str(translation.get('object_name_plural'), default=''),
                view_text=_get_str(translation.get('view_text'), default=''),
                perform_text=_get_str(translation.get('perform_text'), default='')
            ))
    return result


def parse_import_action_type(
        action_type_data: typing.Dict[str, typing.Any],
        component: Component
) -> ActionType:
    return import_action_type(parse_action_type(action_type_data), component)


def _parse_action_type_ref(
        action_type_data: typing.Union[ActionTypeRef, typing.Dict[str, typing.Any]]
) -> ActionTypeRef:
    action_type_id = _get_id(
        action_type_data.get('action_type_id'),
        special_values=[
            ActionType.SAMPLE_CREATION,
            ActionType.MEASUREMENT,
            ActionType.SIMULATION,
            ActionType.TEMPLATE
        ]
    )
    component_uuid = _get_uuid(action_type_data.get('component_uuid'))
    return ActionTypeRef(
        action_type_id=action_type_id,
        component_uuid=component_uuid
    )


def _get_or_create_action_type_id(
        action_type_data: typing.Optional[ActionTypeRef]
) -> typing.Optional[int]:
    if action_type_data is None:
        return None
    component_id = _get_or_create_component_id(action_type_data['component_uuid'])
    try:
        action_type = get_action_type(action_type_data['action_type_id'], component_id)
    except errors.ActionTypeDoesNotExistError:
        assert component_id is not None
        action_type = create_action_type(
            admin_only=True,
            show_on_frontpage=False,
            show_in_navbar=False,
            show_in_object_filters=True,
            enable_labels=False,
            enable_files=False,
            enable_locations=False,
            enable_publications=False,
            enable_comments=False,
            enable_activity_log=False,
            enable_related_objects=False,
            enable_project_link=False,
            enable_instrument_link=False,
            disable_create_objects=False,
            is_template=False,
            fed_id=action_type_data['action_type_id'],
            component_id=component_id,
            scicat_export_type=None
        )
        fed_logs.create_ref_action_type(action_type.id, component_id)
    return action_type.id


def shared_action_type_preprocessor(
        action_type_id: int,
        _component: Component,
        _refs: typing.List[typing.Tuple[str, int]],
        _markdown_images: typing.Dict[str, str]
) -> typing.Optional[SharedActionTypeData]:
    action_type = get_action_type(action_type_id)
    if action_type.component_id is not None:
        return None
    translations_data = {}
    try:
        translations = get_action_type_translations_for_action_type(action_type.id)
        for translation in translations:
            lang_code = get_language(translation.language_id).lang_code
            translations_data[lang_code] = SharedActionTypeTranslationData(
                name=translation.name,
                description=translation.description,
                object_name=translation.object_name,
                object_name_plural=translation.object_name_plural,
                view_text=translation.view_text,
                perform_text=translation.perform_text
            )
    except errors.ActionTypeTranslationDoesNotExistError:
        translations_data = {}
    return SharedActionTypeData(
        action_type_id=action_type.id if action_type.component_id is None else action_type.fed_id,
        component_uuid=flask.current_app.config['FEDERATION_UUID'] if action_type.component is None else action_type.component.uuid,
        admin_only=action_type.admin_only,
        enable_labels=action_type.enable_labels,
        enable_files=action_type.enable_files,
        enable_locations=action_type.enable_locations,
        enable_publications=action_type.enable_publications,
        enable_comments=action_type.enable_comments,
        enable_activity_log=action_type.enable_activity_log,
        enable_related_objects=action_type.enable_related_objects,
        enable_project_link=action_type.enable_project_link,
        enable_instrument_link=action_type.enable_instrument_link,
        disable_create_objects=action_type.disable_create_objects,
        is_template=action_type.is_template,
        translations=translations_data if translations_data else None
    )
