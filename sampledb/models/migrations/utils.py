# coding: utf-8
"""

"""

import importlib
import sys
import typing

from ... import db


def should_skip_by_index(db: typing.Any, index: int) -> bool:
    """
    Returns whether or not a migration should be skipped due to its index.

    :param db: the database
    :param index: the migration index to check
    :return: whether or not the migration should be skipped
    """
    # migration 0 creates the migration_index table, so it cannot be skipped
    # by index as the table might not exist yet
    if index == 0:
        return False

    return db.session.execute(
        db.text("""
        SELECT migration_index
        FROM migration_index
        WHERE migration_index >= :index
        """),
        {'index': index}
    ).first() is not None


def update_migration_index(db: typing.Any, index: int) -> None:
    """
    Set the database's migration index to the given index.

    This function also ensures that the migration index can only ever be
    increased and fails with an assertion error otherwise.

    :param db: the database
    :param index: the new migration index
    """
    # migration 0 creates the migration_index table and sets it to 0
    if index == 0:
        return

    assert db.session.execute(
        db.text("""
        UPDATE migration_index
        SET migration_index = :index
        WHERE migration_index < :index
        """),
        {"index": index}
    ).rowcount == 1


def get_migrations() -> typing.List[typing.Tuple[int, str, typing.Callable[[typing.Any], bool]]]:
    """
    Finds migrations and returns them sorted by their index.

    :return: A list of migrations, with each migration as a tuple of its
        index, name and function.
    """
    migration_module_names = [
        "create_migration_index",
        "actions_add_user_id",
        "object_log_entry_type_add_assign_location",
        "user_log_entry_type_add_assign_location",
        "user_log_entry_type_add_create_location",
        "user_log_entry_type_add_update_location",
        "object_location_assignments_add_responsible_user_id",
        "create_user_object_permissions_by_all_view",
        "files_add_data",
        "user_log_entry_type_add_link_publication",
        "object_log_entry_type_add_link_publication",
        "object_location_assignments_add_confirmed",
        "user_add_is_readonly",
        "user_add_is_hidden",
        "authentication_type_add_api_token",
        "actions_add_description_as_html",
        "instruments_add_description_as_html",
        "user_add_orcid",
        "user_log_entry_type_add_create_instrument_log_entry",
        "notification_type_add_instrument_log_entry_created",
        "instruments_add_users_can_create_log_entries",
        "instruments_add_users_can_view_log_entries",
        "instruments_add_notes",
        "instruments_add_notes_as_html",
        "user_add_affiliation",
        "instruments_add_create_log_entry_default",
        "actions_add_is_hidden",
        "publications_add_object_name",
        "instruments_add_is_hidden",
        "notification_type_add_referenced_by_object_metadata",
        "action_type_create_default_action_types",
        "action_replace_type_with_type_id",
        "object_log_entry_type_reference_object_in_metadata",
        "user_add_is_active",
        "notification_type_add_instrument_log_entry_edited",
        "instrument_log_entries_add_versioning",
        "object_log_entry_type_export_to_dataverse",
        "actions_replace_description_as_html_with_description_is_markdown",
        "instruments_replace_description_as_html_with_description_is_markdown",
        "instruments_replace_notes_as_html_with_notes_is_markdown",
        "instruments_add_short_description",
        "actions_add_short_description",
        "markdown_to_html_cache_recreate",
        "action_type_add_enable_project_link",
        "object_log_entry_type_add_link_project",
        "object_log_entry_type_add_unlink_project",
        "instrument_log_entry_versions_add_content_is_markdown",
        "public_actions_add_common_actions",
        "instrument_log_entry_versions_add_event_utc_datetime",
        "languages_create_default_languages",
        "actions_move_to_action_translations",
        "action_type_move_to_translation",
        "action_type_translations_create_default_translations",
        "instruments_move_to_translations",
        "locations_replace_string_columns_with_JSON",
        "groups_replace_string_columns_with_JSON",
        "projects_replace_string_columns_with_JSON",
        "location_assignments_replace_string_columns_with_JSON",
        "user_add_role",
        "languages_add_enabled_for_user_interface",
        "action_type_drop_description",
        "actions_drop_description_as_html",
        "actions_drop_short_description_as_html",
        "instruments_drop_description_as_html",
        "instruments_drop_short_description_as_html",
        "instruments_drop_notes_as_html",
        "user_add_extra_fields",
        "files_add_binary_data",
        "action_type_add_disable_create_objects",
        "action_type_add_template_attribute",
        "action_type_add_schema_template",
        "objects_current_add_fed_key",
        "objects_current_update_not_null_constraints",
        "objects_previous_add_fed_key",
        "objects_previous_update_not_null_constraints",
        "instruments_add_fed_key",
        "instrument_translations_update_not_null_constraints",
        "users_add_fed_key",
        "user_type_add_federation_user",
        "actions_add_fed_key",
        "actions_update_not_null_constraints",
        "action_types_add_fed_key",
        "locations_add_fed_key",
        "locations_update_not_null_constraints",
        "object_location_assignments_add_fed_key",
        "object_location_assignments_update_not_null_constraints",
        "files_add_fed_key",
        "files_update_not_null_constraints",
        "comments_add_fed_key",
        "comments_update_not_null_constraints",
        "users_update_not_null_constraints",
        "action_translations_update_not_null_constraints",
        "markdown_images_add_fed_key",
        "create_objects_current_name_cache",
        "create_objects_current_tags_cache",
        "drop_public_actions",
        "drop_public_objects",
        "replace_user_object_permissions_by_all_view",
        "drop_default_public_permissions",
        "setup_default_location_permissions",
        "file_log_add_edit_url_type",
        "replace_user_object_permissions_by_all_view2",
        "languages_add_datetime_format_moment_output",
        "replace_user_object_permissions_by_all_view3",
        "fed_user_aliases_add_use_real_name_column",
        "fed_user_aliases_add_use_real_email_column",
        "fed_user_aliases_add_use_real_orcid_column",
        "fed_user_aliases_add_use_real_affiliation_column",
        "fed_user_aliases_add_use_real_role_column",
        "fed_user_aliases_add_null_if_use_real_data_check",
        "action_type_add_scicat_export_type",
        "object_location_assignments_add_declined",
        "fed_user_aliases_add_last_modified",
        "components_add_last_sync_timestamp",
        "users_add_last_modified",
        "location_types_create_default_location_types",
        "locations_add_type_id",
        "location_log_create_initial_log_entries",
        "notification_type_add_responsibility_assignment_declined",
        "action_type_add_order_index",
        "actions_add_admin_only",
        "actions_add_disable_create_objects",
        "users_add_last_modified_by_id",
        "locations_add_is_hidden",
        "background_tasks_add_result_expiration_date_column",
        "dataverse_exports_add_status",
        "location_types_add_enable_instruments",
        "instruments_add_location_id",
        "files_fix_fed_unique_constraint",
        "object_location_assignments_drop_declined_default",
        "instruments_drop_notes",
        "object_location_assignments_drop_utc_datetime_not_null_constraint",
        "locations_drop_is_hidden_default",
        "languages_change_datetime_format_moment_output_type",
        "replace_user_object_permissions_by_all_view4",
        "fed_object_log_entries_add_user_id",
        "object_shares_add_user_id",
        "fed_object_log_entry_type_add_remote_object_import",
        "object_shares_add_import_status",
        "notification_type_add_remote_object_import_failed",
        "notification_type_add_remote_object_import_notes",
        "location_types_add_enable_capacities",
        "action_translations_add_not_null_constraints",
        "action_type_translations_add_not_null_constraints",
        "instrument_translations_add_not_null_constraints",
        "authentications_add_not_null_constraints",
        "component_authentications_add_not_null_constraints",
        "own_component_authentications_add_not_null_constraints",
        "download_service_job_files_add_not_null_constraints",
        "two_factor_authentication_methods_add_not_null_constraints",
        "markdown_images_add_not_null_constraint",
        "languages_add_not_null_constraints",
        "action_type_add_enable_instrument_link",
        "instruments_add_object_id",
        "instruments_add_show_linked_object_data",
        "authentication_type_add_api_access_token",
        "user_type_add_eln_import_user",
        "object_log_entry_type_add_import_from_eln_file",
        "objects_previous_add_eln_import",
        "objects_current_add_eln_import",
        "users_add_eln_import",
        "user_log_entry_type_add_import_from_eln_file",
        "components_add_discoverable",
        "actions_add_objects_readable_by_all_users_by_default",
        "files_add_data_not_null_constraint",
        "replace_timestamp_with_timestamptz",
        "authentication_type_add_fido2_passkey",
        "action_type_add_show_in_object_filters",
        "notification_type_add_automatic_user_federation",
        "topics_add_short_description",
        "topics_add_is_markdown",
        "actions_add_use_instrument_topics",
        "object_log_add_is_imported",
        "languages_add_date_format_moment_output",
        "files_add_preview_image",
        "group_invitations_add_revoked",
        "project_invitations_add_revoked",
        "instrument_log_file_attachments_generate_image_infos",
        "fed_identity_add_login_column",
        "components_add_fed_login_available_column",
        "authentication_type_add_federated_login",
        "locations_add_enable_object_assignments",
        "authentication_type_add_oidc",
        "notification_mode_for_types_add_not_null_constraint",
        'eln_imports_add_signed_by',
    ]

    migrations = []
    for migration_index, migration_module_name in enumerate(migration_module_names):
        try:
            migration_module = importlib.import_module('sampledb.models.migrations.' + migration_module_name)
            migration_function = migration_module.run
        except Exception:
            print(f'Failed to load migration #{migration_index} "{migration_module_name}".', file=sys.stderr)
            sys.exit(1)
        migrations.append((migration_index, migration_module_name, migration_function))
    return migrations


def table_has_column(table_name: str, column_name: str) -> bool:
    """
    Return whether a table has a column with a given name.

    :param table_name: the name of the table
    :param column_name: the name of the column to check for
    :return: whether the column exists
    """
    return bool(db.session.execute(
        db.text("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :column_name
        """),
        params={
            'table_name': table_name,
            'column_name': column_name
        }
    ).scalar())


def column_is_nullable(table_name: str, column_name: str) -> bool:
    """
    Return whether a column may contain NULL values.

    :param table_name: the name of the table
    :param column_name: the name of the column to check
    :return: whether the column may contain NULL values
    """
    return bool(db.session.execute(
        db.text("""
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :column_name
        """),
        params={
            'table_name': table_name,
            'column_name': column_name
        }
    ).scalar() == 'YES')


def enum_has_value(enum_name: str, value_name: str) -> bool:
    """
    Return whether an enum has a value with a given name.

    :param enum_name: the name of the enum
    :param value_name: the name of the value to check for
    :return: whether the value exists
    """
    return bool(db.session.execute(
        db.text("""
            SELECT COUNT(*)
            FROM pg_type
            JOIN pg_enum ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = :enum_name AND pg_enum.enumlabel = :value_name
        """),
        params={
            'enum_name': enum_name,
            'value_name': value_name
        }
    ).scalar())


def add_enum_value(enum_name: str, value_name: str) -> None:
    """
    Add a value to an enum.

    :param enum_name: the name of the enum
    :param value_name: the name of the value to add
    """
    # Use connection and run COMMIT as ALTER TYPE cannot run in a transaction (in PostgreSQL 11)
    engine = db.engine.execution_options(autocommit=False)
    with engine.connect() as connection:
        connection.execute(db.text("COMMIT"))
        connection.execute(db.text(f"""
            ALTER TYPE {enum_name}
            ADD VALUE '{value_name}'
        """))


def enum_value_migration(enum_name: str, value_name: str) -> bool:
    """
    Perform a migration for adding a value to an enum, if the value is missing.

    :param enum_name: the name of the enum
    :param value_name: the name of the value to add
    :return: whether the migration was performed
    """
    if enum_has_value(enum_name, value_name):
        return False
    add_enum_value(enum_name, value_name)
    return True


def timestamp_add_timezone_utc_migration(table_name: str, column_name: str) -> bool:
    """
    Perform a migration for converting a TIMESTAMP WITHOUT TIME ZONE column to
    type TIMESTAMP WITH TIME ZONE using UTC for the conversion.

    :param table_name: the name of the table
    :param column_name: the name of the column to convert
    :return: whether the migration was performed
    """
    if db.session.execute(
        db.text("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = :column_name
        """),
        params={
            'table_name': table_name,
            'column_name': column_name
        }
    ).scalar() == 'timestamp with time zone':
        return False
    db.session.execute(db.text(f"""
        ALTER TABLE {table_name}
        ALTER {column_name}
        TYPE TIMESTAMP WITH TIME ZONE
        USING {column_name} AT TIME ZONE 'UTC'
    """))
    return True
