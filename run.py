#!/usr/bin/env python3
from sampledb import create_app

app = create_app()
app.run(debug=True)
