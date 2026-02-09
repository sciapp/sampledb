# coding: utf-8
"""
Add show_object_title column to object_data_to_html_cache_entries table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('object_data_to_html_cache_entries', 'show_object_title'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE object_data_to_html_cache_entries
        ADD show_object_title BOOLEAN
    """))
    return True
