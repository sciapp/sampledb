# coding: utf-8
"""
Add component_id and id columns, fed key unique constraint and id primary key constraint to markdown_images table.
"""

import os

import flask_sqlalchemy

MIGRATION_INDEX = 92
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'markdown_images'
    """)).fetchall()
    if ('component_id',) in column_names:
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
