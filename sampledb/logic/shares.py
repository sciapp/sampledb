# coding: utf-8
"""

"""

import typing

from ..models.shares import ObjectShare
from .objects import get_object
from .components import get_component
from . import errors, fed_logs
from .. import db, models


def get_all_shares() -> typing.List[ObjectShare]:
    """
    Returns a list of all existing shared objects.

    :return: the list of shares
    """
    return ObjectShare.query.all()


def get_shares_for_component(component_id: int):
    """
    Returns a list of all objects shared with a component.

    :param: the component's ID
    :return: the list of shares
    """
    shares = ObjectShare.query.filter_by(component_id=component_id).all()
    if len(shares) == 0:
        get_component(component_id)
    return shares


def get_shares_for_object(object_id: int):
    shares = ObjectShare.query.filter_by(object_id=object_id).all()
    if len(shares) == 0:
        get_object(object_id)
    return shares


def get_object_if_shared(object_id: int, component_id: int):
    obj = get_object(object_id)
    share = ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).all()
    if len(share) == 0:
        get_component(component_id)
        raise errors.ObjectNotSharedError()
    return obj


def get_share(object_id: int, component_id: int):
    share = ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).first()
    if share is None:
        get_object(object_id)
        get_component(component_id)
        raise errors.ShareDoesNotExistError()
    return share


def add_object_share(object_id: int, component_id: int, policy: dict):
    get_object(object_id)
    get_component(component_id)
    share = models.ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).first()
    if share is not None:
        raise errors.ShareAlreadyExistsError()
    share = ObjectShare(object_id=object_id, component_id=component_id, policy=policy)
    db.session.add(share)
    db.session.commit()
    fed_logs.share_object(object_id, component_id)
    return share


def update_object_share(object_id: int, component_id: int, policy: dict):
    share = models.ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).first()
    if share is None:
        get_object(object_id)
        get_component(component_id)
        raise errors.ShareDoesNotExistError()
    if share.policy != policy:
        share.policy = policy
        db.session.add(share)
        db.session.commit()
        fed_logs.update_object_policy(object_id, component_id)
    return share
