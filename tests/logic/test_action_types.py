import uuid

import pytest

import sampledb
from sampledb.logic import components, errors, action_types, action_type_translations, languages


def test_check_action_type_exists():
    action_type = action_types.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        show_in_object_filters=False,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
        enable_instrument_link=False,
        disable_create_objects=False,
        is_template=False
    )
    action_types.check_action_type_exists(action_type.id)
    with pytest.raises(errors.ActionTypeDoesNotExistError):
        action_types.check_action_type_exists(action_type.id + 1)


def test_add_action_type_to_order():
    component = components.add_component(
        uuid=str(uuid.uuid4())
    )
    local_action_types = action_types.get_action_types() + [
        action_types.create_action_type(
            admin_only=False,
            show_on_frontpage=True,
            show_in_navbar=True,
            show_in_object_filters=False,
            enable_labels=True,
            enable_files=True,
            enable_locations=True,
            enable_publications=True,
            enable_comments=True,
            enable_activity_log=True,
            enable_related_objects=True,
            enable_project_link=True,
            enable_instrument_link=False,
            disable_create_objects=False,
            is_template=False
        )
        for _ in range(10)
    ]
    for i, action_type in enumerate(local_action_types):
        action_type_translations.set_action_type_translation(
            action_type_id=action_type.id,
            language_id=languages.Language.ENGLISH,
            name="Local Action Type " + chr(ord('A') + i),
            description='',
            object_name='Object',
            object_name_plural='Objects',
            view_text='View Objects',
            perform_text='Create Object'
        )

    action_types.set_action_types_order(
        [
            action_type.id
            for action_type in local_action_types
        ]
    )
    ordered_action_types = action_types.get_action_types()
    ordered_action_type_ids = [
        action_type.id
        for action_type in ordered_action_types
    ]
    assert ordered_action_type_ids == [
        action_type.id
        for action_type in local_action_types
    ]

    new_local_action_type_1 = action_types.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        show_in_object_filters=False,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
        enable_instrument_link=False,
        disable_create_objects=False,
        is_template=False
    )
    action_type_translations.set_action_type_translation(
        action_type_id=new_local_action_type_1.id,
        language_id=languages.Language.ENGLISH,
        name='Local Action Type A2',
        description='',
        object_name='Object',
        object_name_plural='Objects',
        view_text='View Objects',
        perform_text='Create Object'
    )
    new_local_action_type_1 = action_types.get_action_type(new_local_action_type_1.id)
    action_types.add_action_type_to_order(new_local_action_type_1)

    ordered_action_types = action_types.get_action_types()
    ordered_action_type_ids = [
        action_type.id
        for action_type in ordered_action_types
    ]
    assert ordered_action_type_ids == [local_action_types[0].id, new_local_action_type_1.id] + [
        action_type.id
        for action_type in local_action_types[1:]
    ]
    new_imported_action_type_1 = action_types.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        show_in_object_filters=False,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
        enable_instrument_link=False,
        disable_create_objects=False,
        is_template=False,
        fed_id=101,
        component_id=component.id
    )
    action_type_translations.set_action_type_translation(
        action_type_id=new_imported_action_type_1.id,
        language_id=languages.Language.ENGLISH,
        name='Imported Action Type B2',
        description='',
        object_name='Object',
        object_name_plural='Objects',
        view_text='View Objects',
        perform_text='Create Object'
    )
    new_imported_action_type_1 = action_types.get_action_type(new_imported_action_type_1.id)
    action_types.add_action_type_to_order(new_imported_action_type_1)

    ordered_action_types = action_types.get_action_types()
    ordered_action_type_ids = [
        action_type.id
        for action_type in ordered_action_types
    ]
    assert ordered_action_type_ids == [local_action_types[0].id, new_local_action_type_1.id] + [
        action_type.id
        for action_type in local_action_types[1:]
    ] + [new_imported_action_type_1.id]

    imported_action_types = [
        action_types.create_action_type(
            admin_only=False,
            show_on_frontpage=True,
            show_in_navbar=True,
            show_in_object_filters=False,
            enable_labels=True,
            enable_files=True,
            enable_locations=True,
            enable_publications=True,
            enable_comments=True,
            enable_activity_log=True,
            enable_related_objects=True,
            enable_project_link=True,
            enable_instrument_link=False,
            disable_create_objects=False,
            is_template=False,
            fed_id=i,
            component_id=component.id
        )
        for i in range(10)
    ]

    for i, action_type in enumerate(imported_action_types):
        action_type_translations.set_action_type_translation(
            action_type_id=action_type.id,
            language_id=languages.Language.ENGLISH,
            name="Imported Action Type " + chr(ord('A') + i),
            description='',
            object_name='Object',
            object_name_plural='Objects',
            view_text='View Objects',
            perform_text='Create Object'
        )
    action_types.set_action_types_order([local_action_types[0].id, new_local_action_type_1.id] + [
            action_type.id
            for action_type in local_action_types[1:]
        ] + [imported_action_types[0].id, imported_action_types[1].id, new_imported_action_type_1.id] + [
            action_type.id
            for action_type in imported_action_types[2:]
        ]
    )
    ordered_action_types = action_types.get_action_types()
    ordered_action_type_ids = [
        action_type.id
        for action_type in ordered_action_types
    ]
    assert ordered_action_type_ids == [local_action_types[0].id, new_local_action_type_1.id] + [
            action_type.id
            for action_type in local_action_types[1:]
        ] + [imported_action_types[0].id, imported_action_types[1].id, new_imported_action_type_1.id] + [
            action_type.id
            for action_type in imported_action_types[2:]
        ]

    new_local_action_type_2 = action_types.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        show_in_object_filters=False,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
        enable_instrument_link=False,
        disable_create_objects=False,
        is_template=False
    )
    action_type_translations.set_action_type_translation(
        action_type_id=new_local_action_type_2.id,
        language_id=languages.Language.ENGLISH,
        name='Local Action Type A3',
        description='',
        object_name='Object',
        object_name_plural='Objects',
        view_text='View Objects',
        perform_text='Create Object'
    )
    new_local_action_type_2 = action_types.get_action_type(new_local_action_type_2.id)
    action_types.add_action_type_to_order(new_local_action_type_2)

    ordered_action_types = action_types.get_action_types()
    ordered_action_type_ids = [
        action_type.id
        for action_type in ordered_action_types
    ]
    assert ordered_action_type_ids == [local_action_types[0].id, new_local_action_type_1.id, new_local_action_type_2.id] + [
        action_type.id
        for action_type in local_action_types[1:]
    ] + [imported_action_types[0].id, imported_action_types[1].id, new_imported_action_type_1.id] + [
        action_type.id
        for action_type in imported_action_types[2:]
    ]

    new_imported_action_type_2 = action_types.create_action_type(
        admin_only=False,
        show_on_frontpage=True,
        show_in_navbar=True,
        show_in_object_filters=False,
        enable_labels=True,
        enable_files=True,
        enable_locations=True,
        enable_publications=True,
        enable_comments=True,
        enable_activity_log=True,
        enable_related_objects=True,
        enable_project_link=True,
        enable_instrument_link=False,
        disable_create_objects=False,
        is_template=False,
        fed_id=100,
        component_id=component.id
    )
    action_type_translations.set_action_type_translation(
        action_type_id=new_imported_action_type_2.id,
        language_id=languages.Language.ENGLISH,
        name='Imported Action Type B3',
        description='',
        object_name='Object',
        object_name_plural='Objects',
        view_text='View Objects',
        perform_text='Create Object'
    )
    new_imported_action_type_2 = action_types.get_action_type(new_imported_action_type_2.id)
    action_types.add_action_type_to_order(new_imported_action_type_2)

    ordered_action_types = action_types.get_action_types()
    ordered_action_type_ids = [
        action_type.id
        for action_type in ordered_action_types
    ]
    assert ordered_action_type_ids == [local_action_types[0].id, new_local_action_type_1.id, new_local_action_type_2.id] + [
        action_type.id
        for action_type in local_action_types[1:]
    ] + [imported_action_types[0].id, imported_action_types[1].id] + [new_imported_action_type_1.id, new_imported_action_type_2.id] + [
        action_type.id
        for action_type in imported_action_types[2:]
    ]
