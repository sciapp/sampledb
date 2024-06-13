# coding: utf-8
"""

"""
import sys

import flask_sqlalchemy

from .utils import get_migrations, should_skip_by_index, update_migration_index


def run(db: flask_sqlalchemy.SQLAlchemy) -> None:
    for index, name, function in get_migrations():

        # Skip migration by migration index
        if should_skip_by_index(db, index):
            continue

        try:
            # Perform migration
            if function(db):
                print(f'Migration #{index} "{name}" applied.', file=sys.stderr)
            elif index > 0:
                print(f'Migration #{index} "{name}" skipped.', file=sys.stderr)

            # Update migration index to skip this migration by index in the future
            update_migration_index(db, index)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
