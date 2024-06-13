# coding: utf-8
"""
Replace columns of type TIMESTAMP WITHOUT TIME ZONE with columns of type
TIMESTAMP WITH TIME ZONE, using UTC for the conversion.
"""

import flask_sqlalchemy

from .utils import timestamp_add_timezone_utc_migration


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    migrations_ran = [
        timestamp_add_timezone_utc_migration(table_name, column_name)
        for table_name, column_name in [
            ('api_log_entries', 'utc_datetime'),
            ('background_tasks', 'expiration_date'),
            ('comments', 'utc_datetime'),
            ('components', 'last_sync_timestamp'),
            ('dataverse_exports', 'utc_datetime'),
            ('download_service_job_files', 'creation'),
            ('download_service_job_files', 'expiration'),
            ('eln_imports', 'import_utc_datetime'),
            ('eln_imports', 'upload_utc_datetime'),
            ('fed_action_log_entries', 'utc_datetime'),
            ('fed_action_type_log_entries', 'utc_datetime'),
            ('fed_comment_log_entries', 'utc_datetime'),
            ('fed_file_log_entries', 'utc_datetime'),
            ('fed_instrument_log_entries', 'utc_datetime'),
            ('fed_location_log_entries', 'utc_datetime'),
            ('fed_location_type_log_entries', 'utc_datetime'),
            ('fed_object_location_assignment_log_entries', 'utc_datetime'),
            ('fed_object_log_entries', 'utc_datetime'),
            ('fed_user_aliases', 'last_modified'),
            ('fed_user_log_entries', 'utc_datetime'),
            ('file_log_entries', 'utc_datetime'),
            ('files', 'utc_datetime'),
            ('group_invitations', 'utc_datetime'),
            ('instrument_log_entry_versions', 'event_utc_datetime'),
            ('instrument_log_entry_versions', 'utc_datetime'),
            ('location_log_entries', 'utc_datetime'),
            ('markdown_images', 'utc_datetime'),
            ('notifications', 'utc_datetime'),
            ('object_location_assignments', 'utc_datetime'),
            ('object_log_entries', 'utc_datetime'),
            ('object_shares', 'utc_datetime'),
            ('objects_current', 'utc_datetime'),
            ('objects_previous', 'utc_datetime'),
            ('objects_subversions', 'utc_datetime'),
            ('objects_subversions', 'utc_datetime_subversion'),
            ('project_invitations', 'utc_datetime'),
            ('scicat_exports', 'utc_datetime'),
            ('temporary_files', 'utc_datetime'),
            ('user_invitations', 'utc_datetime'),
            ('user_log_entries', 'utc_datetime'),
            ('users', 'last_modified')
        ]
    ]
    return any(migrations_ran)
