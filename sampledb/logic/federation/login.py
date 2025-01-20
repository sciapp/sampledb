import datetime
import time
import typing
import hashlib


import flask
import flask_login
from saml2 import BINDING_HTTP_ARTIFACT, BINDING_SOAP, BINDING_HTTP_REDIRECT, response as saml_response, saml, time_util, element_to_extension_element, SAMLError
from saml2.assertion import _authn_context_class_ref, Policy
from saml2.authn_context import PASSWORDPROTECTEDTRANSPORT
from saml2.client import Saml2Client
from saml2.config import SPConfig, IdPConfig
from saml2.metadata import create_metadata_string
from saml2.saml import NAMEID_FORMAT_TRANSIENT, NAME_FORMAT_BASIC
from saml2.server import Server
from saml2.s_utils import factory, rndbytes, UnknownSystemEntity
from saml2.entity import create_artifact, ArtifactResponse
from saml2.samlp import response_from_string

from ..components import Component, get_component_by_uuid, set_component_fed_login_available
from .. import errors
from ...utils import FlaskResponseT
from ...models import SAMLArtifacts, SAMLMetadata, SAMLMetadataType
from ... import db

error_logging = {
    "version": 1,
    "loggers": {
        "saml2": {
            "level": "ERROR"
        }
    }
}


def get_idp_metadata(component: typing.Optional[Component] = None) -> typing.Any:
    config = get_pysaml_idp_config()
    return create_metadata_string(None, config=config, sign=False)


def get_sp_metadata(component: Component) -> typing.Any:
    config = get_pysaml_sp_config(component)
    return create_metadata_string(None, config=config, sign=False)


def get_pysaml_sp_config(component: Component) -> SPConfig:
    metadata = SAMLMetadata.query.filter_by(component_id=component.id, type=SAMLMetadataType.IDENTITY_PROVIDER_METADATA).first()
    conf = SPConfig()
    conf.load({
        "entityid": f"sp-{flask.current_app.config['FEDERATION_UUID']}",
        "description": flask.current_app.config['FEDERATION_UUID'],
        "delete_tmpfiles": True,
        "debug": 0,
        "logging": error_logging,
        "service": {
            "sp": {
                "want_response_signed": False,
                "want_assertions_signed": False,
                "want_assertions_or_response_signed": False,
                "allow_unsolicited": False,
                "want_authn_requests_signed": False,
                "endpoints": {
                    "assertion_consumer_service": [
                        (flask.url_for("frontend.assertion_consumer_service", _external=True), BINDING_HTTP_REDIRECT),
                        (flask.url_for("frontend.assertion_consumer_service", _external=True), BINDING_HTTP_ARTIFACT),
                        (flask.url_for("frontend.assertion_consumer_service", _external=True), BINDING_SOAP)
                    ],
                },
                "name_id_format": [NAMEID_FORMAT_TRANSIENT],
                "name_id_format_allow_create": True
            },
        },
        "metadata": {"inline": [metadata.metadata_xml] if metadata else []}
    })
    return conf


def get_pysaml_idp_config() -> IdPConfig:
    metadata = {"inline": [saml_metadata.metadata_xml for saml_metadata in SAMLMetadata.query.filter_by(type=SAMLMetadataType.SERVICE_PROVIDER_METADATA).all()]}

    config = IdPConfig()
    config.load({
        "entityid": f"idp-{flask.current_app.config['FEDERATION_UUID']}",
        "description": "SampleDB Federation IdP",
        "delete_tmpfiles": True,
        "debug": 0,
        "logging": error_logging,
        "service": {
            "idp": {
                "sign_assertion": False,
                "sign_response": False,
                "want_authn_requests_signed": False,
                "encrypt_assertion": False,
                "name": "SampleDB Federation IdP",
                "endpoints": {
                    "single_sign_on_service": [
                        (flask.url_for("frontend.federated_login_verify", _external=True), BINDING_HTTP_REDIRECT),
                    ],
                    "artifact_resolution_service": [
                        (flask.url_for("frontend.artifact_resolution_service", _external=True), BINDING_SOAP),
                    ]
                },
                "policy": {
                    "default": {
                        "lifetime": {"minutes": 30},
                        "attribute_restrictions": None,
                        "name_form": [NAME_FORMAT_BASIC],
                    }
                },
                "name_id_format": NAMEID_FORMAT_TRANSIENT
            }
        },
        "metadata": metadata,
    })
    return config


def sp_login(component: Component, shared_device: bool) -> flask.Response:
    config = get_pysaml_sp_config(component=component)
    sp = Saml2Client(config)

    relay_state = "shared_device" if shared_device else ""

    try:
        binding, destination = sp.pick_binding(
            "single_sign_on_service", [BINDING_HTTP_REDIRECT], "idpsso", entity_id=f"idp-{component.uuid}"
        )
    except UnknownSystemEntity:
        raise errors.InvalidSAMLRequestError()

    req_id, req = sp.create_authn_request(
        destination, sign=False
    )

    flask.session['saml_req_id'] = req_id
    flask.session['saml_sso_component'] = component.uuid
    flask.session['using_shared_device'] = shared_device

    http_args = sp.apply_binding(binding, str(req), destination, response=False, relay_state=relay_state)
    return flask.Response(response=http_args['data'], headers=http_args['headers'], status=http_args['status'])


def process_login(args: dict[str, str]) -> typing.Optional[FlaskResponseT]:
    if "SAMLRequest" not in args:
        raise errors.InvalidSAMLRequestError()
    msg = args["SAMLRequest"]
    if msg and " " in msg:
        msg = msg.replace(" ", "+")

    config = get_pysaml_idp_config()
    IDP = Server(config=config)

    try:
        authnRequest = IDP.parse_authn_request(msg, binding=BINDING_HTTP_REDIRECT)
    except saml_response.StatusError:
        raise errors.AuthnRequestParsingError()

    authnRequestMsg = authnRequest.message
    try:
        response_args = IDP.response_args(authnRequestMsg, bindings=[BINDING_HTTP_REDIRECT])
    except UnknownSystemEntity:
        return None
    except SAMLError:
        raise errors.InvalidSAMLRequestError()

    entityid = authnRequestMsg.issuer.text.strip()

    return _create_artifact_response(config, IDP, entityid, response_args)


def resolve_artifact(SAMLart: str) -> dict[str, typing.Any]:
    component = get_component_by_uuid(flask.session['saml_sso_component'])
    client = Saml2Client(get_pysaml_sp_config(component))
    message = client.artifact2message(SAMLart, "idpsso", sign=False)
    artifact_response = client.parse_artifact_resolve_response(message.text)

    if artifact_response.in_response_to != flask.session["saml_req_id"]:
        raise errors.MismatchedResponseToRequestError()

    identity = {
        attrib.friendly_name: attrib.attribute_value[0].text
        for attrib in artifact_response.assertion[0].attribute_statement[0].attribute
    }

    return identity


def generate_and_store_artifact(IDP: Server, authn_response: str, endpoint_index: int) -> typing.Any:
    """
    Corresponds to the saml2.entity.Entity.use_artifact method from PySAML2 module with the
    difference that the artifact is stored in the database.
    """
    message_handle = hashlib.sha1(str(authn_response).encode("utf-8"))
    message_handle.update(rndbytes())
    mhd = message_handle.digest()
    saml_art = create_artifact(IDP.config.entityid, mhd, endpoint_index)
    artifact = SAMLArtifacts(artifact=saml_art, message=authn_response)
    db.session.add(artifact)
    db.session.commit()
    return saml_art


def _create_artifact_response(config: dict[str, typing.Any], IDP: Server, ent_id: str, response_args: dict[str, typing.Any]) -> FlaskResponseT:
    del response_args['binding']
    response_args['release_policy'] = Policy(restrictions={"default": {"name_form": saml.NAME_FORMAT_BASIC}})

    identity = {
        "uid": flask_login.current_user.id,
        "email": flask_login.current_user.email,
    }

    response = IDP.create_authn_response(
        identity=identity,
        userid=flask_login.current_user.id,
        authn_statement=factory(
            saml.AuthnStatement,
            authn_instant=time_util.instant(time_stamp=int(time.time())),
            session_not_on_or_after=time_util.in_a_while(minutes=30),
            authn_context=_authn_context_class_ref(PASSWORDPROTECTEDTRANSPORT, None)
        ),
        encrypt_assertion=False,
        name_id=_generate_name_id(IDP.config.entityid, ent_id, str(identity['email'])),
        binding=BINDING_HTTP_REDIRECT,
        **response_args
    )

    artifact = generate_and_store_artifact(IDP, authn_response=str(response), endpoint_index=1)

    destination = IDP.pick_binding(
        "assertion_consumer_service", [BINDING_HTTP_ARTIFACT], "spsso", entity_id=ent_id
    )[1]

    response_result = IDP.apply_binding(BINDING_HTTP_ARTIFACT, artifact, destination=destination)
    artifact_url = response_result['url']
    return flask.redirect(artifact_url)


def eval_artifact_resolve(soap_request: bytes) -> dict[str, typing.Any]:
    config = get_pysaml_idp_config()
    IDP = Server(config=config)

    artifact_resolve_request = IDP.parse_artifact_resolve(soap_request)
    rinfo = IDP.response_args(artifact_resolve_request, bindings=[BINDING_SOAP])
    response = IDP._status_response(ArtifactResponse, artifact_resolve_request.issuer, None, sign=False, **rinfo)
    artifact_message = SAMLArtifacts.query.filter_by(artifact=artifact_resolve_request.artifact.text).first()

    if artifact_message is None:
        raise errors.UnavailableArtifactError()

    authn_response = response_from_string(artifact_message.message)
    response.extension_elements = [element_to_extension_element(authn_response)]

    result: dict[str, typing.Any] = IDP.apply_binding(binding=BINDING_SOAP, msg_str=str(response), response=True)
    return result


def delete_old_artifacts() -> None:
    SAMLArtifacts.query.filter(SAMLArtifacts.since <= datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)).delete()
    db.session.commit()


def _generate_name_id(idp_ent_id: int, sp_ent_id: str, text: str) -> saml.NameID:
    return saml.NameID(name_qualifier=idp_ent_id, sp_name_qualifier=sp_ent_id, format=saml.NAMEID_FORMAT_EMAILADDRESS, text=text)


def update_metadata(component: Component, updates: dict[str, typing.Any]) -> None:
    metadata_idp = SAMLMetadata.query.filter_by(component_id=component.id, type=SAMLMetadataType.IDENTITY_PROVIDER_METADATA).first()
    metadata_sp = SAMLMetadata.query.filter_by(component_id=component.id, type=SAMLMetadataType.SERVICE_PROVIDER_METADATA).first()

    if updates:
        if metadata_idp:
            metadata_idp.metadata_xml = updates['idp']
            metadata_idp.since = datetime.datetime.now(datetime.timezone.utc)
        else:
            metadata_idp = SAMLMetadata(component_id=component.id, metadata_xml=updates['idp'], type=SAMLMetadataType.IDENTITY_PROVIDER_METADATA)
            db.session.add(metadata_idp)

        if metadata_sp:
            metadata_sp.metadata_xml = updates['sp']
            metadata_sp.since = datetime.datetime.now(datetime.timezone.utc)
        else:
            metadata_sp = SAMLMetadata(component_id=component.id, metadata_xml=updates['sp'], type=SAMLMetadataType.SERVICE_PROVIDER_METADATA)
            db.session.add(metadata_sp)
        db.session.commit()
        set_component_fed_login_available(component.id, updates['enabled'])
    else:
        set_component_fed_login_available(component.id, False)


def check_component_locally_ready(component: Component) -> bool:
    return len(SAMLMetadata.query.filter_by(component_id=component.id).all()) == 2
