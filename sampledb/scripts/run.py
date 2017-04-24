# coding: utf-8
"""
Script for running the SampleDB development server.

Usage: python -m sampledb run [<port>]
"""

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
            print("Error: port must be between 1024 and 65535")
            exit(1)
    else:
        port = 8000
    app = create_app()
    app.run(port=port, debug=True, use_evalex=False, use_reloader=False)
