# coding: utf-8
"""
Add component_id and id columns, fed key unique constraint and id primary key constraint to markdown_images table.
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    if table_has_column('markdown_images', 'component_id'):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE markdown_images
            ADD component_id INTEGER,
            ADD FOREIGN KEY(component_id) REFERENCES components(id),
            DROP CONSTRAINT markdown_images_pkey,
            ADD COLUMN id SERIAL PRIMARY KEY,
            ADD CONSTRAINT markdown_images_file_name_component_id_key UNIQUE(file_name, component_id)
    """))
    return True
