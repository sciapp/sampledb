import copy
import datetime
import typing
from email import policy
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

import flask
import flask_mail
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import ExtendedKeyUsageOID, ExtensionOID, NameOID

from ..config import SMIME_CONFIG_KEYS


SMIME_SIGNED_CONTENT_HEADERS = {
    'Content-Type',
    'Content-Transfer-Encoding',
    'Content-ID',
    'Content-Description',
    'Content-Disposition',
    'MIME-Version',
}
SMIME_SIGNING_MATERIAL_CACHE_KEY = 'sampledb.logic.smime.signing_material'

SMIMESigningMaterial = typing.Tuple[
    x509.Certificate,
    typing.Any,
    typing.List[x509.Certificate],
]


def _read_file(path: str) -> bytes:
    with open(path, 'rb') as file:
        return file.read()


def _load_smime_signing_material(
    certificate_path: str,
    private_key_path: str,
    private_key_password: typing.Optional[str],
    extra_certificates_path: typing.Optional[str] = None
) -> SMIMESigningMaterial:
    password = private_key_password.encode('utf-8') if private_key_password else None
    certificate = x509.load_pem_x509_certificate(_read_file(certificate_path))
    private_key = serialization.load_pem_private_key(_read_file(private_key_path), password=password)
    now = datetime.datetime.now(datetime.UTC)
    if certificate.not_valid_before_utc > now or certificate.not_valid_after_utc < now:
        raise ValueError('The S/MIME certificate is not currently valid.')
    certificate_public_key = certificate.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo
    )
    private_key_public_key = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo
    )
    if certificate_public_key != private_key_public_key:
        raise ValueError('The S/MIME certificate does not match the private key.')
    extra_certificates = []
    if extra_certificates_path:
        extra_certificates = x509.load_pem_x509_certificates(_read_file(extra_certificates_path))
    return certificate, private_key, extra_certificates


def _get_smime_signing_material(config: typing.Mapping[str, typing.Any]) -> SMIMESigningMaterial:
    if SMIME_SIGNING_MATERIAL_CACHE_KEY not in flask.current_app.extensions:
        flask.current_app.extensions[SMIME_SIGNING_MATERIAL_CACHE_KEY] = _load_smime_signing_material(
            certificate_path=config['MAIL_SMIME_CERTIFICATE_FILE'],
            private_key_path=config['MAIL_SMIME_PRIVATE_KEY_FILE'],
            private_key_password=config['MAIL_SMIME_PRIVATE_KEY_PASSWORD'],
            extra_certificates_path=config['MAIL_SMIME_EXTRA_CERTIFICATES_FILE']
        )
    return typing.cast(
        SMIMESigningMaterial,
        flask.current_app.extensions[SMIME_SIGNING_MATERIAL_CACHE_KEY]
    )


def _get_certificate_email_addresses(certificate: x509.Certificate) -> typing.Set[str]:
    email_addresses = {
        typing.cast(str, attribute.value).lower()
        for attribute in certificate.subject.get_attributes_for_oid(NameOID.EMAIL_ADDRESS)
    }
    try:
        subject_alternative_names = typing.cast(
            x509.SubjectAlternativeName,
            certificate.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
        )
        email_addresses.update(
            email_address.lower()
            for email_address in subject_alternative_names.get_values_for_type(x509.RFC822Name)
        )
    except x509.ExtensionNotFound:
        pass
    return email_addresses


def _validate_smime_certificate_usage(certificate: x509.Certificate, sender: str) -> None:
    sender_email_address = flask_mail.sanitize_address(sender).split('<')[-1].rstrip('>').lower()
    certificate_email_addresses = _get_certificate_email_addresses(certificate)
    if not certificate_email_addresses:
        raise ValueError('The S/MIME certificate does not contain an email address.')
    if sender_email_address not in certificate_email_addresses:
        raise ValueError(
            f'The S/MIME certificate is not valid for the configured sender address {sender_email_address!r}.'
        )
    try:
        key_usage = typing.cast(
            x509.KeyUsage,
            certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
        )
        if not key_usage.digital_signature:
            raise ValueError('The S/MIME certificate does not allow digital signatures.')
    except x509.ExtensionNotFound:
        pass
    try:
        extended_key_usage = typing.cast(
            x509.ExtendedKeyUsage,
            certificate.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
        )
        if ExtendedKeyUsageOID.EMAIL_PROTECTION not in extended_key_usage:
            raise ValueError('The S/MIME certificate does not allow email protection.')
    except x509.ExtensionNotFound:
        pass


def validate_smime_configuration(config: typing.Mapping[str, typing.Any]) -> None:
    if not smime_is_enabled(config):
        return
    certificate, _, _ = _load_smime_signing_material(
        certificate_path=config['MAIL_SMIME_CERTIFICATE_FILE'],
        private_key_path=config['MAIL_SMIME_PRIVATE_KEY_FILE'],
        private_key_password=config['MAIL_SMIME_PRIVATE_KEY_PASSWORD'],
        extra_certificates_path=config['MAIL_SMIME_EXTRA_CERTIFICATES_FILE']
    )
    _validate_smime_certificate_usage(certificate, config['MAIL_SENDER'])


def smime_is_enabled(config: typing.Mapping[str, typing.Any]) -> bool:
    return any(config.get(config_key) is not None for config_key in SMIME_CONFIG_KEYS)


def _get_first_signed_part_data(message_data: bytes, boundary: str) -> bytes:
    boundary_data = b'--' + boundary.encode('ascii')
    part_start = message_data.index(boundary_data) + len(boundary_data)
    if message_data[part_start:part_start + 2] == b'\r\n':
        part_start += 2
    elif message_data[part_start:part_start + 1] == b'\n':
        part_start += 1
    part_end = message_data.index(b'\r\n' + boundary_data, part_start)
    return message_data[part_start:part_end]


def _build_signature_part(signature: bytes) -> MIMEApplication:
    signature_part = MIMEApplication(
        signature,
        _subtype='x-pkcs7-signature',
        name='smime.p7s'
    )
    signature_part.set_param('smime-type', 'signed-data')
    signature_part.add_header('Content-Description', 'S/MIME Cryptographic Signature')
    signature_part.add_header('Content-Disposition', 'attachment', filename='smime.p7s')
    signature_part.replace_header('Content-Transfer-Encoding', 'base64')
    return signature_part


def sign_mime_message(message: MIMEBase) -> bytes:
    app_config = flask.current_app.config
    certificate, private_key, extra_certificates = _get_smime_signing_material(app_config)

    content = copy.deepcopy(message)
    signed_message = MIMEMultipart(
        'signed',
        protocol='application/x-pkcs7-signature',
        micalg='sha-256'
    )
    signed_message.preamble = 'This is an S/MIME signed message'
    for header, value in message.items():
        if header not in SMIME_SIGNED_CONTENT_HEADERS:
            signed_message[header] = value
            del content[header]

    content.policy = policy.SMTP
    signed_message.attach(content)
    signed_message.attach(_build_signature_part(b''))
    signed_message.policy = policy.SMTP
    signed_message_data = signed_message.as_bytes(policy=policy.SMTP)
    boundary = signed_message.get_boundary()
    if boundary is None:
        raise ValueError('The S/MIME multipart message does not have a boundary.')
    signed_data = _get_first_signed_part_data(
        signed_message_data,
        boundary
    )
    signature_builder = pkcs7.PKCS7SignatureBuilder().set_data(signed_data).add_signer(
        certificate,
        private_key,
        hashes.SHA256()
    )
    for extra_certificate in extra_certificates:
        signature_builder = signature_builder.add_certificate(extra_certificate)
    signature = signature_builder.sign(
        serialization.Encoding.DER,
        [
            pkcs7.PKCS7Options.DetachedSignature,
        ]
    )

    signed_message.set_payload([content, _build_signature_part(signature)])
    return signed_message.as_bytes(policy=policy.SMTP)


class SMIMESigningMessageAdapter(flask_mail.Message):
    def __init__(self, message: flask_mail.Message):
        super().__init__()
        self.__dict__.update(message.__dict__.copy())

    def as_string(self) -> str:
        return self.as_bytes().decode(self.charset or 'utf-8', errors='replace')

    def as_bytes(self) -> bytes:
        message = self._message()
        if smime_is_enabled(flask.current_app.config):
            return sign_mime_message(message)
        return message.as_bytes()


def prepare_mail(message: flask_mail.Message) -> flask_mail.Message:
    if smime_is_enabled(flask.current_app.config):
        return SMIMESigningMessageAdapter(message)
    return message
