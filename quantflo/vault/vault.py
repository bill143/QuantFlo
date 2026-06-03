"""SecureCredentialVault — KMS-envelope-encrypted broker credentials.

NO plaintext credential or DEK is ever persisted: the credential JSON is encrypted
with a per-record DEK (AES-256-GCM); only the KMS-wrapped DEK, the ciphertext, and
the IV are stored. Errors are wrapped in :class:`VaultError` with NO key material in
the message and the original (possibly sensitive) traceback suppressed.
"""
from __future__ import annotations

import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select

from quantflo.core.config import Settings, get_settings
from quantflo.data.db import session_scope
from quantflo.data.models import BrokerCredential
from quantflo.vault.kms import KmsProvider, get_kms_provider

_GCM_NONCE_BYTES = 12
_AAD = b"quantflo-broker-credential"


class VaultError(Exception):
    """Credential-vault failure (never contains key material)."""


class SecureCredentialVault:
    """Encrypt/store/decrypt broker credentials behind a KMS envelope."""

    def __init__(self, settings: Settings | None = None, kms: KmsProvider | None = None) -> None:
        self._settings = settings or get_settings()
        self._kms = kms or get_kms_provider(self._settings)
        self._tenant = self._settings.tenant_id

    @property
    def kms_provider_name(self) -> str:
        return self._kms.name

    async def encrypt_credentials(self, broker_name: str, api_data: dict[str, str]) -> int:
        """Encrypt ``api_data`` and upsert it for ``broker_name``; returns the record id."""
        try:
            plaintext = json.dumps(api_data, separators=(",", ":")).encode()
            dek, wrapped_dek = self._kms.generate_data_key()
            iv = os.urandom(_GCM_NONCE_BYTES)
            ciphertext = AESGCM(dek).encrypt(iv, plaintext, _AAD)
        except Exception:
            raise VaultError("failed to encrypt credentials") from None

        async with session_scope() as session:
            stmt = select(BrokerCredential).where(
                BrokerCredential.tenant_id == self._tenant,
                BrokerCredential.broker_name == broker_name,
            )
            record = (await session.execute(stmt)).scalar_one_or_none()
            if record is None:
                record = BrokerCredential(tenant_id=self._tenant, broker_name=broker_name)
                session.add(record)
            record.encrypted_api_data = ciphertext
            record.encryption_iv = iv
            record.encrypted_dek = wrapped_dek
            record.kms_key_arn = self._kms.arn
            record.kms_provider = self._kms.name
            await session.flush()
            return record.id

    async def decrypt_credentials(self, broker_name: str) -> dict[str, str]:
        """Load and decrypt the credentials for ``broker_name``."""
        async with session_scope() as session:
            stmt = select(BrokerCredential).where(
                BrokerCredential.tenant_id == self._tenant,
                BrokerCredential.broker_name == broker_name,
            )
            record = (await session.execute(stmt)).scalar_one_or_none()

        if record is None:
            raise VaultError(f"no credentials stored for broker '{broker_name}'")
        try:
            dek = self._kms.decrypt_data_key(record.encrypted_dek)
            plaintext = AESGCM(dek).decrypt(record.encryption_iv, record.encrypted_api_data, _AAD)
            data: object = json.loads(plaintext)
        except Exception:
            raise VaultError("failed to decrypt credentials") from None
        if not isinstance(data, dict):
            raise VaultError("decrypted credential payload is malformed")
        return {str(k): str(v) for k, v in data.items()}
