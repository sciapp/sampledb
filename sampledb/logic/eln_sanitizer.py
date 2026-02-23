import os
import typing

from bs4 import BeautifulSoup
from bs4.element import Tag
import flask
import tinycss2

from . import errors


WHITELIST_CSS_FUNCTIONS = {
    'acos', 'asin', 'atan', 'atan2', 'attr', 'blur', 'brightness', 'calc', 'circle', 'clamp', 'color', 'color-mix', 'color-gradient',
    'contrast', 'cos', 'counter', 'counters', 'cubic-bezier', 'drop-shadow', 'ellipse', 'exp', 'fit-content', 'grayscale', 'hsl', 'hsla',
    'hue-rotate', 'hwb', 'hypot', 'inset', 'invert', 'lab', 'lch', 'light-dark', 'linear-gradient', 'log', 'matrix', 'matrix3d', 'max',
    'min', 'minmax', 'mod', 'oklab', 'oklch', 'opacity', 'perspective', 'polygon', 'pow', 'radial-gradient', 'ray', 'rem', 'repeat',
    'repeating-conic-gradient', 'repeating-linear-gradient', 'repeating-radial-gradient', 'rgb', 'rgba', 'rotate', 'rotate3d', 'rotatex',
    'rotatey', 'rotatez', 'round', 'saturate', 'scale', 'scale3d', 'scalex', 'scaley', 'sepia', 'sin', 'skew', 'skewx', 'skewy', 'sqrt',
    'steps', 'tan', 'translate', 'translatex', 'translatey', 'var',
}

WHITELIST_CSS_AT_RULES = {
    'charset', 'layer', 'counter-style', 'container', 'font-feature-values', 'keyframes', 'font-palette-values', 'media', 'page',
    'position-try', 'property', 'scope', 'starting-style', 'supports', 'view-transition', 'top-left-corner', 'top-left',
    'top-center', 'top-right', 'top-right-corner', 'bottom-left-corner', 'bottom-left', 'bottom-center', 'bottom-right',
    'bottom-right-corner', 'left-top', 'left-middle', 'left-bottom', 'right-top', 'right-middle', 'right-bottom',
}


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
        return _sanitize_css_stylesheet(content, eln_import_id, root_path, referenced_files)
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
        style_content = tag["style"]
        style_parsed = tinycss2.parse_blocks_contents(style_content)
        style_sanitized = _css_sanitize_rules(style_parsed, eln_import_id, root_path, referenced_files)
        tag["style"] = tinycss2.serialize(style_sanitized)
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
            tag.string = _sanitize_css_stylesheet(tag.string, eln_import_id, root_path, referenced_files)
    return wrapped_filter


def _sanitize_html_tag_link(tag: Tag) -> None:
    href: typing.Optional[str] = tag.attrs.get("href", None)
    if href is None or not href.startswith("/"):
        tag.decompose()


def _sanitize_script_script_tag(tag: Tag) -> None:
    tag.decompose()


def _sanitize_css_stylesheet(css_content: str, eln_import_id: int, root_path: str, referenced_files: list[str]) -> str:
    parsed_rules = tinycss2.parse_stylesheet(css_content, skip_whitespace=True, skip_comments=True)
    sanitized_rules = _css_sanitize_rules(parsed_rules, eln_import_id, root_path, referenced_files)
    return typing.cast(str, tinycss2.serialize(sanitized_rules))


def _css_sanitize_rules(css_rules: typing.List[tinycss2.ast.Node], eln_import_id: int, root_path: str, referenced_files: list[str]) -> list[tinycss2.ast.Node]:
    result = []
    for rule in css_rules:
        if ((isinstance(rule, tinycss2.ast.QualifiedRule) and _css_sanitize_qualified_rule(rule, eln_import_id, root_path, referenced_files)) or
            (isinstance(rule, tinycss2.ast.AtRule) and _css_sanitize_at_rule(rule, eln_import_id, root_path, referenced_files)) or
            (isinstance(rule, tinycss2.ast.Declaration) and _css_sanitize_declaration(rule, eln_import_id, root_path, referenced_files)) or
                (isinstance(rule, tinycss2.ast.WhitespaceToken))):
            result.append(rule)
    return result


def _css_sanitize_qualified_rule(qualified_rule: tinycss2.ast.QualifiedRule, eln_import_id: int, root_path: str, referenced_files: list[str]) -> bool:
    grouped_statements = _css_group_by_statement(qualified_rule.content)
    result = []
    for statement in grouped_statements:
        result.extend(_css_sanitize_statement(statement, root_path, eln_import_id, referenced_files))
    qualified_rule.content = result
    return True


def _css_sanitize_declaration(declaration: tinycss2.ast.Declaration, eln_import_id: int, root_path: str, referenced_files: list[str]) -> bool:
    result = _css_sanitize_statement(declaration.value, root_path, eln_import_id, referenced_files)
    if not result:
        return False
    declaration.value = result
    return True


def _css_sanitize_at_rule(at_rule: tinycss2.ast.AtRule, eln_import_id: int, root_path: str, referenced_files: list[str]) -> bool:
    if at_rule.prelude:
        if not _css_sanitize_at_rule_head(at_rule.lower_at_keyword, at_rule.prelude, eln_import_id, root_path, referenced_files):
            return False
    if at_rule.content:
        at_rule.content = _css_sanitize_at_rule_body(at_rule.content, eln_import_id, root_path, referenced_files)
    return True


def _css_sanitize_at_rule_head(at_key: str, prelude: list[tinycss2.ast.Node], eln_import_id: int, root_path: str, referenced_files: list[str]) -> bool:
    if at_key in WHITELIST_CSS_AT_RULES:
        return True
    elif at_key == 'import':
        url_token = None
        if isinstance(prelude[0], tinycss2.ast.WhitespaceToken):
            url_token = prelude[1]
        else:
            url_token = prelude[0]

        keep = False
        if isinstance(url_token, tinycss2.ast.StringToken):
            keep = _css_sanitize_url_string_token(url_token, eln_import_id=eln_import_id, root_path=root_path, referenced_files=referenced_files)
        elif isinstance(url_token, tinycss2.ast.FunctionBlock):
            keep = _css_sanitize_function(url_token, eln_import_id=eln_import_id, root_path=root_path, referenced_files=referenced_files)
        return keep

    return False


def _css_sanitize_at_rule_body(content: list[tinycss2.ast.Node], eln_import_id: int, root_path: str, referenced_files: list[str]) -> list[tinycss2.ast.Node]:
    grouped_statements = _css_group_by_statement(content)
    result = []
    for statement in grouped_statements:
        result.extend(_css_sanitize_statement(statement, root_path, eln_import_id, referenced_files))
    return result


def _css_group_by_statement(nodes: list[tinycss2.ast.Node]) -> list[list[tinycss2.ast.Node]]:
    result = []
    current_property = []
    for node in nodes:
        current_property.append(node)
        if (isinstance(node, tinycss2.ast.LiteralToken) and node == ";") or isinstance(node, tinycss2.ast.CurlyBracketsBlock):
            result.append(current_property)
            current_property = []
    result.append(current_property)

    return result


def _css_sanitize_statement(statement: list[tinycss2.ast.Node], root_path: str, eln_import_id: int, referenced_files: list[str]) -> list[tinycss2.ast.Node]:
    for idx, token in enumerate(statement):
        if isinstance(token, tinycss2.ast.AtKeywordToken):
            if not _css_sanitize_at_rule_head(token.lower_value, statement[(idx + 1):-1], eln_import_id=eln_import_id, root_path=root_path, referenced_files=referenced_files):
                return []
        elif isinstance(token, tinycss2.ast.FunctionBlock):
            if not _css_sanitize_function(token, root_path=root_path, eln_import_id=eln_import_id, referenced_files=referenced_files):
                return []
        elif isinstance(token, tinycss2.ast.URLToken):
            if not _css_sanitize_url_string_token(token, root_path=root_path, eln_import_id=eln_import_id, referenced_files=referenced_files):
                return []
        elif isinstance(token, tinycss2.ast.ParseError):
            return []
        elif isinstance(token, tinycss2.ast.CurlyBracketsBlock):
            _css_sanitize_curly_brackets_block(token, root_path=root_path, eln_import_id=eln_import_id, referenced_files=referenced_files)
    return statement


def _css_sanitize_curly_brackets_block(bracket_block: tinycss2.ast.CurlyBracketsBlock, root_path: str, eln_import_id: int, referenced_files: list[str]) -> None:
    grouped_statements = _css_group_by_statement(bracket_block.content)
    result = []
    for statement in grouped_statements:
        result.extend(_css_sanitize_statement(statement, root_path=root_path, eln_import_id=eln_import_id, referenced_files=referenced_files))
    bracket_block.content = result


def _css_sanitize_function(function_block: tinycss2.ast.FunctionBlock, root_path: str, eln_import_id: int, referenced_files: list[str]) -> bool:
    if function_block.type in WHITELIST_CSS_FUNCTIONS:
        return True
    elif function_block.type == 'url':
        if not isinstance(function_block.arguments[0], tinycss2.ast.StringToken):
            return False
        _css_sanitize_url_string_token(function_block.arguments[0], eln_import_id=eln_import_id, root_path=root_path, referenced_files=referenced_files)
    return False


def _css_sanitize_url_token(url_token: tinycss2.ast.URLToken, eln_import_id: int, root_path: str, referenced_files: list[str]) -> bool:
    keep, preview_url = _css_sanitize_url_string(url_token.value, eln_import_id, root_path, referenced_files)
    url_token.value = preview_url
    url_token.representation = f"url({preview_url})"
    return keep


def _css_sanitize_url_string_token(url_token: tinycss2.ast.StringToken, eln_import_id: int, root_path: str, referenced_files: list[str]) -> bool:
    keep, preview_url = _css_sanitize_url_string(url_token.value, eln_import_id, root_path, referenced_files)
    url_token.value = preview_url
    if url_token.representation.startswith("url(") and url_token.value != url_token.representation:
        url_token.representation = f"url({preview_url})"
    else:
        url_token.representation = preview_url
    return keep


def _css_sanitize_url_string(url: str, eln_import_id: int, root_path: str, referenced_files: list[str]) -> tuple[bool, str]:
    root_path = ""
    fullpath = os.path.join(root_path, url)
    normalized_fullpath = os.path.normpath(fullpath)
    preview_url = _transform_url_to_preview_url(normalized_fullpath, eln_import_id) or ""

    if not preview_url:
        return False, ""

    file_fullpath = normalized_fullpath.split("#")[0]
    if file_fullpath not in referenced_files:
        referenced_files.append(file_fullpath)
    return True, preview_url


def _transform_url_to_preview_url(normalized_fullpath: str, eln_import_id: int) -> typing.Optional[str]:
    if normalized_fullpath.startswith("/"):
        normalized_fullpath = normalized_fullpath[1:]

    if normalized_fullpath.startswith("ro-crate-preview.html"):
        return f"{flask.url_for(".eln_preview", eln_import_id=eln_import_id)}{normalized_fullpath[len("ro-crate-preview.html"):]}"
    elif normalized_fullpath.startswith("ro-crate-preview_files/"):
        referenced_subpath = normalized_fullpath[len("ro-crate-preview_files/"):]
        return flask.url_for(".eln_preview", eln_import_id=eln_import_id, subpath=referenced_subpath)
    return None
