import flask
from pydantic import BaseModel, Field

from ...logic import errors, groups
from ..utils import Resource
from .authentication import multi_auth
from .utils.validation import UserId, generate_example
from .utils.responses import NotFoundErrorModel, ForbiddenErrorModel, CreatedResponseModel, BadRequestErrorModel, NoContentModel
from .utils.openapi import method


class UserRef(BaseModel):
    user_id: int = Field(description="the ID of the referenced user", examples=[1])
    href: str = Field(description="the URL of the API endpoint for the referenced user", examples=["https://example.com/api/v2/users/1"])

    @classmethod
    def from_user_id(cls, user_id: int) -> UserRef:
        return cls(
            user_id=user_id,
            href=flask.url_for('.user', user_id=user_id, _external=True),
        )


class GroupModel(BaseModel):
    group_id: int = Field(description="the ID of the basic group", examples=[1])
    name: dict[str, str] = Field(description="the name of the basic group", examples=[{"en": "Example Basic Group"}])
    description: dict[str, str] = Field(description="the description of the basic group", examples=[{"en": "This is an example basic group."}])
    member_users: list[UserRef] = Field(description="the list of users who are members of the basic group", examples=[
        [generate_example(UserRef)]
    ])

    @classmethod
    def from_group(cls, group: groups.Group) -> GroupModel:
        return cls(
            group_id=group.id,
            name=group.name,
            description=group.description,
            member_users=[
                UserRef.from_user_id(user_id)
                for user_id in sorted(groups.get_group_member_ids(group_id=group.id))
            ]
        )


class Groups(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> list[GroupModel]:
        """
        List all basic groups.
        """
        return [
            GroupModel.from_group(group)
            for group in sorted(groups.get_groups(), key=lambda group: group.id)
        ]


class Group(Resource):
    class PathModel(BaseModel):
        group_id: int = Field(description="the ID of an existing basic group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> GroupModel | NotFoundErrorModel:
        """
        Get a basic group.
        """
        try:
            group = groups.get_group(group_id=path.group_id)
        except errors.GroupDoesNotExistError:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"group {path.group_id} does not exist"
            )
        return GroupModel.from_group(group)


class GroupMemberUsers(Resource):
    class PathModel(BaseModel):
        group_id: int = Field(description="the ID of an existing basic group", examples=[1])

    class RequestBodyModel(BaseModel):
        user_id: UserId = Field(description="the ID of an existing user to add to the basic group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> list[UserRef] | ForbiddenErrorModel | NotFoundErrorModel:
        """
        List all member users of a basic group.
        """
        if not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Only admins may manage groups"
            )
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return NotFoundErrorModel(
                error="NotFound",
                message=f"group {path.group_id} does not exist"
            )
        return [
            UserRef.from_user_id(user_id)
            for user_id in sorted(group_member_ids)
        ]

    @multi_auth.login_required
    @method()
    def post(self, path: PathModel, request_body: RequestBodyModel) -> CreatedResponseModel | BadRequestErrorModel | ForbiddenErrorModel | NotFoundErrorModel:
        """
        Add a user to a basic group.
        """
        if not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Only admins may manage groups"
            )
        if flask.g.user.is_readonly:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Read-only users may not manage groups"
            )
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"group {path.group_id} does not exist"
            )
        user_id = request_body.user_id
        if user_id in group_member_ids:
            return BadRequestErrorModel(
                error="Bad Request",
                message="user is already a member of this group"
            )
        groups.add_user_to_group(path.group_id, user_id)
        return CreatedResponseModel(
            location=flask.url_for(
                '.group_member_user',
                group_id=path.group_id,
                user_id=user_id)
        )


class GroupMemberUser(Resource):
    class PathModel(BaseModel):
        group_id: int = Field(description="the ID of an existing basic group", examples=[1])
        user_id: int = Field(description="the ID of an existing user", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> UserRef | ForbiddenErrorModel | NotFoundErrorModel:
        """
        Get a member user of a basic group.
        """
        if not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Only admins may manage groups"
            )
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"group {path.group_id} does not exist"
            )
        if path.user_id not in group_member_ids:
            return NotFoundErrorModel(
                error="Not Found",
                message="user is not a member of this group"
            )
        return UserRef.from_user_id(path.user_id)

    @multi_auth.login_required
    @method()
    def delete(self, path: PathModel) -> NoContentModel | ForbiddenErrorModel | NotFoundErrorModel:
        """
        Remove a user from a basic group.
        """
        if not flask.g.user.is_admin:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Only admins may manage groups"
            )
        if flask.g.user.is_readonly:
            return ForbiddenErrorModel(
                error="Forbidden",
                message="Read-only users may not manage groups"
            )
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return NotFoundErrorModel(
                error="Not Found",
                message=f"group {path.group_id} does not exist"
            )
        if path.user_id not in group_member_ids:
            return NotFoundErrorModel(
                error="Not Found",
                message="user is not a member of this group"
            )
        groups.remove_user_from_group(path.group_id, path.user_id)
        return NoContentModel()
