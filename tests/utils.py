# coding: utf-8
"""

"""
import pytest
import random
import threading
import time
import requests
import flask


@pytest.fixture
def flask_server(app):
    if not getattr(app, 'has_shutdown_route', False):
        @app.route('/shutdown', methods=['POST'])
        def shutdown():
            func = flask.request.environ.get('werkzeug.server.shutdown')
            if func is None:
                raise RuntimeError('Not running with the Werkzeug Server')
            func()
            return 'Server shutting down...'
        app.has_shutdown_route = True

    port = random.randint(10000, 20000)
    server_thread = threading.Thread(target=lambda: app.run(port=port, debug=True, use_reloader=False), daemon=True)
    server_thread.start()
    server_thread.app = app
    server_thread.base_url = 'http://localhost:{0}/'.format(port)
    # short delay to allow the web server to start
    time.sleep(0.1)
    yield server_thread
    requests.post(server_thread.base_url + 'shutdown')
    server_thread.join()
