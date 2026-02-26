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
    "class", "src", "href", "name", "content", "charset", "id", "lang", "rel", "type"
}


class ELNSanitizer:
    # Simple versioning for the sanitizer. It should be increased when changes were made to the sanitizer.
    # The version is used to detect changes to the sanitizer and update the sanitized content of files in the database.
    SANITIZER_VERSION = 1

    def __init__(self, eln_import_id: int, root_path: str, referenced_files: typing.Optional[list[str]]):
        self.eln_import_id = eln_import_id
        self.root_path = root_path
        if referenced_files is None:
            self.referenced_files = []
        else:
            self.referenced_files = referenced_files

    def sanitize(self, content: str, mime_type: str) -> str:
        """
        Sanitizes content based on its mime type. Currently only text/html and text/css are sanitized.

        :param content: String that should be sanitized
        :param mime_type: Mime type of content
        :return: Sanitized string if mime type is text/html or text/css. Otherwise an empty string is returned.
        """
        if mime_type == "text/html":
            return self._sanitize_html(content)
        if mime_type == "text/css":
            return self._sanitize_css_stylesheet(content)
        return ""

    def _sanitize_html(self, html_content: str) -> str:
        """
        Entrypoint for the html sanitization.

        :param html_content: HTML String that should be sanitized.
        :return: Sanitized `html_content`
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup.find_all():
            try:
                self._sanitize_html_attributes(tag)
                self._sanitize_html_tag(tag)
            except errors.ELNImportPreviewIllegalTagError:
                tag.unwrap()

        return str(soup)

    def _sanitize_html_attributes(self, tag: Tag) -> None:
        CUSTOM_ATTRIB_FILTERS = {
            "src": self._sanitize_html_attrib_file_reference("src"),
            "href": self._sanitize_html_attrib_file_reference("href"),
            "style": self._sanitize_html_attrib_style
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

    def _sanitize_html_attrib_file_reference(self, attrib: str) -> typing.Callable[[Tag], None]:
        def wrapped_filter(tag: Tag) -> None:
            src = tag[attrib]

            if not isinstance(src, str):
                del tag[attrib]
                return

            fullpath = os.path.normpath(os.path.join(self.root_path, src))
            preview_url = self._transform_url_to_preview_url(fullpath)
            if preview_url is not None:
                tag[attrib] = preview_url
                file_fullpath = fullpath.split("#")[0]
                if file_fullpath not in self.referenced_files:
                    self.referenced_files.append(file_fullpath)
            elif not src.startswith("#"):
                del tag[attrib]

        return wrapped_filter

    def _sanitize_html_attrib_style(self, tag: Tag) -> None:
        """
        Sanitizes css content of a style attribute.

        :return: Function that performs the sanitization of css attributes for a given tag.
        """
        style_content = tag["style"]
        style_parsed = tinycss2.parse_blocks_contents(style_content)
        style_sanitized = self._css_sanitize_rules(style_parsed)
        tag["style"] = tinycss2.serialize(style_sanitized)

    def _sanitize_html_tag(self, tag: Tag) -> None:
        CUSTOM_FILTERS = {
            "style": self._sanitize_html_tag_style,
            "link": self._sanitize_html_tag_link,
            "script": self._sanitize_script_script_tag,
        }

        if tag.name in CUSTOM_FILTERS:
            CUSTOM_FILTERS[tag.name](tag)
        elif tag.name in WHITELIST_TAGS:
            return
        else:
            raise errors.ELNImportPreviewIllegalTagError()

    def _sanitize_html_tag_style(self, tag: Tag) -> None:
        if tag.string is not None:
            tag.string = self._sanitize_css_stylesheet(tag.string)

    def _sanitize_html_tag_link(self, tag: Tag) -> None:
        href: typing.Optional[str] = tag.attrs.get("href", None)
        if href is None or not href.startswith("/"):
            tag.decompose()

    def _sanitize_script_script_tag(self, tag: Tag) -> None:
        tag.decompose()

    def _sanitize_css_stylesheet(self, css_content: str) -> str:
        """
        Parses and sanitizes a css stylesheet (css file content or content of <style>-tags).

        :param css_content: CSS string that should be sanitized.
        :return: Sanitized css string
        """
        parsed_rules = tinycss2.parse_stylesheet(css_content, skip_whitespace=True, skip_comments=True)
        sanitized_rules = self._css_sanitize_rules(parsed_rules)
        return typing.cast(str, tinycss2.serialize(sanitized_rules))

    def _css_sanitize_rules(self, css_rules: typing.List[tinycss2.ast.Node]) -> list[tinycss2.ast.Node]:
        result = []
        for rule in css_rules:
            if ((isinstance(rule, tinycss2.ast.QualifiedRule) and self._css_sanitize_qualified_rule(rule)) or
                (isinstance(rule, tinycss2.ast.AtRule) and self._css_sanitize_at_rule(rule)) or
                (isinstance(rule, tinycss2.ast.Declaration) and self._css_sanitize_declaration(rule)) or
                    (isinstance(rule, tinycss2.ast.WhitespaceToken))):
                result.append(rule)
        return result

    def _css_sanitize_qualified_rule(self, qualified_rule: tinycss2.ast.QualifiedRule) -> bool:
        grouped_statements = self._css_group_by_statement(qualified_rule.content)
        result = []
        for statement in grouped_statements:
            result.extend(self._css_sanitize_statement(statement))
        qualified_rule.content = result
        return True

    def _css_sanitize_declaration(self, declaration: tinycss2.ast.Declaration) -> bool:
        result = self._css_sanitize_statement(declaration.value)
        if not result:
            return False
        declaration.value = result
        return True

    def _css_sanitize_at_rule(self, at_rule: tinycss2.ast.AtRule) -> bool:
        if at_rule.prelude:
            if not self._css_sanitize_at_rule_head(at_rule.lower_at_keyword, at_rule.prelude):
                return False
        if at_rule.content:
            at_rule.content = self._css_sanitize_at_rule_body(at_rule.content)
        return True

    def _css_sanitize_at_rule_head(self, at_key: str, prelude: list[tinycss2.ast.Node]) -> bool:
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
                keep = self._css_sanitize_url_string_token(url_token)
            elif isinstance(url_token, tinycss2.ast.FunctionBlock):
                keep = self._css_sanitize_function(url_token)
            return keep

        return False

    def _css_sanitize_at_rule_body(self, content: list[tinycss2.ast.Node]) -> list[tinycss2.ast.Node]:
        grouped_statements = self._css_group_by_statement(content)
        result = []
        for statement in grouped_statements:
            result.extend(self._css_sanitize_statement(statement))
        return result

    def _css_group_by_statement(self, nodes: list[tinycss2.ast.Node]) -> list[list[tinycss2.ast.Node]]:
        result = []
        current_property = []
        for node in nodes:
            current_property.append(node)
            if (isinstance(node, tinycss2.ast.LiteralToken) and node == ";") or isinstance(node, tinycss2.ast.CurlyBracketsBlock):
                result.append(current_property)
                current_property = []
        result.append(current_property)
        return result

    def _css_sanitize_statement(self, statement: list[tinycss2.ast.Node]) -> list[tinycss2.ast.Node]:
        for idx, token in enumerate(statement):
            if isinstance(token, tinycss2.ast.AtKeywordToken):
                if not self._css_sanitize_at_rule_head(token.lower_value, statement[(idx + 1):-1]):
                    return []
            elif isinstance(token, tinycss2.ast.FunctionBlock):
                if not self._css_sanitize_function(token):
                    return []
            elif isinstance(token, tinycss2.ast.URLToken):
                if not self._css_sanitize_url_string_token(token):
                    return []
            elif isinstance(token, tinycss2.ast.ParseError):
                return []
            elif isinstance(token, tinycss2.ast.CurlyBracketsBlock):
                self._css_sanitize_curly_brackets_block(token)
        return statement

    def _css_sanitize_curly_brackets_block(self, bracket_block: tinycss2.ast.CurlyBracketsBlock) -> None:
        grouped_statements = self._css_group_by_statement(bracket_block.content)
        result = []
        for statement in grouped_statements:
            result.extend(self._css_sanitize_statement(statement))
        bracket_block.content = result

    def _css_sanitize_function(self, function_block: tinycss2.ast.FunctionBlock) -> bool:
        if function_block.type in WHITELIST_CSS_FUNCTIONS:
            return True
        elif function_block.type == 'url':
            if not isinstance(function_block.arguments[0], tinycss2.ast.StringToken):
                return False
            self._css_sanitize_url_string_token(function_block.arguments[0])
        return False

    def _css_sanitize_url_token(self, url_token: tinycss2.ast.URLToken) -> bool:
        keep, preview_url = self._css_sanitize_url_string(url_token.value)
        url_token.value = preview_url
        url_token.representation = f"url({preview_url})"
        return keep

    def _css_sanitize_url_string_token(self, url_token: tinycss2.ast.StringToken) -> bool:
        keep, preview_url = self._css_sanitize_url_string(url_token.value)
        url_token.value = preview_url
        if url_token.representation.startswith("url(") and url_token.value != url_token.representation:
            url_token.representation = f"url({preview_url})"
        else:
            url_token.representation = preview_url
        return keep

    def _css_sanitize_url_string(self, url: str) -> tuple[bool, str]:
        root_path = ""
        fullpath = os.path.join(root_path, url)
        normalized_fullpath = os.path.normpath(fullpath)
        preview_url = self._transform_url_to_preview_url(normalized_fullpath) or ""

        if not preview_url:
            return False, ""

        file_fullpath = normalized_fullpath.split("#")[0]
        if file_fullpath not in self.referenced_files:
            self.referenced_files.append(file_fullpath)
        return True, preview_url

    def _transform_url_to_preview_url(self, normalized_fullpath: str) -> typing.Optional[str]:
        """
        Transform the path to a given preview file within the eln archive into the required schema used by SampleDB.

        :param normalized_fullpath: Path to the preview file.
        :return: URL to the specified file or none if it is not a valid path to a preview file.
        """
        if normalized_fullpath.startswith("/"):
            normalized_fullpath = normalized_fullpath[1:]

        if normalized_fullpath.startswith("ro-crate-preview.html"):
            return f"{flask.url_for(".eln_preview", eln_import_id=self.eln_import_id)}{normalized_fullpath[len("ro-crate-preview.html"):]}"
        elif normalized_fullpath.startswith("ro-crate-preview_files/"):
            referenced_subpath = normalized_fullpath[len("ro-crate-preview_files/"):]
            return flask.url_for(".eln_preview", eln_import_id=self.eln_import_id, subpath=referenced_subpath)
        return None
