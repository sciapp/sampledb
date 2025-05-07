from dataclasses import dataclass, field
import typing
import hashlib
import json
import datetime
import copy
import enum

import flask

from ... import db
from .. import errors
from .. import datatypes
from ..users import get_user
from ..components import get_component, Component
from ...models import ObjectVersionConflict as ObjectVersionConflictModel
from ..objects import get_object, get_conflicting_federated_object_version, get_first_conflicting_object_version_by_conflict, update_object, get_current_object_version_id, check_object_exists
from ..shares import get_share, get_object_import_specification
from ..schemas import calculate_diff, extract_diff_paths, validate
from ..schemas.data_diffs import VALUE_NOT_SET
from ..object_log import solve_version_conflict


class SolvingStrategy(enum.Enum):
    APPLY_LOCAL = 'apply_local'
    APPLY_IMPORTED = 'apply_imported'
    AUTOMERGE = 'automerge'


@dataclass(frozen=True)
class ObjectVersionConflict:
    object_id: int
    fed_version_id: int
    component_id: int

    base_version_id: int
    solver_id: typing.Optional[int]
    version_solved_in: typing.Optional[int]
    local_version_id: typing.Optional[int]
    discarded: bool
    automerged: bool

    _component_cache: typing.List[Component] = field(default_factory=lambda: [], repr=False, kw_only=True)

    @property
    def component(self) -> Component:
        if len(self._component_cache) == 0:
            self._component_cache.append(get_component(self.component_id))
        return self._component_cache[0]

    @classmethod
    def from_database(cls, object_version_conflict: ObjectVersionConflictModel) -> 'ObjectVersionConflict':
        return ObjectVersionConflict(
            object_id=object_version_conflict.object_id,
            fed_version_id=object_version_conflict.fed_version_id,
            component_id=object_version_conflict.component_id,
            base_version_id=object_version_conflict.base_version_id,
            solver_id=object_version_conflict.solver_id,
            version_solved_in=object_version_conflict.version_solved_in,
            local_version_id=object_version_conflict.local_version_id,
            discarded=object_version_conflict.discarded,
            automerged=object_version_conflict.automerged
        )


def calculate_data_hash(
    data: typing.Optional[dict[str, typing.Any]],
    schema: typing.Optional[dict[str, typing.Any]],
    object_id: typing.Optional[int] = None
) -> typing.Optional[str]:
    """
    Calculates the data hash used to compare object versions during bidirectional object synchronization.

    :param data: the data of the object
    :param schema: the data of the object
    :param object_id: the ID of the object
    :return: the hash value or none if data or schema is None
    """
    if data is None or schema is None:
        return None
    data = copy.deepcopy(data)
    _prepare_data(object_id=object_id, data=data)
    data_content = json.dumps({
        'data': data,
        'schema': schema
    }, sort_keys=True, cls=datatypes.JSONEncoder)

    return hashlib.sha256(data_content.encode('utf-8')).hexdigest()


def calculate_metadata_hash(
    user_id: typing.Optional[int],
    utc_datetime: datetime.datetime
) -> str:
    """
    Calculates the metadata hash used to compare object versions during bidirectional object synchronization.

    :param user_id: the ID of an existing user or none if automerged
    :param utc_datetime: the datetime (in UTC) when the object version was created
    :return: the hash value of the metadata
    """
    if user_id is not None:
        version_author = get_user(user_id)
        if version_author.component_id is not None and version_author.fed_id is not None:
            fed_uuid = get_component(version_author.component_id).uuid
        else:
            fed_uuid = flask.current_app.config['FEDERATION_UUID']
        user_data: typing.Any = {
            'fed_uuid': fed_uuid,
            'user_id': version_author.fed_id if version_author.fed_id else version_author.id
        }
    else:
        user_data = 'automerged'

    metadata_content = json.dumps({
        'user': user_data,
        'utc_datetime': utc_datetime.strftime('%Y-%m-%d %H:%M:%S')
    }, sort_keys=True)
    return hashlib.sha256(metadata_content.encode('utf-8')).hexdigest()


def get_object_conflicts(
    object_id: typing.Optional[int] = None,
    component_id: typing.Optional[int] = None,
    solved: typing.Optional[bool] = None
) -> list[ObjectVersionConflict]:
    """
    Gets all object conflicts matching the specified filters.

    :param object_id: the ID of an object or none
    :param component_id: the ID of a component or none
    :param solved: True or False if filter for solved or unsolved. None if solved and unsolved.
    :return: all object version conflicts that match the specified filters
    """
    query = ObjectVersionConflictModel.query.filter(ObjectVersionConflictModel.discarded.is_(False))
    if object_id is not None:
        query = query.filter(ObjectVersionConflictModel.object_id == object_id)

    if component_id is not None:
        query = query.filter(ObjectVersionConflictModel.component_id == component_id)

    if solved is not None:
        if solved:
            query = query.filter(ObjectVersionConflictModel.version_solved_in.isnot(None))
        else:
            query = query.filter(ObjectVersionConflictModel.version_solved_in.is_(None))

    return [ObjectVersionConflict.from_database(conflict) for conflict in query.all()]


def get_object_conflict_from_solution(
        object_id: int,
        version_solved_in: int
) -> ObjectVersionConflict:
    """
    Gets the object version conflict of the object which was solved in the specified version.

    :param object_id: the ID of an existing object
    :param version_solved_in: the version ID an object was solved in
    :return: the object version conflict which was solved in version_solved_in
    :raise errors.ObjectVersionConflictDoesNotExistError: if no object version conflict was solved in the specified object version
    """
    conflict = ObjectVersionConflictModel.query.filter(
        ObjectVersionConflictModel.object_id == object_id,
        ObjectVersionConflictModel.version_solved_in == version_solved_in
    ).first()

    if not conflict:
        raise errors.ObjectVersionConflictDoesNotExistError()
    return ObjectVersionConflict.from_database(conflict)


def check_object_has_unsolved_conflicts(object_id: int) -> bool:
    """
    Checks if the specified object has unsolved conflicts.

    :param object_id: the ID of an object
    :return: True if the object has at least one unsolved conflicts
    """
    return ObjectVersionConflictModel.query.filter(
        ObjectVersionConflictModel.object_id == object_id,
        ObjectVersionConflictModel.version_solved_in.is_(None),
        ObjectVersionConflictModel.discarded.is_(False)
    ).first() is not None


def get_solvable_conflicts(object_id: int) -> list[ObjectVersionConflict]:
    """
    Gets all solvable (data is available) conflicts for a specified object.

    :param object_id: the ID of an object
    :return: all solvable conflicts for the specified object
    """
    object = get_object(object_id)
    result: list[ObjectVersionConflict] = []

    conflicts = get_object_conflicts(object_id, solved=False)
    for conflict in conflicts:
        if object.component_id is not None:
            import_specification = get_object_import_specification(object_id)
            data_access = import_specification.data if import_specification else False
        else:
            share = get_share(object_id, component_id=conflict.component_id)
            data_access = share.policy.get("access", {}).get("data", False)

        imported_version = get_conflicting_federated_object_version(
            object_id,
            fed_version_id=conflict.fed_version_id,
            version_component_id=conflict.component_id
        )
        if data_access and imported_version.data is not None:
            result.append(conflict)

    return result


def get_object_version_conflict(
    object_id: int,
    component_id: typing.Optional[int] = None,
    fed_version_id: typing.Optional[int] = None,
    only_unsolved: bool = False
) -> ObjectVersionConflict:
    """
    Gets the specified object version conflict.

    :param object_id: the ID of an object
    :param component_id: the ID of a specific component or none
    :param fed_version_id: the federated object version ID or none
    :param only_unsolved: True if only unsolved conflicts should be returned
    """
    conflict_query = ObjectVersionConflictModel.query.filter(
        ObjectVersionConflictModel.object_id == object_id
    )

    if component_id is not None:
        conflict_query = conflict_query.filter(ObjectVersionConflictModel.component_id == component_id)

    if fed_version_id is None:
        conflict_query = conflict_query.filter(ObjectVersionConflictModel.discarded.is_(False))
    else:
        conflict_query = conflict_query.filter(ObjectVersionConflictModel.fed_version_id == fed_version_id)

    if only_unsolved:
        conflict_query = conflict_query.filter(ObjectVersionConflictModel.version_solved_in.is_(None))

    conflict = conflict_query.order_by(ObjectVersionConflictModel.fed_version_id.desc()).first()
    if not conflict:
        raise errors.ObjectVersionConflictDoesNotExistError()
    return ObjectVersionConflict.from_database(conflict)


def get_object_ids_with_conflicts_by_object_ids(
    object_ids: list[int],
    only_unsolved: bool = True
) -> list[int]:
    """
    Filters the object_ids parameter for objects that have conflicts.

    :param object_ids: the IDs of objects
    :param only_unsolved: True if only unsolved conflicts should be filtered for
    :return: the IDs of objects with conflicts
    """
    conflicts_query = ObjectVersionConflictModel.query.filter(
        ObjectVersionConflictModel.object_id.in_(object_ids),
        ObjectVersionConflictModel.discarded.is_(False)
    )

    if only_unsolved:
        conflicts_query = conflicts_query.filter(ObjectVersionConflictModel.version_solved_in.is_(None))

    return [conflict.object_id for conflict in conflicts_query.all()]


def create_object_version_conflict(
    object_id: int,
    fed_version_id: int,
    component_id: int,
    base_version_id: int,
    version_solved_in: typing.Optional[int] = None,
    local_version_id: typing.Optional[int] = None,
    automerged: bool = False,
    solver_id: typing.Optional[int] = None,
) -> ObjectVersionConflict:
    """
    Creates a new object version conflict.

    :param object_id: the local ID of an existing object
    :param fed_version_id: the federated version ID of the object which is conflicting with the local object version
    :param component_id: the component ID of the federated object version
    :param base_version_id: the local version ID of the last identical version before `fed_version_id`
    :param version_solved_in: the local version ID of the conflict solution or none
    :param local_version_id: the local version ID of the latest local version which was used to solve the conflict or none
    :param automerged: True if the conflict was automatically merged
    :param solver_id: the local ID of the user who solved the conflict or none
    :return: the newly created object version conflict
    :raise errors.ObjectVersionConflictAlreadyExistsError: if the object version conflict already exists
    :raise errors.ObjectDoesNotExistError: if the `object_id` does not exist in the database
    """
    check_object_exists(object_id)

    try:
        conflict = get_object_version_conflict(object_id=object_id, fed_version_id=fed_version_id, component_id=component_id)
    except errors.ObjectVersionConflictDoesNotExistError:
        conflict = None

    if conflict is not None:
        raise errors.ObjectVersionConflictAlreadyExistsError()

    existing_conflicts = ObjectVersionConflictModel.query.filter(
        ObjectVersionConflictModel.object_id == object_id,
        ObjectVersionConflictModel.component_id == component_id,
        ObjectVersionConflictModel.fed_version_id < fed_version_id,
    ).all()

    for existing_conflict in existing_conflicts:
        if not existing_conflict.version_solved_in:
            existing_conflict.discarded = True
            db.session.add(existing_conflict)
    db.session.commit()

    conflictModel = ObjectVersionConflictModel(
        object_id=object_id,
        fed_version_id=fed_version_id,
        component_id=component_id,
        base_version_id=base_version_id,
        version_solved_in=version_solved_in,
        local_version_id=local_version_id,
        automerged=automerged,
        solver_id=solver_id
    )

    db.session.add(conflictModel)
    db.session.commit()

    return ObjectVersionConflict.from_database(conflictModel)


def update_object_version_conflict(
    object_id: int,
    fed_version_id: int,
    component_id: int,
    base_version_id: int,
    version_solved_in: typing.Optional[int] = None,
    local_version_id: typing.Optional[int] = None,
    automerged: bool = False,
    solver_id: typing.Optional[int] = None,
) -> None:
    """
    Updates an object version conflict.

    :param object_id: the local ID of an object
    :param fed_version_id: the federated version ID of the object which is conflicting with the local object version
    :param component_id: the component ID of the federated object version
    :param base_version_id: the local version ID of the last identical version before `fed_version_id`
    :param version_solved_in: the local version ID of the conflict solution or none
    :param local_version_id: the local version ID of the latest local version which was used to solve the conflict or none
    :param automerged: True if the conflict was automatically merged
    :param solver_id: the local ID of the user who solved the conflict or none
    :raise errors.ObjectVersionConflictDoesNotExistError: if the object version conflict does not exist
    """
    conflict = ObjectVersionConflictModel.query.filter_by(
        object_id=object_id,
        fed_version_id=fed_version_id,
        component_id=component_id,
    ).first()

    if conflict is None:
        raise errors.ObjectVersionConflictDoesNotExistError()
    conflict.base_version_id = base_version_id
    conflict.version_solved_in = version_solved_in
    conflict.local_version_id = local_version_id
    conflict.automerged = automerged
    conflict.solver_id = solver_id

    db.session.add(conflict)
    db.session.commit()


def solve_conflict(
    unsolved_conflict: ObjectVersionConflict,
    version_solved_in: int,
    local_version_id: int,
    solver_id: typing.Optional[int] = None,
    add_object_log: bool = True,
    automerged: bool = False
) -> None:
    """
    Marks an object version conflict as solved and sets properties for the conflict solution.

    :param unsolved_conflict: the unsolved object version conflict
    :param version_solved_in: the local object version ID the conflict was solved in
    :param local_version_id: the local version ID of the latest local version which was used to solve the conflict
    :param solver_id: the local user ID of the solver or none
    :param add_object_log: True if an object log entry should be created
    :param automerged: True if the conflict was automatically merged
    :raise errors.ObjectVersionConflictDoesNotExistError: if the object version conflict does not exist in the database
    :raise errors.ObjectVersionConflictAlreadyDiscardedError: if the object version conflict is marked as discarded
    :raise errors.ObjectVersionConflictAlreadySolvedError: if the object version conflict is already solved
    """
    conflict = ObjectVersionConflictModel.query.filter_by(
        object_id=unsolved_conflict.object_id,
        fed_version_id=unsolved_conflict.fed_version_id,
        component_id=unsolved_conflict.component_id
    ).first()

    if conflict is None:
        raise errors.ObjectVersionConflictDoesNotExistError()
    elif conflict.discarded:
        raise errors.ObjectVersionConflictAlreadyDiscardedError()
    elif conflict.version_solved_in is not None:
        raise errors.ObjectVersionConflictAlreadySolvedError()
    conflict.version_solved_in = version_solved_in
    conflict.local_version_id = local_version_id
    conflict.solver_id = solver_id
    conflict.automerged = automerged
    db.session.add(conflict)
    db.session.commit()

    if add_object_log and solver_id is not None:
        solve_version_conflict(
            user_id=solver_id,
            object_id=conflict.object_id,
            component_id=conflict.component_id,
            version_id=conflict.fed_version_id,
            solved_in=version_solved_in,
            automerged=automerged
        )


def get_next_object_version_conflict(
        object_id: int,
        component_id: int,
        base_version_id: int,
        current_fed_version_id: int
) -> typing.Optional[ObjectVersionConflict]:
    """
    Returns the latest object version conflict for an object and a component which has a specfic base version (`base_version_id`) and a higher federated version ID than `current_fed_version_id`.

    :param object_id: the local ID of an object
    :param component_id: the component ID of the federation partner
    :param base_version_id: the base version ID of the conflict
    :param current_fed_version_id: the current federated version ID
    :return: the latest object version conflict or none
    """
    conflict = ObjectVersionConflictModel.query.filter(
        ObjectVersionConflictModel.object_id == object_id,
        ObjectVersionConflictModel.component_id == component_id,
        ObjectVersionConflictModel.base_version_id == base_version_id,
        ObjectVersionConflictModel.fed_version_id >= current_fed_version_id,
        ObjectVersionConflictModel.discarded.is_(False),
    ).order_by(ObjectVersionConflictModel.fed_version_id.desc()).first()

    if conflict is None:
        return None
    return ObjectVersionConflict.from_database(conflict)


def get_changed_paths(conflict: ObjectVersionConflict) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
    """
    Returns all schema paths which were changed in the object version conflict specifically in the history since the base version.

    :param conflict: the object version conflict
    :return: the locally changed paths and the federated changed paths
    """
    def _convert_to_list_tuple(data: list[list[typing.Any]]) -> list[tuple[typing.Any]]:
        return [tuple(x) for x in data]

    def get_paths(data_before: dict[str, typing.Any] | None, data_after: dict[str, typing.Any] | None) -> set[tuple[str, ...]]:
        if data_before is None or data_after is None:
            return set()
        return set(_convert_to_list_tuple(extract_diff_paths(calculate_diff(data_before, data_after))))

    base_version = get_object(object_id=conflict.object_id, version_id=conflict.base_version_id)

    local_latest_version = get_object(object_id=conflict.object_id)
    local_changed_paths = get_paths(base_version.data, local_latest_version.data)
    for version_id in range(base_version.version_id + 1, local_latest_version.version_id):
        local_version = get_object(base_version.object_id, version_id=version_id)
        version_paths = get_paths(base_version.data, local_version.data)
        local_changed_paths.update(version_paths)

    first_conflicting_version = get_first_conflicting_object_version_by_conflict(
        object_id=conflict.object_id,
        version_component_id=conflict.component_id,
        local_parent=conflict.base_version_id
    )

    imported_changed_paths = get_paths(base_version.data, first_conflicting_version.data)

    for version_id in range(first_conflicting_version.fed_version_id + 1, conflict.fed_version_id):
        federated_object = get_conflicting_federated_object_version(
            object_id=conflict.object_id,
            fed_version_id=version_id,
            version_component_id=conflict.component_id
        )
        version_paths = get_paths(base_version.data, federated_object.data)
        imported_changed_paths.update(version_paths)

    return local_changed_paths, imported_changed_paths


def try_automerge_open_conflicts(object_id: int) -> None:
    """
    Tries to automerge all open conflicts for an object.

    :param object_id: the local ID of an object
    """
    open_conflicts = get_object_conflicts(object_id=object_id, solved=False)
    while len(open_conflicts) > 0:
        open_conflict = open_conflicts[0]
        try:
            solve_conflict_by_strategy(conflict=open_conflict, solving_strategy=SolvingStrategy.AUTOMERGE)
        except errors.FailedSolvingByStrategyError:
            open_conflicts.remove(open_conflict)
        else:
            open_conflicts = get_object_conflicts(object_id=object_id, solved=False)


def solve_conflict_by_strategy(
    conflict: ObjectVersionConflict,
    solving_strategy: SolvingStrategy,
    user_id: typing.Optional[int] = None,
    schema: typing.Optional[typing.Dict[str, typing.Any]] = None
) -> None:
    """
    Solves an object version conflict using a given strategy (`solving_strategy`) and tries to
    automerge other conflicts after solving the given one.

    :param conflict: an unsolved object version conflict
    :param solving_strategy: solving strategy to use
    :param user_id: the local user ID of the solver or none
    :param schema: the schema of the object or none
    :raise errors.ObjectVersionConflictAlreadySolvedError: if the object version conflict is already solved
    :raise errors.ObjectVersionConflictAlreadyDiscardedError: if the object version conflict is marked as discarded
    :raise errors.UnknownConflictSolvingStrategyError: if the given strategy is unknown
    :raise errors.FailedSolvingByStrategyError: if the conflict could not be solved by the given strategy
    """
    if conflict.version_solved_in is not None:
        raise errors.ObjectVersionConflictAlreadySolvedError()
    elif conflict.discarded:
        raise errors.ObjectVersionConflictAlreadyDiscardedError()
    elif solving_strategy not in list(SolvingStrategy):
        raise errors.UnknownConflictSolvingStrategyError()

    new_data: dict[str, typing.Any] = {}

    hash_data = None

    if solving_strategy == SolvingStrategy.AUTOMERGE:
        fully_solved, new_data = automerge_conflict(object_version_conflict=conflict)

        if not fully_solved:
            raise errors.FailedSolvingByStrategyError()

    elif solving_strategy == SolvingStrategy.APPLY_LOCAL:
        local_object = get_object(conflict.object_id)
        if local_object.data is None:
            raise errors.FailedSolvingByStrategyError()
        new_data = local_object.data
        hash_data = local_object.hash_data

    elif solving_strategy == SolvingStrategy.APPLY_IMPORTED:
        fed_object = get_conflicting_federated_object_version(
            object_id=conflict.object_id,
            fed_version_id=conflict.fed_version_id,
            version_component_id=conflict.component_id
        )
        if fed_object.data is None:
            raise errors.FailedSolvingByStrategyError()
        new_data = fed_object.data
        hash_data = fed_object.hash_data

    local_latest_version_id = get_current_object_version_id(conflict.object_id)

    object = get_object(conflict.object_id)
    if schema is None:
        if object.component_id is None:
            schema = object.schema
        else:
            fed_object = get_conflicting_federated_object_version(
                object_id=conflict.object_id,
                fed_version_id=conflict.fed_version_id,
                version_component_id=conflict.component_id,
            )
            if fed_object.schema is None:
                raise errors.FailedSolvingByStrategyError()
            schema = fed_object.schema

    if schema is None:
        raise errors.FailedSolvingByStrategyError()

    try:
        validate(new_data, schema=schema, component_id=object.component_id)
    except errors.ValidationError:
        raise errors.FailedSolvingByStrategyError()

    update_object(
        object_id=conflict.object_id,
        schema=schema,
        data=new_data,
        user_id=user_id,
        created_by_automerge=(solving_strategy == SolvingStrategy.AUTOMERGE),
        create_log_entries=False,
        version_component_id=conflict.component_id if solving_strategy == SolvingStrategy.APPLY_IMPORTED else None,
        hash_data=hash_data,
    )

    solved_version_id = get_current_object_version_id(conflict.object_id)

    solve_conflict(
        unsolved_conflict=conflict,
        version_solved_in=solved_version_id,
        local_version_id=local_latest_version_id,
        solver_id=user_id,
        automerged=(solving_strategy == SolvingStrategy.AUTOMERGE),
    )

    try_automerge_open_conflicts(object_id=conflict.object_id)


def automerge_conflict(
    object_version_conflict: ObjectVersionConflict,
    local_data: typing.Optional[dict[str, typing.Any]] = None,
    imported_data: typing.Optional[dict[str, typing.Any]] = None,
) -> tuple[bool, dict[str, typing.Any]]:
    """
    Try to automerge conflict data with additionally given local or imported data. If local or imported data is not given,
    the local or imported data of the object version conflict will be used to solve the conflict.

    The function does not change the object itself but returns the automerged data.

    :param object_version_conflict: an unsolved object version conflict
    :param local_data: the local data that should be used or none
    :param imported_data: the imported data that should be used or none
    :return: boolean if the conflict was fully merged and the new data
    :raise errors.FailedSolvingByStrategyError: if the conflict could not be automerged because the conflict associated versions do not contain data
    """
    base_version = get_object(object_version_conflict.object_id, object_version_conflict.base_version_id)
    local_version = get_object(object_version_conflict.object_id)
    imported_version = get_conflicting_federated_object_version(
        object_id=object_version_conflict.object_id,
        fed_version_id=object_version_conflict.fed_version_id,
        version_component_id=object_version_conflict.component_id
    )

    if base_version.data is None or local_version.data is None or imported_version.data is None:
        raise errors.FailedSolvingByStrategyError()

    local_paths, imported_paths = get_changed_paths(object_version_conflict)

    if base_version.component_id is None:
        latest_schema = local_version.schema
    else:
        latest_schema = imported_version.schema

    if local_data is None:
        local_data = local_version.data

    if imported_data is None:
        imported_data = imported_version.data

    return typing.cast(typing.Tuple[bool, typing.Dict[str, typing.Any]], _merge_data(
        base_data=base_version.data,
        local_data=local_data,
        imported_data=imported_data,
        schema=latest_schema,
        blocked_paths=local_paths.intersection(imported_paths),
        solving_strategy=SolvingStrategy.AUTOMERGE
    ))


def _merge_data(
    base_data: typing.Any,
    local_data: typing.Any,
    imported_data: typing.Any,
    schema: typing.Any,
    blocked_paths: set[tuple[str, ...]],
    solving_strategy: SolvingStrategy,
    current_path: typing.Optional[list[typing.Any]] = None,
) -> typing.Tuple[bool, typing.Dict[str, typing.Any] | typing.List[typing.Any]]:
    if current_path is None:
        current_path = []
    type_local = _guess_type(local_data)
    type_imported = _guess_type(imported_data)

    if type_local == type_imported or type_local is not None or type_imported is not None:
        if type_local == 'array':
            return _merge_data_array(base_data, local_data, imported_data, schema, blocked_paths, solving_strategy, current_path)
        elif type_local == 'object':
            return _merge_data_object(base_data, local_data, imported_data, schema, blocked_paths, solving_strategy, current_path)
        return _merge_default(base_data, local_data, imported_data, schema, blocked_paths, solving_strategy, current_path)

    result = {}
    if local_data != VALUE_NOT_SET:
        result['local'] = local_data
    if imported_data != VALUE_NOT_SET:
        result['imported'] = imported_data

    return False, result


def _merge_data_array(
    base_data: list[typing.Any],
    local_data: list[typing.Any],
    imported_data: list[typing.Any],
    schema: typing.Dict[str, typing.Any],
    blocked_paths: set[tuple[str, ...]],
    solving_strategy: SolvingStrategy,
    current_path: list[typing.Any],
) -> typing.Tuple[bool, typing.List[typing.Any]]:
    base_length = len(base_data) if base_data is not None else 0
    local_length = len(local_data) if local_data is not None else 0
    imported_length = len(imported_data) if imported_data is not None else 0

    result = []
    merged = True

    min_len = min(local_length, imported_length)

    for i in range(min_len):
        base_element = base_data[i] if i < base_length else {}
        local_element = local_data[i]
        imported_element = imported_data[i]

        new_path = current_path + [i]

        merged_fully, element_result = _merge_data(
            base_element,
            local_element,
            imported_element,
            schema=schema['items'],
            blocked_paths=blocked_paths,
            solving_strategy=solving_strategy,
            current_path=new_path
        )
        result.append(element_result)
        merged = merged and merged_fully

    if local_length < imported_length:
        result.extend(imported_data[local_length:])
    elif local_length > imported_length:
        result.extend(local_data[imported_length:])

    return merged, result


def _merge_data_object(
    base_data: typing.Dict[str, typing.Any],
    local_data: typing.Dict[str, typing.Any],
    imported_data: typing.Dict[str, typing.Any],
    schema: typing.Dict[str, typing.Any],
    blocked_paths: set[tuple[str, ...]],
    solving_strategy: SolvingStrategy,
    current_path: list[typing.Any]
) -> typing.Tuple[bool, typing.Dict[str, typing.Any]]:
    result = {}
    conflicts_detected = True

    for property_name in set(base_data) | set(local_data) | set(imported_data):
        data_base = base_data.get(property_name, None)
        data_local = local_data.get(property_name, None)
        data_imported = imported_data.get(property_name, None)

        new_path = current_path + [property_name]

        if property_name in schema['properties']:
            merged_fully, property_result = _merge_data(
                data_base,
                data_local,
                data_imported,
                schema=schema['properties'][property_name],
                blocked_paths=blocked_paths,
                solving_strategy=solving_strategy,
                current_path=new_path
            )
            result[property_name] = property_result

            conflicts_detected = conflicts_detected and merged_fully

    return conflicts_detected, result


def _merge_default(
    base_data: typing.Dict[str, typing.Any],
    local_data: typing.Dict[str, typing.Any],
    imported_data: typing.Dict[str, typing.Any],
    schema: typing.Dict[str, typing.Any],
    blocked_paths: set[tuple[str, ...]],
    solving_strategy: SolvingStrategy,
    current_path: list[typing.Any]
) -> typing.Tuple[bool, typing.Dict[str, typing.Any]]:
    if local_data != imported_data:
        if local_data == base_data and tuple(current_path) not in blocked_paths:
            return True, imported_data
        elif imported_data == base_data and tuple(current_path) not in blocked_paths:
            return True, local_data
        result = {}
        if solving_strategy == SolvingStrategy.AUTOMERGE:
            if local_data:
                result['local'] = local_data
            if imported_data:
                result['imported'] = imported_data
            return False, result
        elif solving_strategy == SolvingStrategy.APPLY_LOCAL:
            return True, local_data
        elif solving_strategy == SolvingStrategy.APPLY_IMPORTED:
            return True, imported_data

    return True, local_data


def _guess_type(data: typing.Any) -> typing.Optional[str]:
    if data == VALUE_NOT_SET or data is None:
        return None
    if isinstance(data, list):
        return 'array'
    elif '_type' in data:
        return str(data['_type'])
    return 'object'


def _prepare_data(object_id: typing.Optional[int], data: typing.Any) -> None:
    refs: list[tuple[str, int]] = []
    markdown_images: dict[str, str] = {}

    from .objects import entry_preprocessor
    entry_preprocessor(data=data, refs=refs, markdown_images=markdown_images, object_id=object_id)


def get_affected_components(conflict: ObjectVersionConflict) -> list[Component]:
    """
    Gets all components that are being affected by updating the object.

    :param conflict: the object version conflict
    :return: all components that are being affected
    """
    from ..shares import get_shares_for_object
    object = get_object(object_id=conflict.object_id)
    if object.component is not None:
        return [object.component]

    shares = get_shares_for_object(conflict.object_id)
    return [share.component for share in shares]
