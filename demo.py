#!/usr/bin/env python3
"""
Run the development server for local, interactive testing and demo purposes.

This will REMOVE ALL DATA, set up demo data using the set_up_demo script, add
a route to automatically sign in and then start a Flask development server.
"""

import getpass
import shutil
import tempfile
import os
import sqlalchemy
from sampledb import create_app
import sampledb.config
import sampledb.utils
import sampledb.scripts.set_up_demo

sampledb.config.TEMPLATES_AUTO_RELOAD = True
sampledb.config.SQLALCHEMY_DATABASE_URI = os.environ.get('SAMPLEDB_SQLALCHEMY_DATABASE_URI', 'postgresql+psycopg2://{0}:@localhost:5432/{0}'.format(getpass.getuser()))


temp_dir = tempfile.mkdtemp()
try:
    sampledb.config.SERVER_NAME = 'localhost:5000'

    # fully empty the database first
    sampledb.utils.empty_database(sqlalchemy.create_engine(sampledb.config.SQLALCHEMY_DATABASE_URI, **sampledb.config.SQLALCHEMY_ENGINE_OPTIONS), only_delete=False)

    sampledb.scripts.set_up_demo.main(())

    app = create_app()

    # Setup autologin for demo
    @app.route('/users/me/autologin')
    @app.route('/users/<int:user_id>/autologin')
    def autologin(user_id=None):
        import flask
        import flask_login
        if user_id is None:
            user_id = sampledb.logic.instruments.get_instruments()[0].responsible_users[0].id
        user = sampledb.logic.users.get_user(user_id)
        flask_login.login_user(user)
        # Remove the message asking the user to sign in
        flask.session.pop('_flashes', None)
        flask.flash('You have been signed in automatically as part of the SampleDB Demo.', 'info')
        return flask.redirect(os.environ.get('SAMPLEDB_DEMO_REDIRECT_URI', flask.url_for('frontend.index')))

    sampledb.login_manager.login_view = 'autologin'

    print()
    print("To sign in as instrument scientist, visit:")
    print("http://localhost:5000/users/me/autologin")
    print("or visit any other site that requires being signed in.")
    print(flush=True)

    app.run(debug=True, host=os.environ.get('SAMPLEDB_DEMO_HOST'), use_reloader=False)
finally:
    shutil.rmtree(temp_dir)
