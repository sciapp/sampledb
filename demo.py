#!/usr/bin/env python3
"""
Run the development server for local, interactive testing and demo purposes.
"""

import getpass
from sampledb import create_app
import sampledb.config
from example_data import setup_data

sampledb.config.TEMPLATES_AUTO_RELOAD = True
sampledb.config.SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{0}:@localhost:5432/{0}'.format(getpass.getuser())


app = create_app()

with app.app_context():
    setup_data(app=app)

app.run(debug=True)
