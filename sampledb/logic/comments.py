# coding: utf-8
"""

"""

import datetime
import typing

from .. import db
from . import user_log, object_log
from ..models import Comment


def create_comment(object_id: int, user_id: int, content: str, utc_datetime: datetime.datetime=None) -> None:
    comment = Comment(
        object_id=object_id,
        user_id=user_id,
        content=content,
        utc_datetime=utc_datetime
    )
    db.session.add(comment)
    db.session.commit()
    object_log.post_comment(user_id=user_id, object_id=object_id, comment_id=comment.id)
    user_log.post_comment(user_id=user_id, object_id=object_id, comment_id=comment.id)


def get_comments_for_object(object_id: int) -> typing.List[Comment]:
    comments = Comment.query.filter_by(object_id=object_id).order_by(db.asc(Comment.utc_datetime)).all()
    return comments
