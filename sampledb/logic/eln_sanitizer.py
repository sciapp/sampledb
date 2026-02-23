# Simple versioning for the sanitizer. It should be increased when changes were made to the sanitizer.
# The version is used to detect changes to the sanitizer and update the sanitized content of files in the database.
SANITIZER_VERSION = 1


def sanitize(content: str, mime_type: str, eln_import_id: int, root_path: str, referenced_files: list[str]) -> str:
    if mime_type == "text/html":
        return ""
    if mime_type == "text/css":
        return ""
    return content
