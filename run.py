#!/usr/bin/env python3
from sampledb import create_app
from example_data import setup_data

app = create_app()

with app.app_context():
    setup_data(app=app)

app.run(debug=True)
