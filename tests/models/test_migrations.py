import os

import sampledb
import sampledb.utils


def test_migrations():
    engine = sampledb.db.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI, {})
    sampledb.utils.empty_database(engine, only_delete=False)

    # load and execute SQL previously created with pg_dump
    sql_file_name = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'demo.sql')
    with open(sql_file_name, 'r', encoding='utf8') as sql_file:
        sql_statement = ''
        for sql_line in sql_file.readlines():
            if sql_line.startswith('--'):
                if sql_statement.strip():
                    engine.execute(sampledb.db.text(sql_statement.replace(':', r'\:')))
                    sql_statement = ''
                continue
            sql_statement += sql_line
    del engine

    sampledb.utils.migrations.run(sampledb.db)
