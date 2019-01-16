# coding: utf-8
"""

"""

import importlib
import os
import typing


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
        """
        SELECT migration_index
        FROM migration_index
        WHERE migration_index >= :index
        """,
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
        """
        UPDATE migration_index
        SET migration_index = :index
        WHERE migration_index < :index
        """,
        {"index": index}
    ).rowcount == 1


def find_migrations() -> typing.List[typing.Tuple[int, str, typing.Callable[[typing.Any], bool]]]:
    """
    Finds migrations and returns them sorted by their index.

    :return: A list of migrations, with each migration as a tuple of its
        index, name and function.
    """
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
            migration_name = migration_module.MIGRATION_NAME
            migration_function = migration_module.run
        except AttributeError:
            continue
        # prevent duplicate migration indices
        assert migration_index not in migrations
        migrations[migration_index] = (migration_name, migration_function)

    migration_indices = list(sorted(migrations.keys()))

    # ensure no migration index is missing
    assert migration_indices == list(range(len(migration_indices)))

    sorted_migrations = []
    for index in migration_indices:
        name, function = migrations[index]
        sorted_migrations.append((index, name, function))
    return sorted_migrations
