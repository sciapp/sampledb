from datetime import datetime
import typing

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_bool, _get_utc_datetime, _get_translation, _get_dict
from .users import _parse_user_ref, _get_or_create_user_id, UserRef
from .locations import _get_or_create_location_id, _parse_location_ref, LocationRef
from ..locations import create_fed_assignment, get_fed_object_location_assignment, ObjectLocationAssignment, _get_mutable_object_location_assignment
from ..components import Component
from .. import errors, fed_logs, object_log
from ...models import Object
from ... import db


class ObjectLocationAssignmentData(typing.TypedDict):
    fed_id: int
    component_uuid: str
    location: typing.Optional[LocationRef]
    responsible_user: typing.Optional[UserRef]
    user: typing.Optional[UserRef]
    description: typing.Optional[typing.Dict[str, str]]
    utc_datetime: datetime
    confirmed: bool
    declined: bool


def import_object_location_assignment(
        assignment_data: ObjectLocationAssignmentData,
        object: Object,
        component: Component
) -> ObjectLocationAssignment:
    component_id = _get_or_create_component_id(assignment_data['component_uuid'])
    if component_id is not None:
        assignment = get_fed_object_location_assignment(assignment_data['fed_id'], component_id)
    else:
        assignment = _get_mutable_object_location_assignment(assignment_data['fed_id'])

    user_id = _get_or_create_user_id(assignment_data['user'])
    responsible_user_id = _get_or_create_user_id(assignment_data['responsible_user'])
    location_id = _get_or_create_location_id(assignment_data['location'])

    if assignment is None:
        assert component_id is not None
        assignment = create_fed_assignment(assignment_data['fed_id'], component_id, object.object_id, location_id, responsible_user_id, user_id, assignment_data['description'], assignment_data['utc_datetime'], assignment_data['confirmed'], assignment_data.get('declined', False))
        fed_logs.import_object_location_assignment(assignment.id, component.id)
        if user_id:
            object_log.assign_location(user_id, object_id=object.object_id, object_location_assignment_id=assignment.id, utc_datetime=assignment.utc_datetime, is_imported=True)
    elif assignment.location_id != location_id or assignment.user_id != user_id or assignment.responsible_user_id != responsible_user_id or assignment.description != assignment_data['description'] or assignment.object_id != object.object_id or assignment.confirmed != assignment_data['confirmed'] or assignment.declined != assignment_data.get('declined', False) or assignment.utc_datetime != assignment_data['utc_datetime']:
        assignment.location_id = location_id
        assignment.responsible_user_id = responsible_user_id
        assignment.user_id = user_id
        assignment.description = assignment_data['description']
        assignment.object_id = object.object_id
        assignment.confirmed = assignment_data['confirmed']
        assignment.utc_datetime = assignment_data['utc_datetime']
        assignment.declined = assignment_data.get('declined', False)
        db.session.commit()
        fed_logs.update_object_location_assignment(assignment.id, component.id)
    return ObjectLocationAssignment.from_database(assignment)


def parse_object_location_assignment(
        assignment_data: typing.Dict[str, typing.Any]
) -> ObjectLocationAssignmentData:
    uuid = _get_uuid(assignment_data.get('component_uuid'))
    fed_id = _get_id(assignment_data.get('id'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        # do not accept updates for own data
        raise errors.InvalidDataExportError(f'Invalid update for local object location assignment {fed_id} @ {uuid}')

    responsible_user_data = _get_dict(assignment_data.get('responsible_user'))
    location_data = _get_dict(assignment_data.get('location'))
    description = _get_translation(assignment_data.get('description'))
    if responsible_user_data is None and location_data is None and description is None:
        raise errors.InvalidDataExportError(f'Empty object location assignment {fed_id} @ {uuid}')

    return ObjectLocationAssignmentData(
        fed_id=fed_id,
        component_uuid=uuid,
        location=_parse_location_ref(location_data),
        responsible_user=_parse_user_ref(responsible_user_data),
        user=_parse_user_ref(_get_dict(assignment_data.get('user'))),
        description=description,
        utc_datetime=_get_utc_datetime(assignment_data.get('utc_datetime'), mandatory=True),
        confirmed=_get_bool(assignment_data.get('confirmed'), default=False),
        declined=_get_bool(assignment_data.get('declined'), default=False)
    )


def parse_import_object_location_assignment(
        assignment_data: typing.Dict[str, typing.Any],
        object: Object,
        component: Component
) -> ObjectLocationAssignment:
    return import_object_location_assignment(parse_object_location_assignment(assignment_data), object, component)
