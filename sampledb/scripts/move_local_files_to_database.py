# coding: utf-8
"""
Move all files that use local storage and are found in the file directory to
the database. Files that use local storage but cannot be found will be left
unchanged. The file directory will not be changed by this script.

Usage: python -m sampledb move_local_files_to_database
"""

from sampledb import db, models, logic, create_app


def main(arguments):
    if arguments:
        print(__doc__)
        exit(1)

    num_moved_files = 0
    num_local_files = 0
    app = create_app()
    with app.app_context():
        files = models.File.query.all()
        for file in files:
            if file.data and file.data.get('storage') == 'local':
                num_local_files += 1
                try:
                    with logic.files.File.from_database(file).open(read_only=True) as local_file:
                        file_content = local_file.read()
                    file.binary_data = file_content
                    file.data = dict(file.data, storage='database')
                    db.session.add(file)
                    db.session.commit()
                    num_moved_files += 1
                except Exception:
                    print(f"Error: Failed to move file #{file.id} for object #{file.object_id}")
    if num_moved_files > 0:
        print(f"Success: Moved {num_moved_files} of {num_local_files} files with local storage.")
    elif num_local_files == 0:
        print("Success: There are no file to move.")
