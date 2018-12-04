# coding: utf-8
"""

"""

from .utils import find_migrations, should_skip_by_index, update_migration_index


def run(db):
    for index, name, function in find_migrations():
        print('Migration #{} "{}":'.format(index, name))

        # Skip migration by migration index
        if should_skip_by_index(db, index):
            print("Skipped (index).")
            continue

        # Perform migration
        if function(db):
            print("Done.")
        else:
            print("Skipped (condition).")

        # Update migration index to skip this migration by index in the future
        update_migration_index(db, index)
        db.session.commit()
