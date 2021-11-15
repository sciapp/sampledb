# coding: utf-8
"""

"""

import pytest

import sampledb
from sampledb.logic.markdown_to_html import markdown_to_safe_html, regenerate_cache, clear_cache, get_markdown_from_object_data
from sampledb.models import MarkdownToHTMLCacheEntry


@pytest.fixture
def user(app):
    with app.app_context():
        user = sampledb.models.User(
            name='User',
            email="example@example.com",
            type=sampledb.models.UserType.PERSON
        )
        sampledb.db.session.add(user)
        sampledb.db.session.commit()
        assert user.id is not None
    return user


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


def test_get_markdown_from_object_data_str():
    data = {
        'name': {
            'text': 'name',
            '_type': 'text'
        },
        'comment': {
            'text': 'Image 1: ![image](/markdown_images/' + 64 * 'a' + '.png)',
            '_type': 'text',
            'is_markdown': True
        },
        'markdown': {
            'text': 'Image 2: ![image](/markdown_images/' + 64 * 'b' + '.png)',
            '_type': 'text',
            'is_markdown': True
        }
    }
    markdown = get_markdown_from_object_data(data)
    assert len(markdown) == 2
    assert 'Image 1: ![image](/markdown_images/' + 64 * 'a' + '.png)' in markdown
    assert 'Image 2: ![image](/markdown_images/' + 64 * 'b' + '.png)' in markdown


def test_get_markdown_from_object_data_dict():
    data = {
        'name': {
            'text': 'name',
            '_type': 'text'
        },
        'comment': {
            'text': {
                'en': 'Image 1: ![image](/markdown_images/' + 64 * 'a' + '.png)',
                'de': 'Bild 1: ![image](/markdown_images/' + 64 * 'c' + '.png)'
            },
            '_type': 'text',
            'is_markdown': True
        },
        'markdown': {
            'text': {
                'en': 'Image 2: ![image](/markdown_images/' + 64 * 'b' + '.png)',
                'de': 'Bild 2: ![image](/markdown_images/' + 64 * 'd' + '.png)'
            },
            '_type': 'text',
            'is_markdown': True
        }
    }
    markdown = get_markdown_from_object_data(data)
    assert len(markdown) == 4
    assert 'Image 1: ![image](/markdown_images/' + 64 * 'a' + '.png)' in markdown
    assert 'Image 2: ![image](/markdown_images/' + 64 * 'b' + '.png)' in markdown
    assert 'Bild 1: ![image](/markdown_images/' + 64 * 'c' + '.png)' in markdown
    assert 'Bild 2: ![image](/markdown_images/' + 64 * 'd' + '.png)' in markdown
