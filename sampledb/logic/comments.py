# coding: utf-8
"""
Logic module for comments

Users with WRITE permissions can comment on samples or measurements. These
comments are immutable and therefore this module only allows the creation and
querying of comments.
"""

import typing

from .. import db
from . import user_log, object_log, objects, users, errors
from ..models import Comment


def create_comment(object_id: int, user_id: int, content: str) -> int:
    """
    Creates a new comment and adds it to the object and user logs.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param content: the text content for the new comment
    :return: the ID of the new comment
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """
    # ensure that the object exists
    objects.get_object(object_id)
    # ensure that the user exists
    users.get_user(user_id)
    comment = Comment(
        object_id=object_id,
        user_id=user_id,
        content=content
    )
    db.session.add(comment)
    db.session.commit()
    object_log.post_comment(user_id=user_id, object_id=object_id, comment_id=comment.id)
    user_log.post_comment(user_id=user_id, object_id=object_id, comment_id=comment.id)
    return comment.id


def get_comments_for_object(object_id: int) -> typing.List[Comment]:
    """
    Returns a list of comments for an object.

    :param object_id: the ID of an existing object
    :return: the list of comments, sorted from oldest to newest
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    comments = Comment.query.filter_by(object_id=object_id).order_by(db.asc(Comment.utc_datetime)).all()
    if not comments:
        # ensure that the object exists
        objects.get_object(object_id)
    return comments


def get_comment_for_object(object_id: int, comment_id: int) -> Comment:
    """
    Returns a specific comment for a given object.

    :param object_id: the ID of an existing object
    :param comment_id: the ID of an existing comment
    :return: the specified comment
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.CommentDoesNotExistError: when no comment with the given
        comment ID exists for this object
    """
    comment = Comment.query.filter_by(object_id=object_id, id=comment_id).first()
    if not comment:
        # ensure that the object exists
        objects.get_object(object_id)
        raise errors.CommentDoesNotExistError()
    return comment
