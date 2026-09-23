import typing
from http import HTTPStatus

from pydantic import BaseModel, Field

from .authentication import multi_auth
from ..utils import Resource
from ...logic.action_types import get_action_types, get_action_type
from ...logic import errors, utils, action_types
from .utils.responses import ErrorDetailsModel
from .utils.openapi import method


class ActionTypeModel(BaseModel):
    type_id: int = Field(description="the ID of the action type", examples=[1])
    name: str = Field(description="the name of the action type", examples=["Sample Creation"])
    object_name: str = Field(description="the name for objects created with actions of the action type", examples=["Sample"])
    admin_only: bool = Field(description="whether the action type may only be used by administrators", examples=[False])

    @classmethod
    def from_action_type(cls, action_type: action_types.ActionType) -> typing.Self:
        return cls(
            type_id=action_type.id,
            name=utils.get_translated_text(
                action_type.name,
                language_code='en',
                default='Unnamed Action Type'
            ),
            object_name=utils.get_translated_text(
                action_type.object_name,
                language_code='en',
                default='Object'
            ),
            admin_only=action_type.admin_only
        )


class ActionTypeNotFoundModel(ErrorDetailsModel):
    STATUS: typing.ClassVar[int] = HTTPStatus.NOT_FOUND
    TITLE: typing.ClassVar[str] = "The action type does not exist."


class ActionType(Resource):
    class PathModel(BaseModel):
        type_id: int = Field(description="the ID of an existing action type", examples=[1])

    @multi_auth.login_required
    @method()
    def get(self, path: PathModel) -> ActionTypeModel | ActionTypeNotFoundModel:
        """
        Get an action type.
        """
        try:
            action_type = get_action_type(
                action_type_id=path.type_id
            )
        except errors.ActionTypeDoesNotExistError:
            return ActionTypeNotFoundModel(
                detail=f"Action type #{path.type_id} does not exist."
            )
        return ActionTypeModel.from_action_type(action_type)


class ActionTypes(Resource):
    @multi_auth.login_required
    @method()
    def get(self) -> list[ActionTypeModel]:
        """
        List all action types.
        """
        action_types = get_action_types()
        return [
            ActionTypeModel.from_action_type(action_type)
            for action_type in action_types
        ]
