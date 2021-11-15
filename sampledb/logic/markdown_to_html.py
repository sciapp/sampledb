# coding: utf-8
"""

"""

import bleach
from markdown import markdown as _markdown_to_html
from markdown.extensions.toc import TocExtension, slugify_unicode

from .. import db
from ..logic import errors
from ..models import MarkdownToHTMLCacheEntry


def markdown_to_safe_html(markdown: str, use_cache: bool = True, anchor_prefix: str = 'markdown-anchor') -> str:
    """
    Convert Markdown content to (safe) HTML.

    This first escapes all HTML content in the Markdown text and then converts
    the result to HTML. The conversion may be cached to speed up repeated use
    for the same markdown content.

    :param markdown: the Markdown content to convert
    :param use_cache: whether the cache should be used
    :param anchor_prefix: the prefix to use for anchors
    :return: the content as HTML
    """

    parameters = {
        'anchor_prefix': anchor_prefix
    }

    if use_cache:
        cache_entry = MarkdownToHTMLCacheEntry.query.filter(
            MarkdownToHTMLCacheEntry.markdown == markdown,
            MarkdownToHTMLCacheEntry.parameters['anchor_prefix'].astext == anchor_prefix
        ).first()
        if cache_entry is not None and cache_entry.html is not None:
            return cache_entry.html

    toc_extension = TocExtension(
        marker='',
        permalink=True,
        permalink_class='text-muted headerlink',
        slugify=lambda value, separator: slugify_unicode(anchor_prefix + '-' + value, separator)
    )

    html = _markdown_to_html(
        bleach.clean(markdown),
        extensions=[
            'tables',
            'sane_lists',
            'fenced_code',
            toc_extension
        ]
    )

    if use_cache:
        cache_entry = MarkdownToHTMLCacheEntry(markdown=markdown, parameters=parameters, html=html)
        db.session.add(cache_entry)
        db.session.commit()

    return html


def regenerate_cache() -> None:
    """
    Regenerate the cache for markdown_to_safe_html.
    """
    cache_entries = MarkdownToHTMLCacheEntry.query.all()
    for cache_entry in cache_entries:
        parameters = {}
        if 'anchor_prefix' in cache_entry.parameters:
            parameters['anchor_prefix'] = cache_entry.parameters['anchor_prefix']
        cache_entry.html = markdown_to_safe_html(
            cache_entry.markdown,
            use_cache=False,
            **parameters
        )
        db.session.add(cache_entry)
    db.session.commit()


def clear_cache() -> None:
    """
    Clear the cache for markdown_to_safe_html.
    """
    MarkdownToHTMLCacheEntry.query.delete()
    db.session.commit()


def get_markdown_from_object_data(data):
    """
    Extract Markdown text properties from object data.

    :param data: the object data to get Markdown text from
    :return: a list of all found Markdown texts
    """
    markdown_texts = []
    if isinstance(data, dict):
        properties = data.values()
    elif isinstance(data, list):
        properties = data
    else:
        return []
    for property in properties:
        if isinstance(property, dict) and '_type' in property:
            if property['_type'] == 'text' and property.get('is_markdown'):
                if isinstance(property.get('text'), str):
                    markdown_texts.append(property['text'])
                elif isinstance(property.get('text'), dict):
                    for text in property['text'].values():
                        markdown_texts.append(text)
                else:
                    raise errors.ValidationError('text must be str or a dictionary')
                continue
        else:
            markdown_texts.extend(get_markdown_from_object_data(property))
            continue
    return markdown_texts
