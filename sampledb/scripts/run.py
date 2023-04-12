# coding: utf-8
"""
Script for running the SampleDB server.

Usage: sampledb run [<port>]
"""

import sys
import typing

import cherrypy

from .. import create_app


def main(arguments: typing.List[str]) -> None:
    if len(arguments) > 1:
        print(__doc__)
        sys.exit(1)
    if arguments:
        port_str = arguments[0]
        try:
            port = int(port_str)
            if port < 1024 or port > 65535:
                raise ValueError()
        except ValueError:
            print("Error: port must be between 1024 and 65535", file=sys.stderr)
            sys.exit(1)
    else:
        port = 8000

    app = create_app()
    cherrypy.tree.graft(app, app.config['SERVER_PATH'])
    cherrypy.config.update({
        'environment': 'production',
        'server.socket_host': '0.0.0.0',
        'server.socket_port': port,
        'server.socket_queue_size': 20,
        'log.screen': True
    })
    cherrypy.engine.start()
    cherrypy.engine.block()
