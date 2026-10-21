import typing
from http import HTTPStatus

import flask
from pydantic import BaseModel, Field

from ...logic import errors, groups
from ..utils import Resource
from .authentication import multi_auth
from .utils.validation import UserId, generate_example, LanguageCode
from .utils.responses import CreatedResponseModel, NoContentModel, ErrorDetailsModel, PaginatedSequence, \
    PaginationQueryModel
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
    name: dict[LanguageCode, str] = Field(description="the name of the basic group", examples=[{"en": "Example Basic Group"}])
    description: dict[LanguageCode, str] = Field(description="the description of the basic group", examples=[{"en": "This is an example basic group."}])
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
    def get(self, query: PaginationQueryModel) -> PaginatedSequence[GroupModel]:
        """
        List all basic groups.
        """
        all_groups = groups.get_groups()
        return PaginatedSequence.apply_pagination(
            items=[
                GroupModel.from_group(group)
                for group in all_groups
            ],
            query=query,
            id_getter=lambda group: group.group_id,
        )


class GroupNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The requested basic group does not exist."


class OnlyAdminsMayManageGroupsModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.FORBIDDEN
    TITLE: typing.ClassVar[str] = "Only administrators may manage basic groups."


class UserAlreadyIsGroupMemberModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.BAD_REQUEST
    TITLE: typing.ClassVar[str] = "The user is already a member of this basic group."


class UserIsNoGroupMemberModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The user is not a member of this basic group."


class Group(Resource):
    class PathModel(BaseModel):
        group_id: int = Field(description="the ID of an existing basic group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> GroupModel | GroupNotFoundModel:
        """
        Get a basic group.
        """
        try:
            group = groups.get_group(group_id=path.group_id)
        except errors.GroupDoesNotExistError:
            return GroupNotFoundModel(
                detail=f"Basic group {path.group_id} does not exist"
            )
        return GroupModel.from_group(group)


class GroupMemberUsers(Resource):
    class PathModel(BaseModel):
        group_id: int = Field(description="the ID of an existing basic group", examples=[1])

    class RequestBodyModel(BaseModel):
        user_id: UserId = Field(description="the ID of an existing user to add to the basic group", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel, query: PaginationQueryModel) -> PaginatedSequence[UserRef] | OnlyAdminsMayManageGroupsModel | GroupNotFoundModel:
        """
        List all member users of a basic group.
        """
        if not flask.g.user.is_admin:
            return OnlyAdminsMayManageGroupsModel(
                detail=f"User #{flask.g.user.id} is no administrator, but only administrators may manage basic groups."
            )
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return GroupNotFoundModel(
                detail=f"Basic group #{path.group_id} does not exist."
            )
        return PaginatedSequence.apply_pagination(
            items=[
                UserRef.from_user_id(user_id)
                for user_id in sorted(group_member_ids)
            ],
            query=query,
            path=path,
            id_getter=lambda user_ref: user_ref.user_id,
        )

    @multi_auth.login_required
    @method()
    def post(self, path: PathModel, request_body: RequestBodyModel) -> CreatedResponseModel | UserAlreadyIsGroupMemberModel | OnlyAdminsMayManageGroupsModel | GroupNotFoundModel:
        """
        Add a user to a basic group.
        """
        if not flask.g.user.is_admin:
            return OnlyAdminsMayManageGroupsModel(
                detail=f"User #{flask.g.user.id} is no administrator, but only administrators may manage basic groups."
            )
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return GroupNotFoundModel(
                detail=f"Basic group #{path.group_id} does not exist."
            )
        user_id = request_body.user_id
        if user_id in group_member_ids:
            return UserAlreadyIsGroupMemberModel(
                detail=f"User #{request_body.user_id} is already a member of basic group #{path.group_id}.",
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
    def get(self, path: PathModel) -> UserRef | OnlyAdminsMayManageGroupsModel | GroupNotFoundModel | UserIsNoGroupMemberModel:
        """
        Get a member user of a basic group.
        """
        if not flask.g.user.is_admin:
            return OnlyAdminsMayManageGroupsModel(
                detail=f"User #{flask.g.user.id} is no administrator, but only administrators may manage basic groups."
            )
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return GroupNotFoundModel(
                detail=f"Basic group #{path.group_id} does not exist."
            )
        if path.user_id not in group_member_ids:
            return UserIsNoGroupMemberModel(
                detail=f"User #{path.user_id} is not a member of basic group #{path.group_id}."
            )
        return UserRef.from_user_id(path.user_id)

    @multi_auth.login_required
    @method()
    def delete(self, path: PathModel) -> NoContentModel | OnlyAdminsMayManageGroupsModel | GroupNotFoundModel | UserIsNoGroupMemberModel:
        """
        Remove a user from a basic group.
        """
        if not flask.g.user.is_admin:
            return OnlyAdminsMayManageGroupsModel(
                detail=f"User #{flask.g.user.id} is no administrator, but only administrators may manage basic groups."
            )
        try:
            group_member_ids = groups.get_group_member_ids(path.group_id)
        except errors.GroupDoesNotExistError:
            return GroupNotFoundModel(
                detail=f"Basic group #{path.group_id} does not exist."
            )
        if path.user_id not in group_member_ids:
            return UserIsNoGroupMemberModel(
                detail=f"User #{path.user_id} is not a member of basic group #{path.group_id}."
            )
        groups.remove_user_from_group(path.group_id, path.user_id)
        return NoContentModel()
