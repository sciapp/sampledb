# coding: utf-8
"""
Add user_id column to actions table.
"""

import os

MIGRATION_INDEX = 1
MIGRATION_NAME, _ = os.path.splitext(os.path.basename(__file__))


def run(db):
    client_column_names = db.session.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'actions'
    """).fetchall()
    if ('user_id',) in client_column_names:
        print('Skipping migration {} "{}".'.format(MIGRATION_INDEX, MIGRATION_NAME))
        return

    print('Performing migration {} "{}"...'.format(MIGRATION_INDEX, MIGRATION_NAME))
    db.session.execute("""
        ALTER TABLE users
        ADD user_id INTEGER
    """)
    db.session.execute("""
        ALTER TABLE users
        ADD FOREIGN KEY(user_id) REFERENCES users(id)
    """)
    print('Done.')
