# coding: utf-8
"""

"""

import pytest

import sampledb
from sampledb.logic import markdown_images


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


def test_store_temporary_markdown_image(user):
    content = b'12345'
    file_name = markdown_images.store_temporary_markdown_image(content, '.png', user.id)
    assert file_name.endswith('.png')
    assert markdown_images.get_markdown_image(file_name, user.id) == content


def test_get_markdown_image(user):
    assert markdown_images.get_markdown_image("test.png", user.id) is None

    content = b'12345'
    file_name = markdown_images.store_temporary_markdown_image(content, '.png', user.id)
    assert file_name.endswith('.png')

    assert markdown_images.get_markdown_image(file_name, user.id) == content

    assert markdown_images.get_markdown_image(file_name, user.id + 1) is None

    markdown_images._mark_markdown_image_permanent(file_name)
    assert markdown_images.get_markdown_image(file_name, user.id + 1) == content


def test_remove_expired_images(user):
    content = b'12345'
    file_name = markdown_images.store_temporary_markdown_image(content, '.png', user.id)
    assert file_name.endswith('.png')

    image = sampledb.models.MarkdownImage.query.filter_by(file_name=file_name).first()
    sampledb.db.session.add(image)
    sampledb.db.session.commit()


def test_find_markdown_image_links(app):
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        assert sampledb.logic.markdown_images.find_referenced_markdown_images("") == set()
        assert sampledb.logic.markdown_images.find_referenced_markdown_images("""
        <img src="/markdown_images/test1.png" />
        <a href="/markdown_images/test2.png"></a>
        <img src="/markdown_images/test3.jpg" />
        """) == {"test1.png", "test3.jpg"}


def test_mark_referenced_markdown_images_as_permanent(flask_server, app, user):
    app.config['SERVER_NAME'] = 'localhost'
    with app.app_context():
        file_name1 = markdown_images.store_temporary_markdown_image(b'1', '.png', user.id)
        file_name2 = markdown_images.store_temporary_markdown_image(b'2', '.png', user.id)
        file_name3 = markdown_images.store_temporary_markdown_image(b'3', '.png', user.id)

        sampledb.logic.markdown_images.mark_referenced_markdown_images_as_permanent(
            f"""
            <img src="/markdown_images/{file_name1}" />
            <img src="/markdown_images/{file_name2}" />
            """
        )
        assert sampledb.models.markdown_images.MarkdownImage.query.filter_by(file_name=file_name1).first().permanent
        assert sampledb.models.markdown_images.MarkdownImage.query.filter_by(file_name=file_name2).first().permanent
        assert not sampledb.models.markdown_images.MarkdownImage.query.filter_by(file_name=file_name3).first().permanent

        sampledb.logic.markdown_images.mark_referenced_markdown_images_as_permanent(
            f"""
            <img src="/markdown_images/{file_name3}" />
            <img src="/markdown_images/{file_name2}" />
            """
        )
        assert sampledb.models.markdown_images.MarkdownImage.query.filter_by(file_name=file_name1).first().permanent
        assert sampledb.models.markdown_images.MarkdownImage.query.filter_by(file_name=file_name2).first().permanent
        assert sampledb.models.markdown_images.MarkdownImage.query.filter_by(file_name=file_name3).first().permanent
