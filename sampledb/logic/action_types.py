import dataclasses
import typing

from . import errors, components
from .utils import cache
from .. import db, models
from ..models import SciCatExportType


@dataclasses.dataclass(frozen=True)
class ActionType:
    """
    This class provides an immutable wrapper around models.actions.ActionType.
    """
    id: int
    name: typing.Dict[str, str]
    description: typing.Dict[str, str]
    object_name: typing.Dict[str, str]
    object_name_plural: typing.Dict[str, str]
    view_text: typing.Dict[str, str]
    perform_text: typing.Dict[str, str]
    admin_only: bool
    show_on_frontpage: bool
    show_in_navbar: bool
    show_in_object_filters: bool
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
    order_index: typing.Optional[int]
    usable_in_action_types: typing.List['ActionType'] = dataclasses.field(compare=False)
    fed_id: typing.Optional[int] = None
    component_id: typing.Optional[int] = None
    component: typing.Optional[components.Component] = None
    scicat_export_type: typing.Optional[SciCatExportType] = None

    # make fixed IDs available from wrapper
    SAMPLE_CREATION = models.ActionType.SAMPLE_CREATION
    MEASUREMENT = models.ActionType.MEASUREMENT
    SIMULATION = models.ActionType.SIMULATION
    TEMPLATE = models.ActionType.TEMPLATE

    @classmethod
    def from_database(
            cls,
            action_type: models.ActionType,
            previously_wrapped_action_types: typing.Optional[typing.Dict[int, 'ActionType']] = None
    ) -> 'ActionType':
        if previously_wrapped_action_types is None:
            previously_wrapped_action_types = {}
        wrapped_action_type = ActionType(
            id=action_type.id,
            name=action_type.name,
            description=action_type.description,
            object_name=action_type.object_name,
            object_name_plural=action_type.object_name_plural,
            view_text=action_type.view_text,
            perform_text=action_type.perform_text,
            admin_only=action_type.admin_only,
            show_on_frontpage=action_type.show_on_frontpage,
            show_in_navbar=action_type.show_in_navbar,
            show_in_object_filters=action_type.show_in_object_filters,
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
            order_index=action_type.order_index,
            usable_in_action_types=[],
            fed_id=action_type.fed_id,
            component_id=action_type.component_id,
            component=components.Component.from_database(action_type.component) if action_type.component is not None else None,
            scicat_export_type=action_type.scicat_export_type
        )
        previously_wrapped_action_types[action_type.id] = wrapped_action_type
        # add referenced action types to list after wrapping to support cyclic references
        if action_type.usable_in_action_types:
            for other_action_type in action_type.usable_in_action_types:
                if other_action_type.id in previously_wrapped_action_types:
                    wrapped_action_type.usable_in_action_types.append(previously_wrapped_action_types[other_action_type.id])
                else:
                    wrapped_other_action_type = ActionType.from_database(other_action_type, previously_wrapped_action_types)
                    wrapped_action_type.usable_in_action_types.append(wrapped_other_action_type)
        return wrapped_action_type

    def __repr__(self) -> str:
        return f"<{type(self).__name__}(id={self.id!r})>"


@cache
def check_action_type_exists(
        action_type_id: int
) -> None:
    """
    Check whether an action type with the given action type ID exists.

    :param action_type_id: the ID of an existing action type
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    if not db.session.query(db.exists().where(models.ActionType.id == action_type_id)).scalar():
        raise errors.ActionTypeDoesNotExistError()


def get_action_type(action_type_id: int, component_id: typing.Optional[int] = None) -> ActionType:
    """
    Returns the action type with the given action type ID or composite federation ID.

    :param action_type_id: the ID of an existing action type or ID on other component
        if composite federation ID is used
    :param component_id: optional component ID, if the composite federation ID is used
    :return: the action type
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    if component_id is None:
        action_type = models.ActionType.query.filter_by(id=action_type_id).first()
    else:
        # ensure that the component can be found
        components.check_component_exists(component_id)
        action_type = models.ActionType.query.filter_by(fed_id=action_type_id, component_id=component_id).first()
    if action_type is None:
        raise errors.ActionTypeDoesNotExistError()
    return ActionType.from_database(action_type)


def get_action_types(
        filter_fed_defaults: bool = False
) -> typing.List[ActionType]:
    """
    Return the list of all existing action types.

    :return: the action types
    """
    query = models.ActionType.query

    if filter_fed_defaults:
        query = query.filter(db.or_(models.ActionType.fed_id > 0, models.ActionType.fed_id.is_(None)))

    query = query.order_by(db.nulls_last(models.ActionType.order_index), models.ActionType.id)

    return [
        ActionType.from_database(action_type)
        for action_type in query.all()
    ]


@typing.overload
def create_action_type(
        *,
        admin_only: bool,
        show_on_frontpage: bool,
        show_in_navbar: bool,
        show_in_object_filters: bool,
        enable_labels: bool,
        enable_files: bool,
        enable_locations: bool,
        enable_publications: bool,
        enable_comments: bool,
        enable_activity_log: bool,
        enable_related_objects: bool,
        enable_project_link: bool,
        enable_instrument_link: bool,
        disable_create_objects: bool,
        is_template: bool,
        usable_in_action_type_ids: typing.Sequence[int] = (),
        fed_id: None = None,
        component_id: None = None,
        scicat_export_type: typing.Optional[SciCatExportType] = None
) -> ActionType:
    ...


@typing.overload
def create_action_type(
        *,
        admin_only: bool,
        show_on_frontpage: bool,
        show_in_navbar: bool,
        show_in_object_filters: bool,
        enable_labels: bool,
        enable_files: bool,
        enable_locations: bool,
        enable_publications: bool,
        enable_comments: bool,
        enable_activity_log: bool,
        enable_related_objects: bool,
        enable_project_link: bool,
        enable_instrument_link: bool,
        disable_create_objects: bool,
        is_template: bool,
        usable_in_action_type_ids: typing.Sequence[int] = (),
        fed_id: int,
        component_id: int,
        scicat_export_type: typing.Optional[SciCatExportType] = None
) -> ActionType:
    ...


def create_action_type(
        *,
        admin_only: bool,
        show_on_frontpage: bool,
        show_in_navbar: bool,
        show_in_object_filters: bool,
        enable_labels: bool,
        enable_files: bool,
        enable_locations: bool,
        enable_publications: bool,
        enable_comments: bool,
        enable_activity_log: bool,
        enable_related_objects: bool,
        enable_project_link: bool,
        enable_instrument_link: bool,
        disable_create_objects: bool,
        is_template: bool,
        usable_in_action_type_ids: typing.Sequence[int] = (),
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None,
        scicat_export_type: typing.Optional[SciCatExportType] = None
) -> ActionType:
    """
    Create a new action type.

    :param admin_only: whether actions of this type can only be created by administrators
    :param show_on_frontpage: whether this action type should be shown on the frontpage
    :param show_in_navbar: whether actions of this type should be shown in the navbar
    :param show_in_object_filters: whether this action type should be shown in object filters
    :param enable_labels: whether labels should be enabled for actions of this type
    :param enable_files: whether file uploads should be enabled for actions of this type
    :param enable_locations: whether locations and responsible users should be enabled for actions of this type
    :param enable_publications: whether publications should be enabled for actions of this type
    :param enable_comments: whether comments should be enabled for actions of this type
    :param enable_activity_log: whether the activity log should be enabled for actions of this type
    :param enable_related_objects: whether showing related objects should be enabled for actions of this type
    :param enable_project_link: whether objects created with actions of this type can be linked to a project group
    :param enable_instrument_link: objects created with actions of this type can be linked to an instrument
    :param disable_create_objects: whether the creation of objects with this action type is enabled
    :param is_template: whether this action type can be embedded as a template in actions of other types
    :param usable_in_action_type_ids: sequence of all action types for which objects created with this action type
        should have a "Use in" button
    :param fed_id: action type ID on other database, if action type is imported
    :param component_id: component ID of the component this action type is imported from
    :param scicat_export_type: the SciCat type to use during export, or None
    :return: the created action type
    """
    assert (component_id is None) == (fed_id is None)

    if component_id is not None:
        # ensure that the component can be found
        components.check_component_exists(component_id)

    action_type = models.ActionType(
        admin_only=admin_only,
        show_on_frontpage=show_on_frontpage,
        show_in_navbar=show_in_navbar,
        show_in_object_filters=show_in_object_filters,
        enable_labels=enable_labels,
        enable_files=enable_files,
        enable_locations=enable_locations,
        enable_publications=enable_publications,
        enable_comments=enable_comments,
        enable_activity_log=enable_activity_log,
        enable_related_objects=enable_related_objects,
        enable_project_link=enable_project_link,
        enable_instrument_link=enable_instrument_link,
        disable_create_objects=disable_create_objects,
        is_template=is_template,
        order_index=None,
        usable_in_action_types=[
            models.ActionType.query.filter_by(id=action_type_id).first()
            for action_type_id in usable_in_action_type_ids
        ],
        fed_id=fed_id,
        component_id=component_id,
        scicat_export_type=scicat_export_type
    )
    db.session.add(action_type)
    db.session.commit()
    return ActionType.from_database(action_type)


def update_action_type(
        *,
        action_type_id: int,
        admin_only: bool,
        show_on_frontpage: bool,
        show_in_navbar: bool,
        show_in_object_filters: bool,
        enable_labels: bool,
        enable_files: bool,
        enable_locations: bool,
        enable_publications: bool,
        enable_comments: bool,
        enable_activity_log: bool,
        enable_related_objects: bool,
        enable_project_link: bool,
        enable_instrument_link: bool,
        disable_create_objects: bool,
        is_template: bool,
        usable_in_action_type_ids: typing.Sequence[int] = (),
        scicat_export_type: typing.Optional[SciCatExportType] = None
) -> ActionType:
    """
    Update an existing action type.

    :param action_type_id: the ID of an existing action type
    :param admin_only: whether actions of this type can only be created by administrators
    :param show_on_frontpage: whether this action type should be shown on the frontpage
    :param show_in_navbar: whether actions of this type should be shown in the navbar
    :param show_in_object_filters: whether this action type should be shown in object filters
    :param enable_labels: whether labels should be enabled for actions of this type
    :param enable_files: whether file uploads should be enabled for actions of this type
    :param enable_locations: whether locations and responsible users should be enabled for actions of this type
    :param enable_publications: whether publications should be enabled for actions of this type
    :param enable_comments: whether comments should be enabled for actions of this type
    :param enable_activity_log: whether the activity log should be enabled for actions of this type
    :param enable_related_objects: whether showing related objects should be enabled for actions of this type
    :param enable_project_link: objects created with actions of this type can be linked to a project group
    :param enable_instrument_link: objects created with actions of this type can be linked to an instrument
    :param disable_create_objects: whether the creation of objects with this action type is enabled
    :param is_template: whether this action type can be embedded as a template in actions of other types
    :param usable_in_action_type_ids: sequence of all action types for which objects created with this action type
        should have a "Use in" button
    :param scicat_export_type: the SciCat type to use during export, or None
    :return: the created action type
    :raise errors.ActionTypeDoesNotExistError: when no action type with the
        given action type ID exists
    """
    action_type = models.ActionType.query.filter_by(id=action_type_id).first()
    if action_type is None:
        raise errors.ActionTypeDoesNotExistError()
    action_type.admin_only = admin_only
    action_type.show_on_frontpage = show_on_frontpage
    action_type.show_in_navbar = show_in_navbar
    action_type.show_in_object_filters = show_in_object_filters
    action_type.enable_labels = enable_labels
    action_type.enable_files = enable_files
    action_type.enable_locations = enable_locations
    action_type.enable_publications = enable_publications
    action_type.enable_comments = enable_comments
    action_type.enable_activity_log = enable_activity_log
    action_type.enable_related_objects = enable_related_objects
    action_type.enable_project_link = enable_project_link
    action_type.enable_instrument_link = enable_instrument_link
    action_type.disable_create_objects = disable_create_objects
    action_type.is_template = is_template
    usable_in_action_types = [
        models.ActionType.query.filter_by(id=action_type_id).first()
        for action_type_id in usable_in_action_type_ids
    ]
    action_type.usable_in_action_types = [
        other_action_type
        for other_action_type in usable_in_action_types
        if other_action_type is not None
    ]
    action_type.scicat_export_type = scicat_export_type
    db.session.add(action_type)
    db.session.commit()
    return ActionType.from_database(action_type)


def is_usable_in_action_types_table_empty() -> bool:
    """
    Check if the usable in action types table has entries.
    """
    return db.session.query(models.actions.usable_in_action_types_table).first() is None


def set_action_types_order(action_type_id_list: typing.List[int]) -> None:
    """
    Sets the `order_index` for all action types in the index_list, therefore the order in the list is used.

    :param action_type_id_list: list of action type ids
    """
    for i, action_type_id in enumerate(action_type_id_list):
        action_type = models.ActionType.query.filter_by(id=action_type_id).first()
        if action_type is not None:
            action_type.order_index = i
    db.session.commit()


def add_action_type_to_order(action_type: ActionType) -> None:
    """
    Insert an action type into the current sort order.

    :param action_type: the action type to insert
    """
    if action_type.order_index is not None:
        # action type already has a place in the current sort order
        return
    action_types_before: typing.List[ActionType] = []
    action_types_after: typing.List[ActionType] = []
    action_types = [
        ActionType.from_database(other_action_type)
        for other_action_type in models.ActionType.query.filter(models.ActionType.order_index != db.null()).order_by(models.ActionType.order_index).all()
    ]
    if action_types:
        # check if local action types are listed before imported action types
        local_action_types = [
            other_action_type
            for other_action_type in action_types
            if (other_action_type.fed_id is None)
        ]
        imported_action_types = [
            other_action_type
            for other_action_type in action_types
            if (other_action_type.fed_id is not None)
        ]
        local_before_imported = (max(
            typing.cast(int, other_action_type.order_index)
            for other_action_type in local_action_types
        ) < min(
            typing.cast(int, other_action_type.order_index)
            for other_action_type in imported_action_types
        )) if imported_action_types else True
        if local_before_imported:
            if action_type.fed_id is None:
                action_types = local_action_types
                action_types_after = imported_action_types + action_types_after
            else:
                action_types_before = action_types_before + local_action_types
                action_types = imported_action_types
    if action_types:
        # check if action types are listed in order of their english names
        english_names = [
            other_action_type.name.get('en', '').lower()
            for other_action_type in action_types
        ]
        english_lexicographical_order = english_names == sorted(english_names)
        if english_lexicographical_order:
            english_name = action_type.name.get('en', '').lower()
            action_types_before = action_types_before + [
                other_action_type
                for other_action_type in action_types
                if other_action_type.name.get('en', '').lower() < english_name
            ]
            action_types_after = [
                other_action_type
                for other_action_type in action_types
                if other_action_type.name.get('en', '').lower() > english_name
            ] + action_types_after
            action_types = [
                other_action_type
                for other_action_type in action_types
                if other_action_type.name.get('en', '').lower() == english_name
            ]
    # update order indices
    index_list = [
        other_action_type.id
        for other_action_type in (
            action_types_before + action_types + [action_type] + action_types_after
        )
    ]
    set_action_types_order(index_list)
