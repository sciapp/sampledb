"""
Add column fed_lang_id and component_id to table languages
"""

import flask_sqlalchemy

from .utils import table_has_column


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip by condition
    if table_has_column("languages", "fed_lang_id"):
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE languages
        ADD fed_lang_id INTEGER,
        ADD component_id INTEGER,
        ADD FOREIGN KEY(component_id) REFERENCES components(id),
        ADD CONSTRAINT languages_lang_code_fed_lang_id_component_id_key UNIQUE(lang_code, fed_lang_id, component_id)
    """))
    return True
