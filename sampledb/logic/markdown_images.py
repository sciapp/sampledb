# coding: utf-8
"""
Users may upload images to SampleDB for use in Markdown content. As these
files already need to be available to the user while they are editing the
Markdown document, they are will be stored temporarily, only available to that
user. When the Markdown content is then saved, the images that are actually
referenced (via image elements after rendering the Markdown content to HTML)
will be made permanent.

As these images might be referenced from other places afterwards, an image
that was made permanent will not be deleted when its reference is removed from
the Markdown content that it was uploaded for.
"""

import binascii
import os
import typing

from bs4 import BeautifulSoup
import datetime
import flask

from .users import get_user
from ..models.markdown_images import MarkdownImage
from .. import db


def store_temporary_markdown_image(content: bytes, image_file_extension: str, user_id: int) -> str:
    """
    Store a file for use as an image in Markdown content.

    This also triggers the cleanup of previously uploaded temporary files.

    :param content: the binary content of the file
    :param image_file_extension: the file extension that should be used
    :param user_id: the ID of the user who uploaded the file
    :return: the generated file name to identify the image
    :raise errors.UserDoesNotExistError: if no user with the given ID exists
    """
    # ensure the user exists
    get_user(user_id)

    _remove_expired_images()

    # determine random file name
    num_tries = 10
    for _ in range(num_tries):
        file_name = binascii.b2a_hex(os.urandom(32)).decode('ascii') + image_file_extension
        if MarkdownImage.query.filter_by(file_name=file_name).first() is None:
            break
    else:
        # there should be close to no collisions with 32 random bytes, so if
        # several have occurred in a row, something must have been very wrong
        raise RuntimeError()

    image = MarkdownImage(file_name, content, user_id)
    db.session.add(image)
    db.session.commit()
    return file_name


def get_markdown_image(file_name: str, user_id: int) -> typing.Optional[bytes]:
    """
    Return the content of a Markdown image, if it is found.

    If the image is temporary, only the user who uploaded it may access it.

    :param file_name:
    :param user_id:
    :return: the binary file content or None
    """
    image = MarkdownImage.query.filter_by(file_name=file_name).first()
    if image is None:
        return None
    if image.user_id != user_id and not image.permanent:
        return None
    return image.content


def mark_referenced_markdown_images_as_permanent(html_content: str) -> None:
    """
    Find Markdown images referenced in an HTML snippet as permanent.

    :param html_content: the HTML content containing the image references
    """
    for file_name in find_referenced_markdown_images(html_content):
        _mark_markdown_image_permanent(file_name)


def _mark_markdown_image_permanent(file_name: str) -> None:
    image = MarkdownImage.query.filter_by(file_name=file_name, permanent=False).first()
    if image is None:
        return
    image.permanent = True
    db.session.add(image)
    db.session.commit()


def find_referenced_markdown_images(html_content: str) -> typing.Set[str]:
    file_names = set()
    base_image_url = flask.url_for('frontend.markdown_image', file_name='', _external=False)
    soup = BeautifulSoup(html_content, "html.parser")
    for image in soup.findAll('img'):
        image_url = image.get('src')
        if image_url.startswith(base_image_url):
            file_name = image_url[len(base_image_url):]
            file_names.add(file_name)
    return file_names


def _remove_expired_images():
    expiration_datetime = datetime.datetime.utcnow() - datetime.timedelta(days=2)
    expired_images = MarkdownImage.query.filter_by(permanent=False).filter(MarkdownImage.utc_datetime < expiration_datetime).all()
    for expired_image in expired_images:
        db.session.delete(expired_image)
    db.session.commit()
