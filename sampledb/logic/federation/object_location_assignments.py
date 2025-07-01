from datetime import datetime
import typing

import flask

from .components import _get_or_create_component_id
from .utils import _get_id, _get_uuid, _get_bool, _get_utc_datetime, _get_translation, _get_dict
from .users import _parse_user_ref, _get_or_create_user_id, UserRef
from .locations import _get_or_create_location_id, _parse_location_ref, LocationRef
from ..locations import create_fed_assignment, get_fed_object_location_assignment, ObjectLocationAssignment, _get_mutable_object_location_assignment, get_object_location_assignment
from ..components import Component
from .. import errors, fed_logs, object_log
from ..users import get_user
from ...models import Object
from ... import db


class ObjectLocationAssignmentData(typing.TypedDict):
    id_or_fed_id: int
    component_uuid: typing.Optional[str]
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
) -> tuple[ObjectLocationAssignment, bool]:
    component_id = _get_or_create_component_id(assignment_data['component_uuid']) if assignment_data['component_uuid'] else None
    changes = False

    if component_id is not None:
        assignment = get_fed_object_location_assignment(assignment_data['id_or_fed_id'], component_id)
    else:
        try:
            assignment = _get_mutable_object_location_assignment(assignment_data['id_or_fed_id'])
        except errors.ObjectLocationAssignmentDoesNotExistError:
            assignment = None

    user_id = _get_or_create_user_id(assignment_data['user'])
    responsible_user_id = _get_or_create_user_id(assignment_data['responsible_user'])
    location_id = _get_or_create_location_id(assignment_data['location'])

    if assignment is None:
        assert component_id is not None
        assignment = create_fed_assignment(assignment_data['id_or_fed_id'], component_id, object.object_id, location_id, responsible_user_id, user_id, assignment_data['description'], assignment_data['utc_datetime'], assignment_data['confirmed'], assignment_data.get('declined', False))
        fed_logs.import_object_location_assignment(assignment.id, component.id)
        if user_id:
            object_log.assign_location(user_id, object_id=object.object_id, object_location_assignment_id=assignment.id, utc_datetime=assignment.utc_datetime, is_imported=True)
        changes = True
    elif assignment.location_id != location_id or assignment.user_id != user_id or assignment.responsible_user_id != responsible_user_id or assignment.description != assignment_data['description'] or assignment.object_id != object.object_id or assignment.confirmed != assignment_data['confirmed'] or assignment.declined != assignment_data.get('declined', False) or assignment.utc_datetime != assignment_data['utc_datetime']:
        assignment.location_id = location_id
        assignment.responsible_user_id = responsible_user_id
        assignment.user_id = user_id
        assignment.description = assignment_data['description']
        assignment.object_id = object.object_id
        assignment.utc_datetime = assignment_data['utc_datetime']
        if responsible_user_id is not None:
            try:
                responsible_user = get_user(responsible_user_id)
            except errors.UserDoesNotExistError:
                responsible_user = None
        else:
            responsible_user = None

        if responsible_user is not None and responsible_user.component_id is not None:
            assignment.confirmed = assignment_data['confirmed']
            assignment.declined = assignment_data.get('declined', False)
        db.session.commit()
        fed_logs.update_object_location_assignment(assignment.id, component.id)
        changes = True
    return ObjectLocationAssignment.from_database(assignment), changes


def parse_object_location_assignment(
        assignment_data: typing.Dict[str, typing.Any]
) -> typing.Optional[ObjectLocationAssignmentData]:
    uuid = _get_uuid(assignment_data.get('component_uuid'))
    id_or_fed_id = _get_id(assignment_data.get('id'))

    responsible_user_data = _get_dict(assignment_data.get('responsible_user'))
    location_data = _get_dict(assignment_data.get('location'))
    description = _get_translation(assignment_data.get('description'))
    if uuid == flask.current_app.config['FEDERATION_UUID']:
        try:
            get_object_location_assignment(object_location_assignment_id=id_or_fed_id)
        except errors.ObjectLocationAssignmentDoesNotExistError:
            raise errors.InvalidDataExportError(f'Local object location assignment {id_or_fed_id} does not exist')
        return None
    if responsible_user_data is None and location_data is None and description is None:
        raise errors.InvalidDataExportError(f'Empty object location assignment {id_or_fed_id} @ {uuid}')

    return ObjectLocationAssignmentData(
        id_or_fed_id=id_or_fed_id,
        component_uuid=uuid if uuid != flask.current_app.config['FEDERATION_UUID'] else None,
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
) -> tuple[ObjectLocationAssignment, bool]:
    if object_location_assignment := parse_object_location_assignment(assignment_data):
        return import_object_location_assignment(object_location_assignment, object, component)
    return get_object_location_assignment(assignment_data['id']), False
