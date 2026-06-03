"""KMS envelope-encryption providers for the QUANTFLO credential vault.

Envelope encryption: the KMS issues a per-record Data Encryption Key (DEK). The
DEK encrypts the credential with AES-256-GCM; only the KMS-*wrapped* DEK is stored,
never the plaintext DEK. Two providers:

* :class:`AwsKmsProvider`  — real AWS KMS (boto3 ``generate_data_key`` / ``decrypt``).
* :class:`LocalKmsProvider` — **DEV EMULATOR**. Wraps DEKs with a locally-held AES-256
  master key. This is a **KNOWN PHASE-1 SHORTFALL**: master-key custody is on local
  disk, not an HSM/cloud KMS. Never use it for production secrets.
"""
from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from quantflo.core.config import Settings

LOCAL_KMS_ARN = "local-kms-emulator"
_DEK_BYTES = 32  # AES-256
_GCM_NONCE_BYTES = 12  # 96-bit nonce (GCM standard)
_DEK_AAD = b"quantflo-dek"


class KmsProvider(ABC):
    """Envelope-encryption KMS contract."""

    arn: str
    name: str

    @abstractmethod
    def generate_data_key(self) -> tuple[bytes, bytes]:
        """Return ``(plaintext_dek, wrapped_dek)``; the plaintext is used once, then dropped."""

    @abstractmethod
    def decrypt_data_key(self, wrapped_dek: bytes) -> bytes:
        """Return the plaintext DEK from its KMS-wrapped form."""


class AwsKmsProvider(KmsProvider):
    """Real AWS KMS envelope provider."""

    name = "aws"

    def __init__(self, key_arn: str, region: str) -> None:
        import boto3  # lazy: only imported on the AWS path

        if not key_arn:
            raise ValueError("AWS KMS requires QUANTFLO_KMS_KEY_ARN")
        self.arn = key_arn
        self._client = boto3.client("kms", region_name=region)

    def generate_data_key(self) -> tuple[bytes, bytes]:
        resp = self._client.generate_data_key(KeyId=self.arn, KeySpec="AES_256")
        return bytes(resp["Plaintext"]), bytes(resp["CiphertextBlob"])

    def decrypt_data_key(self, wrapped_dek: bytes) -> bytes:
        resp = self._client.decrypt(CiphertextBlob=wrapped_dek, KeyId=self.arn)
        return bytes(resp["Plaintext"])


class LocalKmsProvider(KmsProvider):
    """DEV EMULATOR — wraps DEKs with a local AES-256 master key. KNOWN SHORTFALL."""

    name = "local"
    arn = LOCAL_KMS_ARN

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) != _DEK_BYTES:
            raise ValueError("local KMS master key must be 32 bytes")
        self._aes = AESGCM(master_key)

    def generate_data_key(self) -> tuple[bytes, bytes]:
        dek = os.urandom(_DEK_BYTES)
        nonce = os.urandom(_GCM_NONCE_BYTES)
        wrapped = nonce + self._aes.encrypt(nonce, dek, _DEK_AAD)
        return dek, wrapped

    def decrypt_data_key(self, wrapped_dek: bytes) -> bytes:
        nonce, ciphertext = wrapped_dek[:_GCM_NONCE_BYTES], wrapped_dek[_GCM_NONCE_BYTES:]
        return self._aes.decrypt(nonce, ciphertext, _DEK_AAD)


def _load_local_master_key(settings: Settings) -> bytes:
    if settings.local_kms_master_key:
        return base64.b64decode(settings.local_kms_master_key)
    path = Path(".secrets") / "local_kms_master.key"
    if path.exists():
        return base64.b64decode(path.read_text().strip())
    path.parent.mkdir(parents=True, exist_ok=True)
    key = os.urandom(_DEK_BYTES)
    path.write_text(base64.b64encode(key).decode())
    return key


def get_kms_provider(settings: Settings) -> KmsProvider:
    """Select the KMS provider from settings (``aws`` -> real KMS, else local emulator)."""
    if settings.kms_provider == "aws":
        return AwsKmsProvider(settings.kms_key_arn or "", settings.aws_region)
    return LocalKmsProvider(_load_local_master_key(settings))
