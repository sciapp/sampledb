import flask
import flask_login

from ..utils import Resource, ResponseData
from ...logic import errors
from ...logic.actions import check_action_exists
from ...logic.instruments import check_instrument_exists
from ...logic.favorites import add_favorite_action, remove_favorite_action, get_user_favorite_action_ids, add_favorite_instrument, remove_favorite_instrument, get_user_favorite_instrument_ids


class FavoriteAction(Resource):
    @flask_login.login_required
    def put(self, action_id: int) -> ResponseData:
        if flask_login.current_user.is_readonly:
            return {
                "message": "user is readonly"
            }, 403
        try:
            check_action_exists(action_id)
        except errors.ActionDoesNotExistError:
            return {
                "message": f"action {action_id} does not exist"
            }, 404
        is_favorite = action_id in get_user_favorite_action_ids(user_id=flask_login.current_user.id)
        if is_favorite:
            return {
                "message": f"action {action_id} is already a favorite"
            }, 409
        add_favorite_action(action_id=action_id, user_id=flask_login.current_user.id)
        return {
            "message": f"action {action_id} has been added to favorite actions"
        }, 200

    @flask_login.login_required
    def delete(self, action_id: int) -> ResponseData:
        if flask_login.current_user.is_readonly:
            return {
                "message": "user is readonly"
            }, 403
        try:
            check_action_exists(action_id)
        except errors.ActionDoesNotExistError:
            return {
                "message": f"action {action_id} does not exist"
            }, 404
        is_favorite = action_id in get_user_favorite_action_ids(user_id=flask_login.current_user.id)
        if not is_favorite:
            return {
                "message": f"action {action_id} is not a favorite"
            }, 404
        remove_favorite_action(action_id=action_id, user_id=flask_login.current_user.id)
        return {
            "message": f"action {action_id} has been removed from favorite actions"
        }, 200


class FavoriteInstrument(Resource):
    @flask_login.login_required
    def put(self, instrument_id: int) -> ResponseData:
        if flask_login.current_user.is_readonly:
            return {
                "message": "user is readonly"
            }, 403
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": "instruments are disabled"
            }, 404
        try:
            check_instrument_exists(instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        is_favorite = instrument_id in get_user_favorite_instrument_ids(user_id=flask_login.current_user.id)
        if is_favorite:
            return {
                "message": f"instrument {instrument_id} is already a favorite"
            }, 409
        add_favorite_instrument(instrument_id=instrument_id, user_id=flask_login.current_user.id)
        return {
            "message": f"instrument {instrument_id} has been added to favorite instruments"
        }, 200

    @flask_login.login_required
    def delete(self, instrument_id: int) -> ResponseData:
        if flask_login.current_user.is_readonly:
            return {
                "message": "user is readonly"
            }, 403
        if flask.current_app.config['DISABLE_INSTRUMENTS']:
            return {
                "message": "instruments are disabled"
            }, 404
        try:
            check_instrument_exists(instrument_id)
        except errors.InstrumentDoesNotExistError:
            return {
                "message": f"instrument {instrument_id} does not exist"
            }, 404
        is_favorite = instrument_id in get_user_favorite_instrument_ids(user_id=flask_login.current_user.id)
        if not is_favorite:
            return {
                "message": f"instrument {instrument_id} is not a favorite"
            }, 404
        remove_favorite_instrument(instrument_id=instrument_id, user_id=flask_login.current_user.id)
        return {
            "message": f"instrument {instrument_id} has been removed from favorite instruments"
        }, 200
