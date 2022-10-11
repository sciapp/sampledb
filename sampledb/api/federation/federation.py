# coding: utf-8
"""
RESTful API for SampleDB
"""

import datetime
import typing

import flask

from ..utils import Resource, ResponseData
from ...logic import errors
from ...logic.components import Component
from ...logic.shares import get_shares_for_component, ObjectShare
from ...logic.federation.action_types import shared_action_type_preprocessor
from ...logic.federation.actions import shared_action_preprocessor
from ...logic.federation.instruments import shared_instrument_preprocessor
from ...logic.federation.location_types import shared_location_type_preprocessor
from ...logic.federation.locations import shared_location_preprocessor
from ...logic.federation.objects import shared_object_preprocessor
from ...logic.federation.update import import_updates, PROTOCOL_VERSION_MAJOR, PROTOCOL_VERSION_MINOR
from ...logic.federation.users import shared_user_preprocessor
from ...api.federation.authentication import http_token_auth
from ...logic.users import get_user_aliases_for_component

preprocessors = {
    'actions': shared_action_preprocessor,
    'users': shared_user_preprocessor,
    'instruments': shared_instrument_preprocessor,
    'locations': shared_location_preprocessor,
    'location_types': shared_location_type_preprocessor,
    'action_types': shared_action_type_preprocessor
}


def _get_header(component: Component) -> typing.Dict[str, typing.Any]:
    return {
        'db_uuid': flask.current_app.config['FEDERATION_UUID'],
        'target_uuid': component.uuid,
        'protocol_version': {
            'major': PROTOCOL_VERSION_MAJOR,
            'minor': PROTOCOL_VERSION_MINOR
        },
        'sync_timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
    }


def _get_last_sync(args: typing.Dict[str, typing.Any]) -> typing.Optional[datetime.datetime]:
    if 'last_sync_timestamp' not in args.keys():
        return None
    try:
        return datetime.datetime.strptime(args['last_sync_timestamp'], '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        return None


def share_to_json(share: ObjectShare) -> typing.Dict[str, typing.Any]:
    return {
        'object_id': share.object_id,
        'policy': share.policy,
        'utc_datetime': share.utc_datetime.strftime('%Y-%m-%d %H:%M:%S.%f') if share.utc_datetime else None
    }


class UpdateHook(Resource):
    @http_token_auth.login_required
    def post(self) -> ResponseData:
        try:
            import_updates(flask.g.component)
        except errors.UnauthorizedRequestError:
            pass
        except errors.NoAuthenticationMethodError:
            pass
        except errors.InvalidDataExportError:
            pass
        except errors.MissingComponentAddressError:
            pass
        except errors.ComponentNotConfiguredForFederationError:
            pass
        except errors.RequestServerError:
            pass
        except ConnectionError:
            pass
        return None


class Objects(Resource):
    @http_token_auth.login_required
    def get(self) -> ResponseData:
        component = flask.g.component
        shares = get_shares_for_component(component.id)
        refs: typing.List[typing.Tuple[str, int]] = []
        markdown_images: typing.Dict[str, str] = {}
        ref_ids: typing.Dict[str, typing.List[int]] = {
            'actions': [],
            'users': [],
            'instruments': [],
            'locations': [],
            'location_types': [],
            'action_types': []
        }

        result_lists: typing.Dict[str, typing.List[typing.Any]] = {
            'actions': [],
            'users': [],
            'instruments': [],
            'locations': [],
            'location_types': [],
            'objects': [],
            'action_types': []
        }

        for share in shares:
            obj = shared_object_preprocessor(share.object_id, share.policy, refs, markdown_images)
            result_lists['objects'].append(obj)

        while len(refs) > 0:
            type, id = refs.pop()
            if type in ref_ids and id not in ref_ids[type]:
                processed = preprocessors[type](id, component, refs, markdown_images)
                if processed is not None:
                    result_lists[type].append(processed)
                ref_ids[type].append(id)

        return {
            'header': _get_header(component),
            'markdown_images': markdown_images,
            'actions': result_lists['actions'],
            'users': result_lists['users'],
            'instruments': result_lists['instruments'],
            'locations': result_lists['locations'],
            'location_types': result_lists['location_types'],
            'objects': result_lists['objects'],
            'action_types': result_lists['action_types']
        }


class Users(Resource):
    @http_token_auth.login_required
    def get(self) -> ResponseData:
        last_sync = _get_last_sync(flask.request.args)
        component = flask.g.component

        result_users = []
        shared_user_aliases = get_user_aliases_for_component(component.id, modified_since=last_sync)
        for alias in shared_user_aliases:
            result_users.append(
                {
                    'user_id': alias.user_id,
                    'component_uuid': flask.current_app.config['FEDERATION_UUID'],
                    'name': alias.name,
                    'email': alias.email,
                    'orcid': alias.orcid,
                    'affiliation': alias.affiliation,
                    'role': alias.role,
                    'extra_fields': alias.extra_fields
                }
            )
        return {
            'header': _get_header(component),
            'users': result_users
        }
