"""
Add hash_data and hash_metadata columns to objects_subversions
"""
import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migrations by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'objects_subversions'
    """)).fetchall()
    if ('hash_metadata', ) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE objects_subversions
        ADD hash_metadata VARCHAR
    """))

    return True
