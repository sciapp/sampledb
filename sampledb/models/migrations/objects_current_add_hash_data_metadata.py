"""
Add hash_data and hash_metadata columns to objects_current
"""
import flask_sqlalchemy


def run(db: flask_sqlalchemy.SQLAlchemy) -> bool:
    # Skip migrations by condition
    column_names = db.session.execute(db.text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'objects_current'
    """)).fetchall()
    if ('hash_data', ) in column_names:
        return False

    # Perform migration
    db.session.execute(db.text("""
        ALTER TABLE objects_current
        ADD hash_data VARCHAR,
        ADD hash_metadata VARCHAR
    """))
    return True
