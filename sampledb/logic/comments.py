# coding: utf-8
"""
Logic module for comments

Users with WRITE permissions can comment on samples or measurements. These
comments are immutable and therefore this module only allows the creation and
querying of comments.
"""

import datetime
import typing

from .. import db
from . import user_log, object_log, objects, users, errors, components
from ..models import Comment


def create_comment(object_id: int, user_id: typing.Optional[int], content: str, utc_datetime: typing.Optional[datetime.datetime] = None, fed_id: typing.Optional[int] = None, component_id: typing.Optional[int] = None) -> int:
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

    if (component_id is None) != (fed_id is None) or (component_id is None and user_id is None):
        raise TypeError('Invalid parameter combination.')

    # ensure that the object exists
    objects.get_object(object_id)
    if user_id is not None:
        # ensure that the user exists
        users.get_user(user_id)
    if component_id is not None:
        # ensure that the component can be found
        components.get_component(component_id)
    comment = Comment(
        object_id=object_id,
        user_id=user_id,
        content=content,
        fed_id=fed_id,
        component_id=component_id,
        utc_datetime=utc_datetime
    )
    db.session.add(comment)
    db.session.commit()
    if component_id is None:
        object_log.post_comment(user_id=user_id, object_id=object_id, comment_id=comment.id)
        user_log.post_comment(user_id=user_id, object_id=object_id, comment_id=comment.id)
    return comment.id


def get_comment(comment_id: int, component_id: typing.Optional[int] = None):
    """
    :param comment_id: the federated ID of the comment
    :param component_id: the components ID (source)
    :return: the comment
    """
    if component_id is None:
        comment = Comment.query.get(comment_id)
    else:
        # ensure that the component can be found
        components.get_component(component_id)
        comment = Comment.query.filter_by(fed_id=comment_id, component_id=component_id).first()
    if comment is None:
        raise errors.CommentDoesNotExistError()
    return comment


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
