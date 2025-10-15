import typing
import datetime

from . import errors
from .. import db
from ..models import UpdatableObjectsCheck, UpdatableObjectsCheckStatus, AutomaticSchemaUpdate, AutomaticSchemaUpdateStatus
from . import background_tasks


def get_updatable_objects_checks() -> typing.Sequence[UpdatableObjectsCheck]:
    return UpdatableObjectsCheck.query.order_by(db.desc(UpdatableObjectsCheck.utc_datetime)).all()


def start_updatable_objects_checks(
        user_id: int,
        action_ids: typing.Optional[typing.Sequence[int]]
) -> UpdatableObjectsCheck:
    if db.session.query(db.exists().where(UpdatableObjectsCheck.status != UpdatableObjectsCheckStatus.DONE)).scalar():
        raise errors.UpdatableObjectsCheckAlreadyInProgressError()
    updatable_objects_check = UpdatableObjectsCheck(
        status=UpdatableObjectsCheckStatus.POSTED,
        user_id=user_id,
        utc_datetime=datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None),
        action_ids=action_ids,
        result=None,
    )
    db.session.add(updatable_objects_check)
    db.session.commit()
    background_tasks.post_check_for_automatic_schema_updates_task(updatable_objects_check_id=updatable_objects_check.id)
    return updatable_objects_check


def get_updatable_objects_check(
        updatable_objects_check_id: int
) -> UpdatableObjectsCheck:
    updatable_objects_check = UpdatableObjectsCheck.query.filter_by(id=updatable_objects_check_id).first()
    if updatable_objects_check is None:
        raise errors.UpdatableObjectsCheckDoesNotExistError()
    return updatable_objects_check


def set_updatable_objects_check_status(
        updatable_objects_check_id: int,
        status: UpdatableObjectsCheckStatus,
        result: typing.Dict[str, typing.Any]
) -> None:
    updatable_objects_check = UpdatableObjectsCheck.query.filter_by(id=updatable_objects_check_id).first()
    if updatable_objects_check is None:
        raise errors.UpdatableObjectsCheckDoesNotExistError()
    updatable_objects_check.status = status
    updatable_objects_check.result = result
    db.session.add(updatable_objects_check)
    db.session.commit()


def get_automatic_schema_updates() -> typing.Sequence[AutomaticSchemaUpdate]:
    return AutomaticSchemaUpdate.query.order_by(db.desc(AutomaticSchemaUpdate.utc_datetime)).all()


def start_automatic_schema_updates(
        user_id: int,
        updatable_objects_check_id: int,
        object_ids: typing.Sequence[int],
) -> AutomaticSchemaUpdate:
    if db.session.query(db.exists().where(AutomaticSchemaUpdate.status != AutomaticSchemaUpdateStatus.DONE)).scalar():
        raise errors.AutomaticSchemaUpdateAlreadyInProgressError()
    automatic_schema_update = AutomaticSchemaUpdate(
        status=AutomaticSchemaUpdateStatus.POSTED,
        user_id=user_id,
        utc_datetime=datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None),
        updatable_objects_check_id=updatable_objects_check_id,
        object_ids=object_ids,
        result=None,
    )
    db.session.add(automatic_schema_update)
    db.session.commit()
    background_tasks.post_perform_automatic_schema_updates_task(automatic_schema_update_id=automatic_schema_update.id)
    return automatic_schema_update


def get_automatic_schema_update(
        automatic_schema_update_id: int
) -> AutomaticSchemaUpdate:
    automatic_schema_update = AutomaticSchemaUpdate.query.filter_by(id=automatic_schema_update_id).first()
    if automatic_schema_update is None:
        raise errors.AutomaticSchemaUpdateDoesNotExistError()
    return automatic_schema_update


def set_automatic_schema_update_status(
        automatic_schema_update_id: int,
        status: AutomaticSchemaUpdateStatus,
        result: typing.Dict[str, typing.Any]
) -> None:
    automatic_schema_update = AutomaticSchemaUpdate.query.filter_by(id=automatic_schema_update_id).first()
    if automatic_schema_update is None:
        raise errors.AutomaticSchemaUpdateDoesNotExistError()
    automatic_schema_update.status = status
    automatic_schema_update.result = result
    db.session.add(automatic_schema_update)
    db.session.commit()
