"""Vault tests: KMS envelope crypto round-trips + DB-backed credential round-trip."""
from __future__ import annotations

import os

import boto3
import pytest
from moto import mock_aws
from sqlalchemy import select

from quantflo.data.db import session_scope
from quantflo.data.models import BrokerCredential
from quantflo.vault.kms import AwsKmsProvider, LocalKmsProvider
from quantflo.vault.vault import SecureCredentialVault, VaultError
from tests.conftest import requires_db


def test_local_kms_dek_wrap_roundtrip() -> None:
    prov = LocalKmsProvider(os.urandom(32))
    dek, wrapped = prov.generate_data_key()
    assert len(dek) == 32
    assert wrapped != dek
    assert prov.decrypt_data_key(wrapped) == dek


@mock_aws
def test_aws_kms_dek_wrap_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    client = boto3.client("kms", region_name="us-east-1")
    key_id = client.create_key()["KeyMetadata"]["KeyId"]
    prov = AwsKmsProvider(key_id, "us-east-1")
    dek, wrapped = prov.generate_data_key()
    assert len(dek) == 32
    assert prov.decrypt_data_key(wrapped) == dek


@requires_db
async def test_vault_db_roundtrip(pools: None) -> None:
    vault = SecureCredentialVault()  # local KMS emulator (kms_provider=local)
    creds = {"api_key": "db-XXXX-secret", "account": "TRADO-123", "secret": "p@ss w0rd!"}

    rec_id = await vault.encrypt_credentials("tradovate", creds)
    assert rec_id > 0
    assert await vault.decrypt_credentials("tradovate") == creds

    # Stored ciphertext must NOT contain the plaintext, and no plaintext key is persisted.
    async with session_scope() as session:
        row = (
            await session.execute(
                select(BrokerCredential).where(BrokerCredential.broker_name == "tradovate")
            )
        ).scalar_one()
        assert b"db-XXXX-secret" not in row.encrypted_api_data
        assert b"p@ss w0rd!" not in row.encrypted_api_data
        assert row.kms_provider == "local"
        assert len(row.encryption_iv) == 12


@requires_db
async def test_vault_missing_broker_raises(pools: None) -> None:
    vault = SecureCredentialVault()
    with pytest.raises(VaultError):
        await vault.decrypt_credentials("nonexistent-broker")
