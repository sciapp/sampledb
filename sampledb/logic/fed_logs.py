# coding: utf-8
"""

"""
import typing
import datetime

from sampledb import db, models
from .actions import check_action_exists
from .action_types import check_action_type_exists
from .comments import get_comment
from .components import check_component_exists
from .files import get_file
from .instruments import check_instrument_exists
from .locations import check_location_exists, get_object_location_assignment, get_location_type
from .objects import check_object_exists
from .users import check_user_exists
from ..models import fed_logs


def _store_new_fed_user_log_entry(
        type: models.FedUserLogEntryType,
        user_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any]
) -> None:
    check_user_exists(user_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedUserLogEntry(
        type=type,
        user_id=user_id,
        component_id=component_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_user(user_id: int, component_id: int) -> None:
    _store_new_fed_user_log_entry(
        type=models.FedUserLogEntryType.IMPORT_USER,
        user_id=user_id,
        component_id=component_id,
        data={}
    )


def update_user(user_id: int, component_id: int) -> None:
    _store_new_fed_user_log_entry(
        type=models.FedUserLogEntryType.UPDATE_USER,
        user_id=user_id,
        component_id=component_id,
        data={}
    )


def create_ref_user(user_id: int, component_id: int) -> None:
    _store_new_fed_user_log_entry(
        type=models.FedUserLogEntryType.CREATE_REF_USER,
        user_id=user_id,
        component_id=component_id,
        data={}
    )


def _store_new_fed_object_log_entry(
        type: models.FedObjectLogEntryType,
        object_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any],
        user_id: typing.Optional[int] = None
) -> None:
    check_object_exists(object_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedObjectLogEntry(
        type=type,
        object_id=object_id,
        component_id=component_id,
        user_id=user_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_object(object_id: int, component_id: int, import_notes: typing.List[str], user_id: typing.Optional[int], version_id: int) -> None:
    _store_new_fed_object_log_entry(
        type=models.FedObjectLogEntryType.IMPORT_OBJECT,
        object_id=object_id,
        component_id=component_id,
        user_id=user_id,
        data={
            'version_id': version_id,
            'import_notes': import_notes
        }
    )


def update_object(object_id: int, component_id: int, import_notes: typing.List[str], user_id: typing.Optional[int], version_id: int) -> None:
    _store_new_fed_object_log_entry(
        type=models.FedObjectLogEntryType.UPDATE_OBJECT,
        object_id=object_id,
        component_id=component_id,
        user_id=user_id,
        data={
            'version_id': version_id,
            'import_notes': import_notes,
        }
    )


def share_object(object_id: int, component_id: int, user_id: typing.Optional[int]) -> None:
    _store_new_fed_object_log_entry(
        type=models.FedObjectLogEntryType.ADD_POLICY,
        object_id=object_id,
        component_id=component_id,
        user_id=user_id,
        data={}
    )


def update_object_policy(object_id: int, component_id: int, user_id: typing.Optional[int]) -> None:
    _store_new_fed_object_log_entry(
        type=models.FedObjectLogEntryType.UPDATE_OBJECT_POLICY,
        object_id=object_id,
        component_id=component_id,
        user_id=user_id,
        data={}
    )


def remote_import_object(object_id: int, component_id: int, import_status: typing.Dict[str, typing.Any]) -> None:
    _store_new_fed_object_log_entry(
        type=models.FedObjectLogEntryType.REMOTE_IMPORT_OBJECT,
        object_id=object_id,
        component_id=component_id,
        user_id=None,
        data={
            'import_status': import_status
        }
    )


def _store_new_fed_location_log_entry(
        type: models.FedLocationLogEntryType,
        location_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any]
) -> None:
    check_location_exists(location_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedLocationLogEntry(
        type=type,
        location_id=location_id,
        component_id=component_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_location(location_id: int, component_id: int) -> None:
    _store_new_fed_location_log_entry(
        type=models.FedLocationLogEntryType.IMPORT_LOCATION,
        location_id=location_id,
        component_id=component_id,
        data={}
    )


def update_location(location_id: int, component_id: int) -> None:
    _store_new_fed_location_log_entry(
        type=models.FedLocationLogEntryType.UPDATE_LOCATION,
        location_id=location_id,
        component_id=component_id,
        data={}
    )


def create_ref_location(location_id: int, component_id: int) -> None:
    _store_new_fed_location_log_entry(
        type=models.FedLocationLogEntryType.CREATE_REF_LOCATION,
        location_id=location_id,
        component_id=component_id,
        data={}
    )


def _store_new_fed_location_type_log_entry(
        type: models.FedLocationTypeLogEntryType,
        location_type_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any]
) -> None:
    get_location_type(location_type_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedLocationTypeLogEntry(
        type=type,
        location_type_id=location_type_id,
        component_id=component_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_location_type(location_type_id: int, component_id: int) -> None:
    _store_new_fed_location_type_log_entry(
        type=models.FedLocationTypeLogEntryType.IMPORT_LOCATION_TYPE,
        location_type_id=location_type_id,
        component_id=component_id,
        data={}
    )


def update_location_type(location_type_id: int, component_id: int) -> None:
    _store_new_fed_location_type_log_entry(
        type=models.FedLocationTypeLogEntryType.UPDATE_LOCATION_TYPE,
        location_type_id=location_type_id,
        component_id=component_id,
        data={}
    )


def create_ref_location_type(location_type_id: int, component_id: int) -> None:
    _store_new_fed_location_type_log_entry(
        type=models.FedLocationTypeLogEntryType.CREATE_REF_LOCATION_TYPE,
        location_type_id=location_type_id,
        component_id=component_id,
        data={}
    )


def _store_new_fed_action_log_entry(
        type: models.FedActionLogEntryType,
        action_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any]
) -> None:
    check_action_exists(action_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedActionLogEntry(
        type=type,
        action_id=action_id,
        component_id=component_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_action(action_id: int, component_id: int, import_notes: typing.List[str]) -> None:
    _store_new_fed_action_log_entry(
        type=models.FedActionLogEntryType.IMPORT_ACTION,
        action_id=action_id,
        component_id=component_id,
        data={
            'import_notes': import_notes
        }
    )


def update_action(action_id: int, component_id: int, import_notes: typing.List[str]) -> None:
    _store_new_fed_action_log_entry(
        type=models.FedActionLogEntryType.UPDATE_ACTION,
        action_id=action_id,
        component_id=component_id,
        data={
            'import_notes': import_notes
        }
    )


def create_ref_action(action_id: int, component_id: int) -> None:
    _store_new_fed_action_log_entry(
        type=models.FedActionLogEntryType.CREATE_REF_ACTION,
        action_id=action_id,
        component_id=component_id,
        data={}
    )


def _store_new_fed_action_type_log_entry(
        type: models.FedActionTypeLogEntryType,
        action_type_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any]
) -> None:
    check_action_type_exists(action_type_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedActionTypeLogEntry(
        type=type,
        action_type_id=action_type_id,
        component_id=component_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_action_type(action_type_id: int, component_id: int) -> None:
    _store_new_fed_action_type_log_entry(
        type=models.FedActionTypeLogEntryType.IMPORT_ACTION_TYPE,
        action_type_id=action_type_id,
        component_id=component_id,
        data={}
    )


def update_action_type(action_type_id: int, component_id: int) -> None:
    _store_new_fed_action_type_log_entry(
        type=models.FedActionTypeLogEntryType.UPDATE_ACTION_TYPE,
        action_type_id=action_type_id,
        component_id=component_id,
        data={}
    )


def create_ref_action_type(action_type_id: int, component_id: int) -> None:
    _store_new_fed_action_type_log_entry(
        type=models.FedActionTypeLogEntryType.CREATE_REF_ACTION_TYPE,
        action_type_id=action_type_id,
        component_id=component_id,
        data={}
    )


def _store_new_fed_instrument_log_entry(
        type: models.FedInstrumentLogEntryType,
        instrument_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any]
) -> None:
    check_instrument_exists(instrument_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedInstrumentLogEntry(
        type=type,
        instrument_id=instrument_id,
        component_id=component_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_instrument(instrument_id: int, component_id: int) -> None:
    _store_new_fed_instrument_log_entry(
        type=models.FedInstrumentLogEntryType.IMPORT_INSTRUMENT,
        instrument_id=instrument_id,
        component_id=component_id,
        data={}
    )


def update_instrument(instrument_id: int, component_id: int) -> None:
    _store_new_fed_instrument_log_entry(
        type=models.FedInstrumentLogEntryType.UPDATE_INSTRUMENT,
        instrument_id=instrument_id,
        component_id=component_id,
        data={}
    )


def create_ref_instrument(instrument_id: int, component_id: int) -> None:
    _store_new_fed_instrument_log_entry(
        type=models.FedInstrumentLogEntryType.CREATE_REF_INSTRUMENT,
        instrument_id=instrument_id,
        component_id=component_id,
        data={}
    )


def _store_new_fed_comment_log_entry(
        type: models.FedCommentLogEntryType,
        comment_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any]
) -> None:
    get_comment(comment_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedCommentLogEntry(
        type=type,
        comment_id=comment_id,
        component_id=component_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_comment(comment_id: int, component_id: int) -> None:
    _store_new_fed_comment_log_entry(
        type=models.FedCommentLogEntryType.IMPORT_COMMENT,
        comment_id=comment_id,
        component_id=component_id,
        data={}
    )


def update_comment(comment_id: int, component_id: int) -> None:
    _store_new_fed_comment_log_entry(
        type=models.FedCommentLogEntryType.UPDATE_COMMENT,
        comment_id=comment_id,
        component_id=component_id,
        data={}
    )


def _store_new_fed_file_log_entry(
        type: models.FedFileLogEntryType,
        file_id: int,
        object_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any]
) -> None:
    get_file(file_id, object_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedFileLogEntry(
        type=type,
        file_id=file_id,
        object_id=object_id,
        component_id=component_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_file(file_id: int, object_id: int, component_id: int) -> None:
    _store_new_fed_file_log_entry(
        type=models.FedFileLogEntryType.IMPORT_FILE,
        file_id=file_id,
        object_id=object_id,
        component_id=component_id,
        data={}
    )


def update_file(file_id: int, object_id: int, component_id: int) -> None:
    _store_new_fed_file_log_entry(
        type=models.FedFileLogEntryType.UPDATE_FILE,
        file_id=file_id,
        object_id=object_id,
        component_id=component_id,
        data={}
    )


def _store_new_fed_object_location_assignment_log_entry(
        type: fed_logs.FedObjectLocationAssignmentLogEntryType,
        object_location_assignment_id: int,
        component_id: int,
        data: typing.Dict[str, typing.Any]
) -> None:
    get_object_location_assignment(object_location_assignment_id)
    check_component_exists(component_id)
    log_entry = fed_logs.FedObjectLocationAssignmentLogEntry(
        type=type,
        object_location_assignment_id=object_location_assignment_id,
        component_id=component_id,
        data=data,
        utc_datetime=datetime.datetime.now(datetime.timezone.utc)
    )
    db.session.add(log_entry)
    db.session.commit()


def import_object_location_assignment(object_location_assignment_id: int, component_id: int) -> None:
    _store_new_fed_object_location_assignment_log_entry(
        type=fed_logs.FedObjectLocationAssignmentLogEntryType.IMPORT_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment_id,
        component_id=component_id,
        data={}
    )


def update_object_location_assignment(object_location_assignment_id: int, component_id: int) -> None:
    _store_new_fed_object_location_assignment_log_entry(
        type=fed_logs.FedObjectLocationAssignmentLogEntryType.UPDATE_OBJECT_LOCATION_ASSIGNMENT,
        object_location_assignment_id=object_location_assignment_id,
        component_id=component_id,
        data={}
    )


def get_fed_user_log_entries_for_user(user_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedUserLogEntry]:
    log_entries: typing.List[fed_logs.FedUserLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedUserLogEntry.query.filter_by(user_id=user_id, component_id=component_id).order_by(db.desc(fed_logs.FedUserLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedUserLogEntry.query.filter_by(user_id=user_id).order_by(db.desc(fed_logs.FedUserLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_user_exists(user_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_user_log_entries_for_component(component_id: int) -> typing.List[fed_logs.FedUserLogEntry]:
    log_entries: typing.List[fed_logs.FedUserLogEntry]
    log_entries = fed_logs.FedUserLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedUserLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries


def get_fed_object_log_entries_for_object(object_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedObjectLogEntry]:
    log_entries: typing.List[fed_logs.FedObjectLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedObjectLogEntry.query.filter_by(object_id=object_id, component_id=component_id).order_by(db.desc(fed_logs.FedObjectLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedObjectLogEntry.query.filter_by(object_id=object_id).order_by(db.desc(fed_logs.FedObjectLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_object_exists(object_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_object_log_entries_for_component(component_id: int) -> typing.List[fed_logs.FedObjectLogEntry]:
    log_entries: typing.List[fed_logs.FedObjectLogEntry]
    log_entries = fed_logs.FedObjectLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedObjectLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries


def get_fed_location_log_entries_for_location(location_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedLocationLogEntry]:
    log_entries: typing.List[fed_logs.FedLocationLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedLocationLogEntry.query.filter_by(location_id=location_id, component_id=component_id).order_by(db.desc(fed_logs.FedLocationLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedLocationLogEntry.query.filter_by(location_id=location_id).order_by(db.desc(fed_logs.FedLocationLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_location_exists(location_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_location_log_entries_for_component(component_id: int) -> typing.List[fed_logs.FedLocationLogEntry]:
    log_entries: typing.List[fed_logs.FedLocationLogEntry]
    log_entries = fed_logs.FedLocationLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedLocationLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries


def get_fed_location_type_log_entries_for_location_type(
        location_type_id: int,
        component_id: typing.Optional[int] = None
) -> typing.List[fed_logs.FedLocationTypeLogEntry]:
    log_entries: typing.List[fed_logs.FedLocationTypeLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedLocationTypeLogEntry.query.filter_by(location_type_id=location_type_id, component_id=component_id).order_by(db.desc(fed_logs.FedLocationTypeLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedLocationTypeLogEntry.query.filter_by(location_type_id=location_type_id).order_by(db.desc(fed_logs.FedLocationTypeLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        get_location_type(location_type_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_location_type_log_entries_for_component(
        component_id: int
) -> typing.List[fed_logs.FedLocationTypeLogEntry]:
    log_entries: typing.List[fed_logs.FedLocationTypeLogEntry]
    log_entries = fed_logs.FedLocationTypeLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedLocationTypeLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries


def get_fed_action_log_entries_for_action(action_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedActionLogEntry]:
    log_entries: typing.List[fed_logs.FedActionLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedActionLogEntry.query.filter_by(action_id=action_id, component_id=component_id).order_by(db.desc(fed_logs.FedActionLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedActionLogEntry.query.filter_by(action_id=action_id).order_by(db.desc(fed_logs.FedActionLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_action_exists(action_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_action_log_entries_for_component(component_id: int) -> typing.List[fed_logs.FedActionLogEntry]:
    log_entries: typing.List[fed_logs.FedActionLogEntry]
    log_entries = fed_logs.FedActionLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedActionLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries


def get_fed_action_type_log_entries_for_action_type(action_type_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedActionTypeLogEntry]:
    log_entries: typing.List[fed_logs.FedActionTypeLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedActionTypeLogEntry.query.filter_by(action_type_id=action_type_id, component_id=component_id).order_by(db.desc(fed_logs.FedActionTypeLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedActionTypeLogEntry.query.filter_by(action_type_id=action_type_id).order_by(db.desc(fed_logs.FedActionTypeLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_action_type_exists(action_type_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_action_type_log_entries_for_component(component_id: int) -> typing.List[fed_logs.FedActionTypeLogEntry]:
    log_entries: typing.List[fed_logs.FedActionTypeLogEntry]
    log_entries = fed_logs.FedActionTypeLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedActionTypeLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries


def get_fed_instrument_log_entries_for_instrument(instrument_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedInstrumentLogEntry]:
    log_entries: typing.List[fed_logs.FedInstrumentLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedInstrumentLogEntry.query.filter_by(instrument_id=instrument_id, component_id=component_id).order_by(db.desc(fed_logs.FedInstrumentLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedInstrumentLogEntry.query.filter_by(instrument_id=instrument_id).order_by(db.desc(fed_logs.FedInstrumentLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_instrument_exists(instrument_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_instrument_log_entries_for_component(component_id: int) -> typing.List[fed_logs.FedInstrumentLogEntry]:
    log_entries: typing.List[fed_logs.FedInstrumentLogEntry]
    log_entries = fed_logs.FedInstrumentLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedInstrumentLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries


def get_fed_comment_log_entries_for_comment(comment_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedCommentLogEntry]:
    log_entries: typing.List[fed_logs.FedCommentLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedCommentLogEntry.query.filter_by(comment_id=comment_id, component_id=component_id).order_by(db.desc(fed_logs.FedCommentLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedCommentLogEntry.query.filter_by(comment_id=comment_id).order_by(db.desc(fed_logs.FedCommentLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        get_comment(comment_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_comment_log_entries_for_object(object_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedCommentLogEntry]:
    log_entries: typing.List[fed_logs.FedCommentLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedCommentLogEntry.query.join(models.Comment).filter(models.Comment.object_id == object_id, models.FedCommentLogEntry.comment_id == models.Comment.id, models.FedCommentLogEntry.component_id == component_id).order_by(db.desc(fed_logs.FedCommentLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedCommentLogEntry.query.join(models.Comment).filter(models.Comment.object_id == object_id, models.FedCommentLogEntry.comment_id == models.Comment.id).order_by(db.desc(fed_logs.FedCommentLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_object_exists(object_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_comment_log_entries_for_component(component_id: int) -> typing.List[fed_logs.FedCommentLogEntry]:
    log_entries: typing.List[fed_logs.FedCommentLogEntry]
    log_entries = fed_logs.FedCommentLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedCommentLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries


def get_fed_file_log_entries_for_file(file_id: int, object_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedFileLogEntry]:
    log_entries: typing.List[fed_logs.FedFileLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedFileLogEntry.query.filter_by(file_id=file_id, object_id=object_id, component_id=component_id).order_by(db.desc(fed_logs.FedFileLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedFileLogEntry.query.filter_by(file_id=file_id, object_id=object_id).order_by(db.desc(fed_logs.FedFileLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        get_file(file_id, object_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_file_log_entries_for_object(object_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedFileLogEntry]:
    log_entries: typing.List[fed_logs.FedFileLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedFileLogEntry.query.filter_by(object_id=object_id, component_id=component_id).order_by(db.desc(fed_logs.FedFileLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedFileLogEntry.query.filter_by(object_id=object_id).order_by(db.desc(fed_logs.FedFileLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_object_exists(object_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_file_log_entries_for_component(component_id: int) -> typing.List[fed_logs.FedFileLogEntry]:
    log_entries: typing.List[fed_logs.FedFileLogEntry]
    log_entries = fed_logs.FedFileLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedFileLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries


def get_fed_object_location_assignment_log_entries_for_assignment(object_location_assignment_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedObjectLocationAssignmentLogEntry]:
    log_entries: typing.List[fed_logs.FedObjectLocationAssignmentLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedObjectLocationAssignmentLogEntry.query.filter_by(object_location_assignment_id=object_location_assignment_id, component_id=component_id).order_by(db.desc(fed_logs.FedObjectLocationAssignmentLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedObjectLocationAssignmentLogEntry.query.filter_by(object_location_assignment_id=object_location_assignment_id).order_by(db.desc(fed_logs.FedObjectLocationAssignmentLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        get_object_location_assignment(object_location_assignment_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_object_location_assignment_log_entries_for_object(object_id: int, component_id: typing.Optional[int] = None) -> typing.List[fed_logs.FedObjectLocationAssignmentLogEntry]:
    log_entries: typing.List[fed_logs.FedObjectLocationAssignmentLogEntry]
    if component_id is not None:
        log_entries = fed_logs.FedObjectLocationAssignmentLogEntry.query.join(models.ObjectLocationAssignment).filter(models.ObjectLocationAssignment.object_id == object_id, models.FedObjectLocationAssignmentLogEntry.object_location_assignment_id == models.ObjectLocationAssignment.id, models.FedObjectLocationAssignmentLogEntry.component_id == component_id).order_by(db.desc(fed_logs.FedObjectLocationAssignmentLogEntry.utc_datetime)).all()
    else:
        log_entries = fed_logs.FedObjectLocationAssignmentLogEntry.query.join(models.ObjectLocationAssignment).filter(models.ObjectLocationAssignment.object_id == object_id, models.FedObjectLocationAssignmentLogEntry.object_location_assignment_id == models.ObjectLocationAssignment.id).order_by(db.desc(fed_logs.FedObjectLocationAssignmentLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_object_exists(object_id)
        if component_id is not None:
            check_component_exists(component_id)
    return log_entries


def get_fed_object_location_assignment_log_entries_for_component(component_id: int) -> typing.List[fed_logs.FedObjectLocationAssignmentLogEntry]:
    log_entries: typing.List[fed_logs.FedObjectLocationAssignmentLogEntry]
    log_entries = fed_logs.FedObjectLocationAssignmentLogEntry.query.filter_by(component_id=component_id).order_by(db.desc(fed_logs.FedObjectLocationAssignmentLogEntry.utc_datetime)).all()
    if len(log_entries) == 0:
        check_component_exists(component_id)
    return log_entries
