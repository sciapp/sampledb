# coding: utf-8
"""
Script for building the SampleDB translations.

These are built automatically, unless the BUILD_TRANSLATIONS configuration
value is unset/set to False. This script mostly exists so that the
translations can be built once during testing instead of building them for
each individual test.

Usage: python -m sampledb build_translations
"""

import sampledb


def main(arguments):
    if arguments:
        print(__doc__)
        exit(1)
    sampledb.build_translations(sampledb.config.PYBABEL_PATH)
    print("Success: the translations have been built")
