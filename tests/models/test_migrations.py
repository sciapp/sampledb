import os
import sys

import sampledb
import sampledb.utils
import sampledb.models.migrations


def test_migrations():
    engine = sampledb.db.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI, **sampledb.config.SQLALCHEMY_ENGINE_OPTIONS)
    sampledb.utils.empty_database(engine, only_delete=False)

    # load and execute SQL previously created with pg_dump
    sql_file_name = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'demo.sql')
    sql_statements = []
    with open(sql_file_name, 'r', encoding='utf8') as sql_file:
        sql_statement = ''
        for sql_line in sql_file.readlines():
            if sql_line.startswith('--'):
                if sql_statement.strip():
                    sql_statements.append(sql_statement.replace(':', r'\:'))
                    sql_statement = ''
                continue
            sql_statement += sql_line

    with engine.begin() as connection:
        # detach connection, as demo.sql statements change state
        connection.detach()
        for sql_statement in sql_statements:
            connection.execute(sampledb.db.text(sql_statement))

    # create missing tables using SQLAlchemy
    sampledb.db.metadata.create_all(bind=engine)
    del engine

    sampledb.utils.migrations.run(sampledb.db)


def test_all_migrations_listed():
    migrations = sampledb.models.migrations.get_migrations()
    migration_names = [
        migration[1]
        for migration in migrations
    ]
    migrations_dir = os.path.dirname(sampledb.models.migrations.__file__)
    for migration_module_name in os.listdir(migrations_dir):
        if not migration_module_name.endswith('.py'):
            continue
        if migration_module_name in ('__init__.py', 'utils.py'):
            continue
        assert os.path.splitext(migration_module_name)[0] in migration_names
        with open(os.path.join(migrations_dir, migration_module_name), 'r', encoding='utf8') as migration_file:
            migration_code = migration_file.read()
        assert 'MIGRATION_INDEX' not in migration_code
        assert 'MIGRATION_NAME' not in migration_code
