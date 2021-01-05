# coding: utf-8
"""

"""

import sampledb
from sampledb.logic.markdown_to_html import markdown_to_safe_html, regenerate_cache, clear_cache
from sampledb.models import MarkdownToHTMLCacheEntry


def test_markdown_to_html_cache():
    assert markdown_to_safe_html("test") == "<p>test</p>"
    assert MarkdownToHTMLCacheEntry.query.filter_by(markdown="test").first().html == "<p>test</p>"

    sampledb.db.session.delete(MarkdownToHTMLCacheEntry.query.filter_by(markdown="test").first())
    sampledb.db.session.commit()
    sampledb.db.session.add(MarkdownToHTMLCacheEntry(markdown="test", html="value", parameters={'anchor_prefix': 'markdown-anchor'}))
    sampledb.db.session.commit()
    assert markdown_to_safe_html("test") == "value"

    regenerate_cache()
    assert MarkdownToHTMLCacheEntry.query.filter_by(markdown="test").first().html == "<p>test</p>"
    assert markdown_to_safe_html("test") == "<p>test</p>"

    clear_cache()
    assert MarkdownToHTMLCacheEntry.query.filter_by(markdown="test").first() is None


def test_escape_html_in_markdown():
    assert markdown_to_safe_html("<br />test") == "<p>&lt;br /&gt;test</p>"
