# coding: utf-8
"""
Generate entries for the instrument_log_file_attachment_image_infos table.
"""

import flask_sqlalchemy

from ...logic.instrument_log_entries import generate_instrument_log_file_attachment_image_info


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migration by condition
    image_infos_exist = db.session.execute(db.text("""
        SELECT thumbnail_mime_type
        FROM instrument_log_file_attachment_image_infos
    """)).first() is not None
    if image_infos_exist:
        return False
    # Perform migration
    for file_attachment_id, in db.session.execute(db.text("""
        SELECT id
        FROM instrument_log_file_attachments
    """)).all():
        generate_instrument_log_file_attachment_image_info(file_attachment_id=file_attachment_id)
    return True
