import datetime
import shutil
import subprocess
from email import policy
from email.parser import BytesParser

import flask_mail
import pytest

import sampledb.logic.smime as smime
from sampledb.logic.smime import SMIMESigningMessageAdapter, validate_smime_configuration

cryptography = pytest.importorskip('cryptography')

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def _write_test_signing_material(tmp_path):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, 'SampleDB Test'),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS, 'sampledb@example.com'),
    ])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    certificate_path = tmp_path / 'certificate.pem'
    private_key_path = tmp_path / 'private-key.pem'
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    private_key_path.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    ))
    return certificate_path, private_key_path


def _write_test_signing_material_without_email_address(tmp_path):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, 'SampleDB Test'),
    ])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    certificate_path = tmp_path / 'certificate.pem'
    private_key_path = tmp_path / 'private-key.pem'
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    private_key_path.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    ))
    return certificate_path, private_key_path


def test_smime_signed_message(app, tmp_path):
    certificate_path, private_key_path = _write_test_signing_material(tmp_path)
    app.config['MAIL_SMIME_CERTIFICATE_FILE'] = str(certificate_path)
    app.config['MAIL_SMIME_PRIVATE_KEY_FILE'] = str(private_key_path)
    app.config['MAIL_SMIME_PRIVATE_KEY_PASSWORD'] = None
    app.config['MAIL_SMIME_EXTRA_CERTIFICATES_FILE'] = None

    message = SMIMESigningMessageAdapter(flask_mail.Message(
        subject='SampleDB Test',
        sender='sampledb@example.com',
        recipients=['recipient@example.com'],
        body='Plain text body',
        html='<p>HTML body</p>',
    ))

    signed_message_data = message.as_bytes()
    parsed_message = BytesParser(policy=policy.SMTP).parsebytes(signed_message_data)

    assert parsed_message['Subject'] == 'SampleDB Test'
    assert parsed_message['From'] == 'sampledb@example.com'
    assert parsed_message['To'] == 'recipient@example.com'
    assert parsed_message.get_content_type() == 'multipart/signed'
    assert parsed_message.get_param('protocol') == 'application/x-pkcs7-signature'
    assert parsed_message.get_param('micalg') == 'sha-256'

    content_part, signature_part = parsed_message.iter_parts()
    assert content_part.get_content_type() == 'multipart/mixed'
    assert signature_part.get_content_type() == 'application/x-pkcs7-signature'
    assert signature_part.get_filename() == 'smime.p7s'
    assert signature_part.get_payload(decode=True)

    openssl = shutil.which('openssl')
    if openssl is None:
        pytest.skip('OpenSSL is required for verifying S/MIME signatures')
    message_path = tmp_path / 'message.eml'
    verified_content_path = tmp_path / 'verified-content.eml'
    message_path.write_bytes(signed_message_data)
    subprocess.run(
        [
            openssl,
            'smime',
            '-verify',
            '-in', str(message_path),
            '-CAfile', str(certificate_path),
            '-out', str(verified_content_path),
        ],
        check=True
    )


def test_validate_smime_configuration_requires_certificate_email_address(app, tmp_path):
    certificate_path, private_key_path = _write_test_signing_material_without_email_address(tmp_path)
    app.config['MAIL_SMIME_CERTIFICATE_FILE'] = str(certificate_path)
    app.config['MAIL_SMIME_PRIVATE_KEY_FILE'] = str(private_key_path)
    app.config['MAIL_SMIME_PRIVATE_KEY_PASSWORD'] = None
    app.config['MAIL_SMIME_EXTRA_CERTIFICATES_FILE'] = None

    with pytest.raises(ValueError, match='does not contain an email address'):
        validate_smime_configuration(app.config)


def test_smime_signing_material_is_cached(app, monkeypatch):
    app.extensions.pop(smime.SMIME_SIGNING_MATERIAL_CACHE_KEY, None)
    app.config['MAIL_SMIME_CERTIFICATE_FILE'] = 'certificate.pem'
    app.config['MAIL_SMIME_PRIVATE_KEY_FILE'] = 'private-key.pem'
    app.config['MAIL_SMIME_PRIVATE_KEY_PASSWORD'] = None
    app.config['MAIL_SMIME_EXTRA_CERTIFICATES_FILE'] = None

    signing_material = object()
    load_calls = []

    def load_smime_signing_material(*args, **kwargs):
        load_calls.append((args, kwargs))
        return signing_material

    monkeypatch.setattr(smime, '_load_smime_signing_material', load_smime_signing_material)

    assert smime._get_smime_signing_material(app.config) is signing_material
    assert smime._get_smime_signing_material(app.config) is signing_material
    assert load_calls == [
        (
            (),
            {
                'certificate_path': 'certificate.pem',
                'private_key_path': 'private-key.pem',
                'private_key_password': None,
                'extra_certificates_path': None
            }
        )
    ]
