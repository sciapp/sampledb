# coding: utf-8
"""

"""
import dataclasses
import datetime
import typing

from .objects import get_object
from .components import get_component, Component
from . import errors, fed_logs
from ..models import Object
from .. import db, models


@dataclasses.dataclass(frozen=True)
class ObjectShare:
    """
    This class provides an immutable wrapper around models.shares.ObjectShare.
    """
    object_id: int
    component_id: int
    policy: typing.Dict[str, typing.Any]
    utc_datetime: typing.Optional[datetime.datetime]
    component: typing.Optional[Component]

    @classmethod
    def from_database(cls, object_share: models.ObjectShare) -> 'ObjectShare':
        return ObjectShare(
            object_id=object_share.object_id,
            component_id=object_share.component_id,
            policy=object_share.policy,
            utc_datetime=object_share.utc_datetime,
            component=Component.from_database(object_share.component) if object_share.component is not None else None,
        )


def get_all_shares() -> typing.List[ObjectShare]:
    """
    Returns a list of all existing shared objects.

    :return: the list of shares
    """
    return [
        ObjectShare.from_database(object_share)
        for object_share in models.ObjectShare.query.all()
    ]


def get_shares_for_component(component_id: int) -> typing.List[ObjectShare]:
    """
    Returns a list of all objects shared with a component.

    :param: the component's ID
    :return: the list of shares
    """
    shares = models.ObjectShare.query.filter_by(component_id=component_id).all()
    if len(shares) == 0:
        get_component(component_id)
    return [
        ObjectShare.from_database(object_share)
        for object_share in shares
    ]


def get_shares_for_object(object_id: int) -> typing.List[ObjectShare]:
    shares = models.ObjectShare.query.filter_by(object_id=object_id).all()
    if len(shares) == 0:
        get_object(object_id)
    return [
        ObjectShare.from_database(object_share)
        for object_share in shares
    ]


def get_object_if_shared(object_id: int, component_id: int) -> Object:
    obj = get_object(object_id)
    share = models.ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).all()
    if len(share) == 0:
        get_component(component_id)
        raise errors.ObjectNotSharedError()
    return obj


def _get_mutable_share(object_id: int, component_id: int) -> models.ObjectShare:
    share: typing.Optional[models.ObjectShare] = models.ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).first()
    if share is None:
        get_object(object_id)
        get_component(component_id)
        raise errors.ShareDoesNotExistError()
    return share


def get_share(object_id: int, component_id: int) -> ObjectShare:
    share = _get_mutable_share(object_id, component_id)
    return ObjectShare.from_database(share)


def add_object_share(
        object_id: int,
        component_id: int,
        policy: typing.Dict[str, typing.Any]
) -> ObjectShare:
    get_object(object_id)
    get_component(component_id)
    share = models.ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).first()
    if share is not None:
        raise errors.ShareAlreadyExistsError()
    share = models.ObjectShare(object_id=object_id, component_id=component_id, policy=policy)
    db.session.add(share)
    db.session.commit()
    fed_logs.share_object(object_id, component_id)
    return ObjectShare.from_database(share)


def update_object_share(
        object_id: int,
        component_id: int,
        policy: typing.Dict[str, typing.Any]
) -> ObjectShare:
    share = _get_mutable_share(object_id, component_id)
    if share.policy != policy:
        share.policy = policy
        db.session.add(share)
        db.session.commit()
        fed_logs.update_object_policy(object_id, component_id)
    return ObjectShare.from_database(share)
