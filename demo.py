#!/usr/bin/env python3
"""
Run the development server for local, interactive testing and demo purposes.
"""

import getpass
import shutil
import tempfile
import os
import sqlalchemy
from sampledb import create_app
import sampledb.config
from example_data import setup_data

sampledb.config.TEMPLATES_AUTO_RELOAD = True
sampledb.config.SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{0}:@localhost:5432/{0}'.format(getpass.getuser())


temp_dir = tempfile.mkdtemp()
try:
    os.mkdir(os.path.join(temp_dir, 'instrument_files'))
    sampledb.config.FILE_SOURCES = {
        # 'instrument': lambda user_id: os.path.join(temp_dir, 'instrument_files')
        'instrument': sampledb.logic.files.LocalFileSource(lambda user_id: '/Users/rhiem/Documents/Documents')
    }
    os.mkdir(os.path.join(temp_dir, 'uploaded_files'))
    sampledb.config.FILE_STORAGE_PATH = os.path.join(temp_dir, 'uploaded_files')

    # fully empty the database first
    metadata = sqlalchemy.MetaData(bind=sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI))
    metadata.reflect()
    metadata.drop_all()
    app = create_app()

    with app.app_context():
        setup_data(app=app)

    app.run(debug=True)
finally:
    shutil.rmtree(temp_dir)
