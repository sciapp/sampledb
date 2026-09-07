import json
import typing
from dataclasses import dataclass
from functools import cached_property

import flask
from pydantic import BaseModel, Strict, model_validator, Field
from pydantic_core import PydanticCustomError

from .authentication import multi_auth, object_permissions_required
from ..utils import Resource
from ...logic import errors, locations, location_permissions, utils
from ...models import Permissions
from .utils.validation import ModelWithDefaultsFromValidationInfo, OptionalNotNone, UserId, is_expected_from_validation_info, populate_missing_or_expect_from_validation_info
from .utils.responses import NotFoundErrorModel, ForbiddenErrorModel, BadRequestErrorModel, CreatedResponseModel
from .utils.openapi import method


@typing.overload
def _get_location(location_id: int, loc: str) -> locations.Location:
    pass


@typing.overload
def _get_location(location_id: None, loc: str) -> None:
    pass


def _get_location(location_id: int | None, loc: str) -> locations.Location | None:
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


def _get_location_type(type_id: int | None) -> locations.LocationType | None:
    if type_id is None:
        return None
    try:
        return locations.get_location_type(type_id)
    except errors.LocationTypeDoesNotExistError:
        raise PydanticCustomError("no_such_location_type", "Location type should exist (type_id)")


if typing.TYPE_CHECKING:
    class _BaseLocation(typing.Protocol):
        @property
        def parent_location_id(self) -> int | None:
            pass

        @property
        def type(self) -> typing.Any:
            pass
else:
    class _BaseLocation(BaseModel):
        pass


class _ParentLocationMixin(_BaseLocation):
    @cached_property
    def parent_location(self) -> locations.Location | None:
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


class LocationTypeModel(BaseModel):
    location_type_id: int = Field(description="the ID of the location type", examples=[1])
    name: str | None = Field(description="the name of the location type", examples=["Example Location Type"])

    @classmethod
    def from_location_type(cls, location_type: locations.LocationType) -> typing.Self:
        return cls(
            location_type_id=location_type.id,
            name=location_type.name.get('en', None) if location_type.name else None,
        )


class ObjectLocationAssignmentModel(BaseModel):
    object_id: int = Field(description="the ID of the object that is assigned to a location/responsible user", examples=[1])
    location_id: int | None = Field(description="the ID of the location the object is assigned to", examples=[1])
    responsible_user_id: int | None = Field(description="the ID of the responsible user the object is assigned to", examples=[1])
    user_id: int | None = Field(description="the ID of the user who assinged the object to a location/responsible user", examples=[1])
    description: str | None = Field(description="the description of the object location/responsible user assignment", examples=["The object is stored on the example shelf."])
    utc_datetime: str | None = Field(description="the datetime in UTC when the object was assignment was created, formatted as YYYY-MM-DD HH:MM:SS", examples=["2026-01-02 03:04:05"])

    @classmethod
    def from_object_location_assignment(cls, object_location_assignment: locations.ObjectLocationAssignment) -> typing.Self:
        return cls(
            object_id=object_location_assignment.object_id,
            location_id=object_location_assignment.location_id,
            responsible_user_id=object_location_assignment.responsible_user_id,
            user_id=object_location_assignment.user_id,
            description=utils.get_translated_text(object_location_assignment.description, 'en'),
            utc_datetime=object_location_assignment.utc_datetime.strftime('%Y-%m-%d %H:%M:%S') if object_location_assignment.utc_datetime is not None else None
        )


class LocationModel(BaseModel):
    location_id: int = Field(description="the ID of the location", examples=[1])
    name: str | None = Field(description="the name of the location", examples=["Example Location"])
    description: str | None = Field(description="the description of the location", examples=["This is an example location."])
    parent_location_id: int | None = Field(description="the ID of the parent location of the location", examples=[2])
    type_id: int | None = Field(description="the ID of the location type of the location", examples=[-99])
    is_hidden: bool = Field(description="whether the location is hidden from location lists", examples=[False])
    enable_object_assignments: bool = Field(description="whether objects may be assigned to the location", examples=[True])

    @classmethod
    def from_location(cls, location: locations.Location) -> typing.Self:
        return cls(
            location_id=location.id,
            name=utils.get_translated_text(location.name, 'en') if location.name else None,
            description=utils.get_translated_text(location.description, 'en') if location.description else None,
            parent_location_id=location.parent_location_id,
            type_id=location.type_id,
            is_hidden=location.is_hidden,
            enable_object_assignments=location.enable_object_assignments,
        )


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
        parent_location_id: typing.Annotated[int | None, Strict()] = Field(description="the ID of the parent location for the location to update", examples=[1])
        type_id: typing.Annotated[int, Strict()] = Field(description="the location type ID for the location to create", examples=[-99])
        is_hidden: bool = Field(description="whether the location should be set to hidden", examples=[False])
        enable_object_assignments: bool = Field(description="whether object assignments should be enabled for the location to update", examples=[True])

        @cached_property
        def type(self) -> locations.LocationType:
            return _get_location_type(self.type_id)

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> LocationModel | ForbiddenErrorModel | NotFoundErrorModel:
        """
        Get a location.
        """
        try:
            location = locations.get_location(location_id=path.location_id)
        except errors.LocationDoesNotExistError:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"location {path.location_id} does not exist"
            )
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
            return ForbiddenErrorModel(
                error="Forbidden",
                message="insufficient permissions for location"
            )
        return LocationModel.from_location(location)

    @multi_auth.login_required
    @method(request_body_context_builder=ValidationContext.from_path_model)
    def put(self, path: PathModel, request_body: RequestBodyModel) -> LocationModel | BadRequestErrorModel | ForbiddenErrorModel:
        """
        Update a location.
        """
        if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="only administrators may manage locations"
            )
        if Permissions.WRITE not in location_permissions.get_user_location_permissions(path.location_id, flask.g.user.id):
            return ForbiddenErrorModel(
                error="Forbidden",
                message="insufficient permissions for location"
            )
        if request_body.parent_location is not None:
            if Permissions.WRITE not in location_permissions.get_user_location_permissions(request_body.parent_location.id, flask.g.user.id):
                return ForbiddenErrorModel(
                    error="Forbidden",
                    message="insufficient permissions for parent location"
                )
            if not request_body.parent_location.type.enable_sub_locations:
                return BadRequestErrorModel(
                    error="Bad Request",
                    message="parent location type does not allow having sub locations"
                )
        if not request_body.type.enable_parent_location and request_body.parent_location is not None:
            return BadRequestErrorModel(
                error="Bad Request",
                message="location type does not allow having a parent location"
            )
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
        return LocationModel.from_location(location)


class Locations(Resource):
    class RequestBodyModel(_ParentLocationMixin, BaseModel):
        name: str = Field(description="the name for the location to create", examples=["Example Location"])
        description: str = Field("", description="the description for the location to create", examples=["This is an example location"])
        parent_location_id: typing.Annotated[int | None, Strict()] = Field(None, description="the ID of the parent location for the location to create", examples=[1])
        type_id: OptionalNotNone[typing.Annotated[int, Strict()]] = Field(None, description="the location type ID for the location to create", examples=[-99])

        @cached_property
        def type(self) -> locations.LocationType | None:
            return _get_location_type(self.type_id)

    @multi_auth.login_required
    @method()
    def get(self) -> list[LocationModel]:
        """
        Get all locations.
        """
        return [
            LocationModel.from_location(location)
            for location in location_permissions.get_locations_with_user_permissions(
                user_id=flask.g.user.id,
                permissions=Permissions.READ
            )
        ]

    @multi_auth.login_required
    @method()
    def post(self, request_body: RequestBodyModel) -> CreatedResponseModel | BadRequestErrorModel | ForbiddenErrorModel:
        """
        Create a new location.
        """
        if flask.current_app.config['ONLY_ADMINS_CAN_MANAGE_LOCATIONS'] and not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="only administrators may manage locations"
            )
        if parent_location := request_body.parent_location:
            if Permissions.WRITE not in location_permissions.get_user_location_permissions(parent_location.id, flask.g.user.id):
                return ForbiddenErrorModel(
                    error="Forbidden",
                    message="insufficient permissions for parent location"
                )
            if not parent_location.type.enable_sub_locations:
                return BadRequestErrorModel(
                    error="Bad Request",
                    message="parent location type does not allow having sub locations"
                )
        if location_type := request_body.type:
            if location_type.admin_only and not flask.g.user.is_admin:
                return ForbiddenErrorModel(
                    error="Forbidden",
                    message="location type may only be used by administrators"
                )
            if not location_type.enable_parent_location and request_body.parent_location is not None:
                return BadRequestErrorModel(
                    error="Bad Request",
                    message="location type does not allow having a parent location"
                )
        location = locations.create_location(
            name={'en': request_body.name},
            description={'en': request_body.description},
            parent_location_id=None if request_body.parent_location is None else request_body.parent_location.id,
            user_id=flask.g.user.id,
            type_id=locations.LocationType.LOCATION if request_body.type is None else request_body.type.id
        )
        return CreatedResponseModel(
            location=flask.url_for('.location', location_id=location.id)
        )


class LocationType(Resource):
    class PathModel(BaseModel):
        location_type_id: int = Field(description="the ID of an existing location type", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> LocationTypeModel | NotFoundErrorModel:
        """
        Get a location type.
        """
        try:
            location_type = locations.get_location_type(location_type_id=path.location_type_id)
        except errors.LocationTypeDoesNotExistError:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"location type {path.location_type_id} does not exist"
            )
        return LocationTypeModel.from_location_type(location_type)


class LocationTypes(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> list[LocationTypeModel]:
        """
        List all location types.
        """
        return [
            LocationTypeModel.from_location_type(location_type)
            for location_type in locations.get_location_types()
        ]


class ObjectLocationAssignment(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])
        object_location_assignment_index: int = Field(description="the ID of an existing location assignment for this object", examples=[1])

    @object_permissions_required(Permissions.READ)
    @method()
    def get(self, path: PathModel) -> ObjectLocationAssignmentModel | NotFoundErrorModel:
        """
        Get an object location assignment.
        """
        try:
            object_location_assignments = locations.get_object_location_assignments(object_id=path.object_id)
        except errors.ObjectDoesNotExistError:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"object {path.object_id} does not exist"
            )
        if path.object_location_assignment_index < 0 or path.object_location_assignment_index >= len(object_location_assignments):
            return NotFoundErrorModel(
                error="NotFound",
                message=f"location assignment {path.object_location_assignment_index} for object {path.object_id} does not exist"
            )
        return ObjectLocationAssignmentModel.from_object_location_assignment(object_location_assignments[path.object_location_assignment_index])


class ObjectLocationAssignments(Resource):
    class PathModel(BaseModel):
        object_id: int = Field(description="the ID of an existing object", examples=[1])

    class RequestBodyModel(BaseModel):
        object_id: OptionalNotNone[typing.Annotated[int, is_expected_from_validation_info(lambda i: i.context.object_id)]] = Field(description="the ID the object to assign to a user or location, must match the object_id path parameter", examples=[1])
        location_id: OptionalNotNone[typing.Annotated[int, Strict()]] = Field(description="the ID of the location for this object", examples=[1])
        responsible_user_id: OptionalNotNone[typing.Annotated[UserId, Strict()]] = Field(description="the ID of the responsible user for this object", examples=[1])
        description: str = Field("", description="the description for the object location assignment to create", examples=["The object is stored in shelf A"])

        @cached_property
        def location(self) -> locations.Location | None:
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
    def get(self, path: PathModel) -> list[ObjectLocationAssignmentModel] | NotFoundErrorModel:
        """
        List all object location assignments.
        """
        try:
            return [
                ObjectLocationAssignmentModel.from_object_location_assignment(object_location_assignment)
                for object_location_assignment in locations.get_object_location_assignments(path.object_id)
            ]
        except errors.ObjectDoesNotExistError:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"object {path.object_id} does not exist"
            )

    @object_permissions_required(Permissions.WRITE)
    @method(request_body_context_builder=ValidationContext.from_path)
    def post(self, path: PathModel, request_body: RequestBodyModel) -> CreatedResponseModel | BadRequestErrorModel | ForbiddenErrorModel:
        """
        Create a new object location assignment.
        """
        if location := request_body.location:
            if Permissions.READ not in location_permissions.get_user_location_permissions(location.id, flask.g.user.id):
                return ForbiddenErrorModel(
                    error="Forbidden",
                    message="no permissions for location"
                )
            if not location.enable_object_assignments or not location.type.enable_object_assignments:
                return BadRequestErrorModel(
                    error="Bad Request",
                    message="location does not allow object assignments"
                )
        try:
            locations.assign_location_to_object(
                object_id=path.object_id,
                location_id=None if request_body.location is None else request_body.location.id,
                responsible_user_id=request_body.responsible_user_id,
                user_id=flask.g.user.id,
                description={'en': request_body.description}
            )
        except errors.ExceedingLocationCapacityError:
            return BadRequestErrorModel(
                error="Bad Request",
                message="capacity of location exceeded"
            )
        object_location_assignment = locations.get_object_location_assignments(path.object_id)[-1]
        return CreatedResponseModel(
            location=flask.url_for(
                '.object_location_assignment',
                object_id=path.object_id,
                object_location_assignment_index=object_location_assignment.id
            )
        )
