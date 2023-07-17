# coding: utf-8
"""
Logic module for comments

Users with WRITE permissions can comment on samples or measurements. These
comments are immutable and therefore this module only allows the creation and
querying of comments.
"""

import dataclasses
import datetime
import typing

from .. import db, models
from . import user_log, object_log, objects, users, errors, components


@dataclasses.dataclass(frozen=True)
class Comment:
    """
    This class provides an immutable wrapper around models.comments.Comment.
    """
    id: int
    object_id: int
    user_id: typing.Optional[int]
    author: typing.Optional[users.User]
    content: str
    utc_datetime: typing.Optional[datetime.datetime]
    fed_id: typing.Optional[int] = None
    component_id: typing.Optional[int] = None
    component: typing.Optional[components.Component] = None

    @classmethod
    def from_database(cls, comment: models.Comment) -> 'Comment':
        return Comment(
            id=comment.id,
            object_id=comment.object_id,
            user_id=comment.user_id,
            author=users.User.from_database(comment.author) if comment.author is not None else None,
            content=comment.content,
            utc_datetime=comment.utc_datetime,
            fed_id=comment.fed_id,
            component_id=comment.component_id,
            component=components.Component.from_database(comment.component) if comment.component is not None else None
        )


@typing.overload
def create_comment(
        object_id: int,
        user_id: int,
        content: str,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        *,
        create_log_entry: bool = True,
        fed_id: None = None,
        component_id: None = None
) -> int:
    ...


@typing.overload
def create_comment(
        object_id: int,
        user_id: typing.Optional[int],
        content: str,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        *,
        create_log_entry: bool = True,
        fed_id: int,
        component_id: int
) -> int:
    ...


def create_comment(
        object_id: int,
        user_id: typing.Optional[int],
        content: str,
        utc_datetime: typing.Optional[datetime.datetime] = None,
        *,
        create_log_entry: bool = True,
        fed_id: typing.Optional[int] = None,
        component_id: typing.Optional[int] = None
) -> int:
    """
    Creates a new comment and adds it to the object and user logs.

    :param object_id: the ID of an existing object
    :param user_id: the ID of an existing user
    :param content: the text content for the new comment
    :param utc_datetime: the creation time of the comment or None to select the current time
    :param create_log_entry: whether to create a log entry
    :param fed_id: the ID of the related comment at the exporting component
    :param component_id: the ID of the exporting component
    :return: the ID of the new comment
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    :raise errors.UserDoesNotExistError: when no user with the given user ID
        exists
    """

    assert (component_id is None) == (fed_id is None)
    assert component_id is not None or user_id is not None

    # ensure that the object exists
    objects.check_object_exists(object_id)
    if user_id is not None:
        # ensure that the user exists
        users.check_user_exists(user_id)
    if component_id is not None:
        # ensure that the component can be found
        components.check_component_exists(component_id)
    comment = models.Comment(
        object_id=object_id,
        user_id=user_id,
        content=content,
        fed_id=fed_id,
        component_id=component_id,
        utc_datetime=utc_datetime
    )
    db.session.add(comment)
    db.session.commit()
    if component_id is None and create_log_entry:
        # ensured by the if at the start of the function
        assert user_id is not None
        object_log.post_comment(user_id=user_id, object_id=object_id, comment_id=comment.id)
        user_log.post_comment(user_id=user_id, object_id=object_id, comment_id=comment.id)
    comment_id: int = comment.id
    return comment_id


def get_comment(comment_id: int, component_id: typing.Optional[int] = None) -> Comment:
    """
    :param comment_id: the federated ID of the comment
    :param component_id: the components ID (source)
    :return: the comment
    :raise errors.CommentDoesNotExistError: when no comment with the given ID exists
    """
    if component_id is None:
        comment = models.Comment.query.filter_by(id=comment_id).first()
    else:
        # ensure that the component can be found
        components.check_component_exists(component_id)
        comment = models.Comment.query.filter_by(fed_id=comment_id, component_id=component_id).first()
    if comment is None:
        raise errors.CommentDoesNotExistError()
    return Comment.from_database(comment)


def update_comment(
        comment_id: int,
        user_id: typing.Optional[int],
        content: str,
        utc_datetime: datetime.datetime
) -> None:
    """
    :param comment_id: the ID of an existing comment
    :param user_id: the ID of the (new) author
    :param content: the new content
    :param utc_datetime: the new datetime
    :raise errors.CommentDoesNotExistError: when no comment with the given ID
        exists
    """
    comment = models.Comment.query.filter_by(id=comment_id).first()
    if comment is None:
        raise errors.CommentDoesNotExistError()
    # user_id must not be None for local comments
    assert comment.component_id is not None or user_id is not None
    comment.user_id = user_id
    comment.content = content
    comment.utc_datetime = utc_datetime
    db.session.add(comment)
    db.session.commit()


def get_comments_for_object(object_id: int) -> typing.List[Comment]:
    """
    Returns a list of comments for an object.

    :param object_id: the ID of an existing object
    :return: the list of comments, sorted from oldest to newest
    :raise errors.ObjectDoesNotExistError: when no object with the given
        object ID exists
    """
    comments = models.Comment.query.filter_by(object_id=object_id).order_by(db.asc(models.Comment.utc_datetime)).all()
    if not comments:
        # ensure that the object exists
        objects.check_object_exists(object_id)
    return [
        Comment.from_database(comment)
        for comment in comments
    ]


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
    comment = models.Comment.query.filter_by(object_id=object_id, id=comment_id).first()
    if not comment:
        # ensure that the object exists
        objects.check_object_exists(object_id)
        raise errors.CommentDoesNotExistError()
    return Comment.from_database(comment)
