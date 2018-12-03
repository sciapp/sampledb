# coding: utf-8
"""

"""

import importlib
import os


def run(db):
    migrations_dir = os.path.abspath(os.path.dirname(__file__))

    migrations = {}

    for migration_file in os.listdir(migrations_dir):
        if not migration_file.endswith('.py'):
            continue
        if migration_file.startswith('_'):
            continue
        migration_name, _ = os.path.splitext(migration_file)
        migration_module = importlib.import_module('sampledb.models.migrations.' + migration_name)
        try:
            migration_index = migration_module.MIGRATION_INDEX
            migration_run = migration_module.run
        except AttributeError:
            continue
        if migration_index in migrations:
            print('Duplicate migration index', migration_index)
            exit(1)
        migrations[migration_index] = migration_run

    migration_indices = list(sorted(migrations.keys()))
    for migration_index in migration_indices:
        migrations[migration_index](db)
