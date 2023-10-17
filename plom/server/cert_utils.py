# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald

"""SSL and related utilities for the Plom Server"""

import datetime
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes

from plom.server import confdir


def build_self_signed_SSL_keys(dur: Path = confdir) -> None:
    """Make new self-signed key and cert files if they do not yet exist.

    This uses the ``cryptography`` module and follows
    `their tutorial <https://cryptography.io/en/latest/x509/tutorial>`_.
    That that this is only used for self-signed keys/certs, typically for
    development: none of this code is used when we have a proper
    externally-generated cert (e.g., by LetsEncrypt).

    Note the country code is hardcoded to CA.

    Args:
        dur (pathlib.Path): where to put the key and cert file.

    Rraises:
        FileExistsError: keys are already there.
    """
    key_file = Path(dur) / "plom-selfsigned.key"
    cert_file = Path(dur) / "plom-selfsigned.crt"
    if key_file.is_file() and cert_file.is_file():
        raise FileExistsError("SSL key and certificate already exist")

    # new private key, stored in file
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(key_file, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Various details about who we are.
    # For self-signed certificate, subject and issuer always the same
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "For Development"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        )
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())  # Sign our certificate with the new private key
    )

    # Write certificate to disk
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
