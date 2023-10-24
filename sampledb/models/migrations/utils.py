# coding: utf-8
"""

"""

import importlib
import os
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


def find_migrations() -> typing.List[typing.Tuple[int, str, typing.Callable[[typing.Any], bool]]]:
    """
    Finds migrations and returns them sorted by their index.

    :return: A list of migrations, with each migration as a tuple of its
        index, name and function.
    """
    migrations_dir = os.path.abspath(os.path.dirname(__file__))

    migrations: typing.Dict[int, typing.Tuple[str, typing.Callable[[typing.Any], bool]]] = {}

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
        if migration_index in migrations:
            print(f"Duplicate migration index {migration_index} used in {migration_name} and {migrations[migration_index][0]}", file=sys.stderr)
            sys.exit(1)
        migrations[migration_index] = (migration_name, migration_function)

    migration_indices = list(sorted(migrations.keys()))

    # ensure no migration index is missing
    assert migration_indices == list(range(len(migration_indices)))

    sorted_migrations = []
    for index in migration_indices:
        name, function = migrations[index]
        sorted_migrations.append((index, name, function))
    return sorted_migrations


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
