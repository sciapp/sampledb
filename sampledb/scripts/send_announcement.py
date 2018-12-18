# coding: utf-8
"""
Script for sending an announcement notification to all users.

Usage: python -m sampledb send_announcement <text_file_name> <html_file_name>
"""

from .. import create_app
from ..logic.notifications import create_announcement_notification_for_all_users


def main(arguments):
    if len(arguments) != 2:
        print(__doc__)
        exit(1)
    text_file_name, html_file_name = arguments
    with open(text_file_name, 'r') as text_file:
        text = text_file.read()
    with open(html_file_name, 'r') as html_file:
        html = html_file.read()
    app = create_app()
    with app.app_context():
        create_announcement_notification_for_all_users(text, html)
