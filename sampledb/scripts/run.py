# coding: utf-8
"""
Script for running the SampleDB server.

Usage: python -m sampledb run [<port>]
"""

import sys
import cherrypy

from .. import create_app


def main(arguments):
    if len(arguments) > 1:
        print(__doc__)
        exit(1)
    if arguments:
        port = arguments[0]
        try:
            port = int(port)
            if port < 1024 or port > 65535:
                raise ValueError()
        except ValueError:
            print("Error: port must be between 1024 and 65535", file=sys.stderr)
            exit(1)
    else:
        port = 8000
    app = create_app()
    cherrypy.tree.graft(app, app.config['SERVER_PATH'])
    cherrypy.config.update({
        'environment': 'production',
        'server.socket_host': '0.0.0.0',
        'server.socket_port': port,
        'server.thread_pool': 4,
        'log.screen': True
    })
    cherrypy.engine.start()
    cherrypy.engine.block()
