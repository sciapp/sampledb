import json
import typing
from dataclasses import dataclass
from functools import cached_property

import flask
from pydantic import BaseModel, Strict, model_validator, Field
from pydantic_core import PydanticCustomError

from .authentication import multi_auth, object_permissions_required
from ..utils import Resource, ResponseData
from ...logic import errors, locations, location_permissions, utils
from ...models import Permissions
from .utils.validation import ModelWithDefaultsFromValidationInfo, OptionalNotNone, UserId, is_expected_from_validation_info, populate_missing_or_expect_from_validation_info, method


@typing.overload
def _get_location(location_id: int, loc: str) -> locations.Location:
    pass


@typing.overload
def _get_location(location_id: None, loc: str) -> None:
    pass


def _get_location(location_id: typing.Optional[int], loc: str) -> typing.Optional[locations.Location]:
    if location_id is None:
        return None
    try:
        return locations.get_location(location_id)
    except errors.LocationDoesNotExistError:
        raise PydanticCustomError("no_suck_location", f"Location should exist ({loc})")


@typing.overload
def _get_location_type(type_id: int) -> locations.LocationType:
    pass


@typing.overload
def _get_location_type(type_id: None) -> None:
    pass


def _get_location_type(type_id: typing.Optional[int]) -> typing.Optional[locations.LocationType]:
    if type_id is None:
        return None
    try:
        return locations.get_location_type(type_id)
    except errors.LocationTypeDoesNotExistError:
        raise PydanticCustomError("no_such_location_type", "Location type should exist (type_id)")


if typing.TYPE_CHECKING:
    class _BaseLocation(typing.Protocol):
        @property
        def parent_location_id(self) -> typing.Optional[int]:
            pass

        @property
        def type(self) -> typing.Any:
            pass
else:
    class _BaseLocation(BaseModel):
        pass


class _ParentLocationMixin(_BaseLocation):
    @cached_property
    def parent_location(self) -> typing.Optional[locations.Location]:
        if self.parent_location_id is None:
            return None
        try:
            return locations.get_location(self.parent_location_id)
        except errors.LocationDoesNotExistError:
            raise PydanticCustomError("no_such_location", "Location should exist (parent_location_id)")

    @model_validator(mode="after")
    def check(self) -> typing.Self:
        self.parent_location, self.type  # pylint: disable=pointless-statement
        return self


def location_to_json(location: locations.Location) -> typing.Dict[str, typing.Any]:
    return {
        'location_id': location.id,
        'name': utils.get_translated_text(location.name, 'en') if location.name else None,
        'description': utils.get_translated_text(location.description, 'en'),
        'parent_location_id': location.parent_location_id,
        'type_id': location.type_id,
        'is_hidden': location.is_hidden,
        'enable_object_assignments': location.enable_object_assignments,
    }


def location_type_to_json(location_type: locations.LocationType) -> typing.Dict[str, typing.Any]:
    return {
        'location_type_id': location_type.id,
        'name': location_type.name.get('en', None) if location_type.name else None,
    }


def object_location_assignment_to_json(object_location_assignment: locations.ObjectLocationAssignment) -> typing.Dict[str, typing.Any]:
    return {
        'object_id': object_location_assignment.object_id,
        'location_id': object_location_assignment.location_id,
        'responsible_user_id': object_location_assignment.responsible_user_id,
        'user_id': object_location_assignment.user_id,
        'description': utils.get_translated_text(object_location_assignment.description, 'en'),
        'utc_datetime': object_location_assignment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S') if object_location_assignment.utc_datetime is not None else None
    }


class Location(Resource):
    class PathModel(BaseModel):
        location_id: int = Field(description="the ID of an existing location", examples=[1])

    @dataclass(frozen=True, slots=True)
    class ValidationContext:
        location: locations.Location

        @classmethod
        def from_path_model(cls, path: Location.PathModel) -> typing.Self:
            try:
                location = locations.get_location(path.location_id)
            except errors.LocationDoesNotExistError:
                flask.abort(flask.Response(json.dumps({"msg": "location does not exist"}), status=404, mimetype='application/json'))
            return cls(
                location=location
            )

    class RequestBodyModel(ModelWithDefaultsFromValidationInfo, _ParentLocationMixin):
        location_id: typing.Annotated[int, Strict(), populate_missing_or_expect_from_validation_info(lambda i: i.context.location.id)] = Field(description="the ID for the location to update, must match the location_id path parameter", examples=[1])
        name: str = Field(description="the name for the location to update", examples=["Example Location"])
        description: str = Field(description="the description for the location to update", examples=["This is an example location"])
        parent_location_id: typing.Annotated[typing.Optional[int], Strict()] = Field(description="the ID of the parent location for the location to update", examples=[1])
        type_id: typing.Annotated[int, Strict()] = Field(description="the location type ID for the location to create", examples=[-99])
        is_hidden: bool = Field(description="whether the location should be set to hidden", examples=[False])
        enable_object_assignments: bool = Field(description="whether object assignments should be enabled for the location to update", examples=[True])

        @cached_property
        def type(self) -> locations.LocationType:
            return _get_location_type(self.type_id)

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get a location.
        """
        try:
            location = locations.get_location(location_id=path.location_id)
        except errors.LocationDoesNotExistError:
            return {
                "message": f"location {path.location_id} does not exist"
            }, 404
        permissions = location_permissions.location_permissions.get_permissions_for_user(
            resource_id=path.location_id,
            user_id=flask.g.user.id,
            include_all_users=True,
            include_groups=True,
            include_projects=True,
            include_admin_permissions=True,
            limit_readonly_users=True
        )
        if Permissions.READ not in permissions:
            return flask.abort(403)
        return location_to_json(location)

    @multi_auth.login_required
    @method(request_body_context_builder=ValidationContext.from_path_model)
    def put(self, path: PathModel, request_body: RequestBodyModel) -> ResponseData:
        """
        Update a location.
        """
        if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask.g.user.is_admin:
            return {
                "message": "only administrators may manage locations"
            }, 403
        if Permissions.WRITE not in location_permissions.get_user_location_permissions(path.location_id, flask.g.user.id):
            return {
                "message": "insufficient permissions for location"
            }, 403
        if request_body.parent_location is not None:
            if Permissions.WRITE not in location_permissions.get_user_location_permissions(request_body.parent_location.id, flask.g.user.id):
                return {
                    "message": "insufficient permissions for parent location"
                }, 403
            if not request_body.parent_location.type.enable_sub_locations:
                return {
                    "message": "parent location type does not allow having sub locations"
                }, 400
        if not request_body.type.enable_parent_location and request_body.parent_location is not None:
            return {
                "message": "location type does not allow having a parent location"
            }, 400
        locations.update_location(
            location_id=path.location_id,
            name={'en': request_body.name},
            description={'en': request_body.description},
            parent_location_id=request_body.parent_location_id,
            user_id=flask.g.user.id,
            type_id=request_body.type.id,
            is_hidden=request_body.is_hidden,
            enable_object_assignments=request_body.enable_object_assignments
        )
        location = locations.get_location(path.location_id)
        return location_to_json(location), 200


class Locations(Resource):
    class RequestBodyModel(_ParentLocationMixin, BaseModel):
        name: str = Field(description="the name for the location to create", examples=["Example Location"])
        description: str = Field("", description="the description for the location to create", examples=["This is an example location"])
        parent_location_id: typing.Annotated[typing.Optional[int], Strict()] = Field(None, description="the ID of the parent location for the location to create", examples=[1])
        type_id: OptionalNotNone[typing.Annotated[int, Strict()]] = Field(None, description="the location type ID for the location to create", examples=[-99])

        @cached_property
        def type(self) -> typing.Optional[locations.LocationType]:
            return _get_location_type(self.type_id)

    @multi_auth.login_required
    @method()
    def get(self) -> ResponseData:
        """
        Get all locations.
        """
        return [
            location_to_json(location)
            for location in location_permissions.get_locations_with_user_permissions(
                user_id=flask.g.user.id,
                permissions=Permissions.READ
            )
        ]

    @multi_auth.login_required
    @method()
    def post(self, request_body: RequestBodyModel) -> ResponseData:
        """
        Create a new location.
        """
        if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask.g.user.is_admin:
            return {
                "message": "only administrators may manage locations"
            }, 403
        if parent_location := request_body.parent_location:
            if Permissions.WRITE not in location_permissions.get_user_location_permissions(parent_location.id, flask.g.user.id):
                return {
                    "message": "insufficient permissions for parent location"
                }, 403
            if not parent_location.type.enable_sub_locations:
                return {
                    "message": "parent location type does not allow having sub locations"
                }, 400
        if location_type := request_body.type:
            if location_type.admin_only and not flask.g.user.is_admin:
                return {
                    "message": "location type may only be used by administrators"
                }, 403
            if not location_type.enable_parent_location and request_body.parent_location is not None:
                return {
                    "message": "location type does not allow having a parent location"
                }, 400
        location = locations.create_location(
            name={'en': request_body.name},
            description={'en': request_body.description},
            parent_location_id=None if request_body.parent_location is None else request_body.parent_location.id,
            user_id=flask.g.user.id,
            type_id=locations.LocationType.LOCATION if request_body.type is None else request_body.type.id
        )
        return flask.redirect(
            flask.url_for('.location', location_id=location.id),
            201
        )


class LocationType(Resource):
    class PathModel(BaseModel):
        location_type_id: int = Field(description="the ID of an existing location type", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get a location type.
        """
        try:
            location_type = locations.get_location_type(location_type_id=path.location_type_id)
        except errors.LocationTypeDoesNotExistError:
            return {
                "message": f"location type {path.location_type_id} does not exist"
            }, 404
        return location_type_to_json(location_type)


class LocationTypes(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> ResponseData:
        """
        List all location types.
        """
        return [
            location_type_to_json(location_type)
            for location_type in locations.get_location_types()
        ]


class ObjectLocationAssignment(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])
        object_location_assignment_index: int = Field(description="the ID of an existing location assignment for this object", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        Get an object location assignment.
        """
        try:
            object_location_assignments = locations.get_object_location_assignments(object_id=path.object_id)
        except errors.ObjectDoesNotExistError:
            return {
                "message": f"object {path.object_id} does not exist"
            }, 404
        if path.object_location_assignment_index < 0 or path.object_location_assignment_index >= len(object_location_assignments):
            return {
                "message": f"location assignment {path.object_location_assignment_index} for object {path.object_id} does not exist"
            }, 404
        return object_location_assignment_to_json(object_location_assignments[path.object_location_assignment_index])


class ObjectLocationAssignments(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    class RequestBodyModel(BaseModel):
        object_id: OptionalNotNone[typing.Annotated[int, is_expected_from_validation_info(lambda i: i.context.object_id)]] = Field(description="the ID the object to assign to a user or location, must match the object_id path parameter", examples=[1])
        location_id: OptionalNotNone[typing.Annotated[int, Strict()]] = Field(description="the ID of the location for this object", examples=[1])
        responsible_user_id: OptionalNotNone[typing.Annotated[UserId, Strict()]] = Field(description="the ID of the responsible user for this object", examples=[1])
        description: str = Field("", description="the description for the object location assignment to create", examples=["The object is stored in shelf A"])

        @cached_property
        def location(self) -> typing.Optional[locations.Location]:
            return _get_location(self.location_id, "location_id")

        @model_validator(mode="after")
        def check_assigned_to_something(self) -> typing.Self:
            # accessing `self.location` also checks validity of location ID
            if self.location is None and self.responsible_user_id is None:
                raise PydanticCustomError("unassigned", "Object assignment should include a location or a responsible user")
            return self

    @dataclass(frozen=True, slots=True)
    class ValidationContext:
        object_id: int

        @classmethod
        def from_path(cls, path: ObjectLocationAssignments.PathModel) -> typing.Self:
            return cls(
                object_id=path.object_id
            )

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ResponseData:
        """
        List all object location assignments.
        """
        try:
            return [
                object_location_assignment_to_json(object_location_assignment)
                for object_location_assignment in locations.get_object_location_assignments(path.object_id)
            ]
        except errors.ObjectDoesNotExistError:
            return {
                "message": f"object {path.object_id} does not exist"
            }, 404

    @object_permissions_required(Permissions.WRITE)
    @method(request_body_context_builder=ValidationContext.from_path)
    def post(self, path: PathModel, request_body: RequestBodyModel) -> ResponseData:
        """
        Create a new object location assignment.
        """
        if location := request_body.location:
            if Permissions.READ not in location_permissions.get_user_location_permissions(location.id, flask.g.user.id):
                return {
                    "message": "no permissions for location"
                }, 403
            if not location.enable_object_assignments or not location.type.enable_object_assignments:
                return {
                    "message": "location does not allow object assignments"
                }, 400
        try:
            locations.assign_location_to_object(
                object_id=path.object_id,
                location_id=None if request_body.location is None else request_body.location.id,
                responsible_user_id=request_body.responsible_user_id,
                user_id=flask.g.user.id,
                description={'en': request_body.description}
            )
        except errors.ExceedingLocationCapacityError:
            return {
                "message": "capacity of location exceeded"
            }, 400
        object_location_assignment = locations.get_object_location_assignments(path.object_id)[-1]
        return flask.redirect(
            flask.url_for('.object_location_assignment', object_id=path.object_id, object_location_assignment_index=object_location_assignment.id),
            201
        )
