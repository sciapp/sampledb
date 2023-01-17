# coding: utf-8
"""

"""
import dataclasses
import datetime
import typing

from .objects import get_object, check_object_exists
from .components import check_component_exists, Component
from .notifications import create_notification_for_a_failed_remote_object_import, create_notification_for_a_remote_object_import_with_notes
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
    utc_datetime: datetime.datetime
    component: Component
    user_id: typing.Optional[int]
    import_status: typing.Optional[typing.Dict[str, typing.Any]] = None

    @classmethod
    def from_database(cls, object_share: models.ObjectShare) -> 'ObjectShare':
        return ObjectShare(
            object_id=object_share.object_id,
            component_id=object_share.component_id,
            policy=object_share.policy,
            utc_datetime=object_share.utc_datetime,
            component=Component.from_database(object_share.component),
            user_id=object_share.user_id,
            import_status=object_share.import_status
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
        check_component_exists(component_id)
    return [
        ObjectShare.from_database(object_share)
        for object_share in shares
    ]


def get_shares_for_object(object_id: int) -> typing.List[ObjectShare]:
    shares = models.ObjectShare.query.filter_by(object_id=object_id).all()
    if len(shares) == 0:
        check_object_exists(object_id)
    return [
        ObjectShare.from_database(object_share)
        for object_share in shares
    ]


def get_object_if_shared(object_id: int, component_id: int) -> Object:
    obj = get_object(object_id)
    share = models.ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).all()
    if len(share) == 0:
        check_component_exists(component_id)
        raise errors.ObjectNotSharedError()
    return obj


def _get_mutable_share(object_id: int, component_id: int) -> models.ObjectShare:
    share: typing.Optional[models.ObjectShare] = models.ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).first()
    if share is None:
        check_object_exists(object_id)
        check_component_exists(component_id)
        raise errors.ShareDoesNotExistError()
    return share


def get_share(object_id: int, component_id: int) -> ObjectShare:
    share = _get_mutable_share(object_id, component_id)
    return ObjectShare.from_database(share)


def add_object_share(
        object_id: int,
        component_id: int,
        policy: typing.Dict[str, typing.Any],
        user_id: typing.Optional[int] = None
) -> ObjectShare:
    check_object_exists(object_id)
    check_component_exists(component_id)
    share = models.ObjectShare.query.filter_by(object_id=object_id, component_id=component_id).first()
    if share is not None:
        raise errors.ShareAlreadyExistsError()
    share = models.ObjectShare(object_id=object_id, component_id=component_id, policy=policy, user_id=user_id)
    db.session.add(share)
    db.session.commit()
    fed_logs.share_object(object_id, component_id, user_id=user_id)
    return ObjectShare.from_database(share)


def update_object_share(
        object_id: int,
        component_id: int,
        policy: typing.Dict[str, typing.Any],
        user_id: typing.Optional[int] = None
) -> ObjectShare:
    share = _get_mutable_share(object_id, component_id)
    if share.policy != policy:
        share.policy = policy
        share.user_id = user_id
        db.session.add(share)
        db.session.commit()
        fed_logs.update_object_policy(object_id, component_id, user_id=user_id)
    return ObjectShare.from_database(share)


def set_object_share_import_status(
        object_id: int,
        component_id: int,
        import_status: typing.Dict[str, typing.Any]
) -> None:
    share = _get_mutable_share(object_id, component_id)
    if share.import_status != import_status:
        if share.user_id:
            if not import_status['success'] and (share.import_status is None or share.import_status['success']):
                create_notification_for_a_failed_remote_object_import(share.user_id, object_id, component_id)
            elif import_status['success'] and import_status['notes'] and (share.import_status is None or not share.import_status['success'] or share.import_status['notes'] != import_status['notes']):
                create_notification_for_a_remote_object_import_with_notes(share.user_id, object_id, component_id, import_status['notes'])
        share.import_status = import_status
        db.session.add(share)
        db.session.commit()
        fed_logs.remote_import_object(
            object_id=object_id,
            component_id=component_id,
            import_status=import_status
        )


class ObjectShareImportStatus(typing.TypedDict):
    success: bool
    notes: typing.List[str]
    utc_datetime: str
    object_id: typing.Optional[int]


def parse_object_share_import_status(
        import_status: typing.Dict[str, typing.Any]
) -> typing.Optional[ObjectShareImportStatus]:
    if not isinstance(import_status, dict):
        return None
    import_status_keys = set(import_status.keys())
    if not all(isinstance(key, str) for key in import_status_keys):
        return None
    for key, value_type in [
        ('success', bool),
        ('notes', list),
        ('utc_datetime', str),
        ('object_id', (int, type(None)))
    ]:
        if key not in import_status_keys:
            return None
        if not isinstance(import_status[key], value_type):  # type: ignore
            return None
    success = import_status['success']
    notes = import_status['notes']
    if not all(isinstance(note, str) for note in notes):
        return None
    utc_datetime = import_status['utc_datetime']
    try:
        datetime.datetime.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None
    object_id = import_status['object_id']
    if success:
        if object_id is None or object_id <= 0:
            return None
    else:
        if object_id is not None:
            return None
    return ObjectShareImportStatus(
        success=success,
        notes=notes,
        utc_datetime=utc_datetime,
        object_id=object_id
    )
