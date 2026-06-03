"""initial schema: instruments, bars (hypertable), ingestion_runs, data_quality_events, broker_credentials

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-03
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT = sa.text("'local'")
_NOW = sa.text("now()")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    op.create_table(
        "instruments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default=_TENANT, nullable=False),
        sa.Column("symbol", sa.String(16), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("exchange", sa.String(16), nullable=False),
        sa.Column("tick_size", sa.Numeric(20, 8), nullable=False),
        sa.Column("point_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(8), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("is_micro", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.UniqueConstraint("tenant_id", "symbol", name="uq_instruments_tenant_symbol"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default=_TENANT, nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=True),
        sa.Column("timeframe", sa.String(8), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), server_default=sa.text("'running'"), nullable=False),
        sa.Column("rows_ingested", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_rejected", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_ingestion_runs_status", "ingestion_runs", ["tenant_id", "status", "started_at"]
    )

    op.create_table(
        "bars",
        sa.Column("tenant_id", sa.String(64), server_default=_TENANT, nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("contract", sa.String(24), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("is_rth", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "instrument_id", "timeframe", "contract", "time"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="CASCADE"),
    )
    # TimescaleDB hypertable partitioned on `time` (PK includes `time`, as required).
    op.execute("SELECT create_hypertable('bars', 'time', if_not_exists => TRUE)")
    op.create_index("ix_bars_lookup", "bars", ["tenant_id", "instrument_id", "timeframe", "time"])

    op.create_table(
        "data_quality_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default=_TENANT, nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=True),
        sa.Column("ingestion_run_id", sa.BigInteger(), nullable=True),
        sa.Column("timeframe", sa.String(8), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), server_default=sa.text("'warning'"), nullable=False),
        sa.Column("bar_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detail", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_dqe_lookup",
        "data_quality_events",
        ["tenant_id", "instrument_id", "event_type", "created_at"],
    )

    op.create_table(
        "broker_credentials",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default=_TENANT, nullable=False),
        sa.Column("broker_name", sa.String(64), nullable=False),
        sa.Column("encrypted_api_data", sa.LargeBinary(), nullable=False),
        sa.Column("encryption_iv", sa.LargeBinary(), nullable=False),
        sa.Column("encrypted_dek", sa.LargeBinary(), nullable=False),
        sa.Column("kms_key_arn", sa.String(256), nullable=False),
        sa.Column("kms_provider", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.UniqueConstraint("tenant_id", "broker_name", name="uq_broker_credentials_tenant_broker"),
    )


def downgrade() -> None:
    # Reverse dependency order. drop_table cascades each table's indexes.
    op.drop_table("broker_credentials")
    op.drop_table("data_quality_events")
    op.drop_table("bars")
    op.drop_table("ingestion_runs")
    op.drop_table("instruments")
    # The timescaledb extension is intentionally left installed (shared infrastructure).
