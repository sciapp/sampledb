import os
import typing

from bs4 import BeautifulSoup
from bs4.element import Tag
import flask

from . import errors


WHITELIST_TAGS = {
    "p", "a", "div", "article", "section", "nav", "span", "meta", "title", "h1", "h2", "h3", "h4", "h5", "html", "body", "head", "header",
    "main", "footer", "table", "tbody", "tr", "td", "th", "colgroup", "col", "ul", "ol", "li", "br", "hr", "summary", "details", "img", "input",
}

WHITELIST_ATTRIBUTES = {
    "class", "src", "href", "name", "content", "charset", "id", "lang", "rel", "type",
}

# Simple versioning for the sanitizer. It should be increased when changes were made to the sanitizer.
# The version is used to detect changes to the sanitizer and update the sanitized content of files in the database.
SANITIZER_VERSION = 1


def sanitize(content: str, mime_type: str, eln_import_id: int, root_path: str, referenced_files: list[str]) -> str:
    if mime_type == "text/html":
        return _sanitize_html(content, eln_import_id, root_path, referenced_files)
    if mime_type == "text/css":
        return ""
    return content


def _sanitize_html(html_content: str, eln_import_id: int, root_path: str, referenced_files: list[str]) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    for tag in soup.find_all():
        try:
            _sanitize_html_attributes(tag, eln_import_id, root_path, referenced_files)
            _sanitize_html_tag(tag, eln_import_id, root_path, referenced_files)
        except errors.ELNImportPreviewIllegalTagError:
            tag.unwrap()

    return str(soup)


def _sanitize_html_attributes(tag: Tag, eln_import_id: int, root_path: str, referenced_files: list[str]) -> None:
    CUSTOM_ATTRIB_FILTERS = {
        "src": _sanitize_html_attrib_reference("src", eln_import_id, root_path, referenced_files),
        "href": _sanitize_html_attrib_reference("href", eln_import_id, root_path, referenced_files),
        "style": _sanitize_html_attrib_style(eln_import_id, root_path, referenced_files)
    }

    if tag.attrs is not None:
        attr_keys = set(tag.attrs.keys())
        for attr in attr_keys:
            if attr in CUSTOM_ATTRIB_FILTERS:
                CUSTOM_ATTRIB_FILTERS[attr](tag)
            elif "javascript:" in tag[attr]:
                tag.attrs.pop(attr)
            elif attr not in WHITELIST_ATTRIBUTES:
                tag.attrs.pop(attr)


def _sanitize_html_attrib_reference(attrib: str, eln_import_id: int, root_path: str, referenced_files: list[str]) -> typing.Callable[[Tag], None]:
    def wrapped_filter(tag: Tag) -> None:
        src = tag[attrib]

        if not isinstance(src, str):
            del tag[attrib]
            return

        fullpath = os.path.normpath(os.path.join(root_path, src))
        preview_url = _transform_url_to_preview_url(fullpath, eln_import_id)
        if preview_url is not None:
            tag[attrib] = preview_url
            file_fullpath = fullpath.split("#")[0]
            if file_fullpath not in referenced_files:
                referenced_files.append(file_fullpath)
        elif not src.startswith("#"):
            del tag[attrib]

    return wrapped_filter


def _sanitize_html_attrib_style(eln_import_id: int, root_path: str, referenced_files: list[str]) -> typing.Callable[[Tag], None]:
    def wrapped_filter(tag: Tag) -> None:
        tag["style"] = ""
    return wrapped_filter


def _sanitize_html_tag(tag: Tag, eln_import_id: int, root_path: str, referenced_files: list[str]) -> None:
    CUSTOM_FILTERS = {
        "style": _sanitize_html_tag_style(eln_import_id, root_path, referenced_files),
        "link": _sanitize_html_tag_link,
        "script": _sanitize_script_script_tag,
    }

    if tag.name in CUSTOM_FILTERS:
        CUSTOM_FILTERS[tag.name](tag)
    elif tag.name in WHITELIST_TAGS:
        return
    else:
        raise errors.ELNImportPreviewIllegalTagError()


def _sanitize_html_tag_style(eln_import_id: int, root_path: str, referenced_files: list[str]) -> typing.Callable[[Tag], None]:
    def wrapped_filter(tag: Tag) -> None:
        if tag.string is not None:
            tag.string = ""
    return wrapped_filter


def _sanitize_html_tag_link(tag: Tag) -> None:
    href: typing.Optional[str] = tag.attrs.get("href", None)
    if href is None or not href.startswith("/"):
        tag.decompose()


def _sanitize_script_script_tag(tag: Tag) -> None:
    tag.decompose()


def _transform_url_to_preview_url(normalized_fullpath: str, eln_import_id: int) -> typing.Optional[str]:
    if normalized_fullpath.startswith("/"):
        normalized_fullpath = normalized_fullpath[1:]

    if normalized_fullpath.startswith("ro-crate-preview.html"):
        return f"{flask.url_for(".eln_preview", eln_import_id=eln_import_id)}{normalized_fullpath[len("ro-crate-preview.html"):]}"
    elif normalized_fullpath.startswith("ro-crate-preview_files/"):
        referenced_subpath = normalized_fullpath[len("ro-crate-preview_files/"):]
        return flask.url_for(".eln_preview", eln_import_id=eln_import_id, subpath=referenced_subpath)
    return None
