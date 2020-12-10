# coding: utf-8
"""

"""

import bleach
from markdown import markdown as _markdown_to_html

from .. import db
from ..models import MarkdownToHTMLCacheEntry


def markdown_to_safe_html(markdown: str, use_cache: bool = True) -> str:
    """
    Convert Markdown content to (safe) HTML.

    This first escapes all HTML content in the Markdown text and then converts
    the result to HTML. The conversion may be cached to speed up repeated use
    for the same markdown content.

    :param markdown: the Markdown content to convert
    :param use_cache: whether the cache should be used
    :return: the content as HTML
    """
    if use_cache:
        cache_entry = MarkdownToHTMLCacheEntry.query.get(markdown)
        if cache_entry is not None and cache_entry.html is not None:
            return cache_entry.html

    html = _markdown_to_html(
        bleach.clean(markdown),
        extensions=['tables']
    )

    if use_cache:
        cache_entry = MarkdownToHTMLCacheEntry(markdown=markdown, html=html)
        db.session.add(cache_entry)
        db.session.commit()

    return html


def regenerate_cache() -> None:
    """
    Regenerate the cache for markdown_to_safe_html.
    """
    cache_entries = MarkdownToHTMLCacheEntry.query.all()
    for cache_entry in cache_entries:
        cache_entry.html = markdown_to_safe_html(cache_entry.markdown, use_cache=False)
        db.session.add(cache_entry)
    db.session.commit()


def clear_cache() -> None:
    """
    Clear the cache for markdown_to_safe_html.
    """
    MarkdownToHTMLCacheEntry.query.delete()
    db.session.commit()
