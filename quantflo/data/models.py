"""SQLAlchemy ORM models for the QUANTFLO data layer (Phase 1).

Single-tenant now (``tenant_id`` defaults to a single local owner) and
multi-tenant-ready: **every table carries ``tenant_id``**. No trading logic — these
are storage schemas for market data, data-quality events, ingestion runs, and the
encrypted credential vault. ``bars`` becomes a TimescaleDB hypertable (see the
initial migration); its primary key therefore includes the ``time`` column.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DEFAULT_TENANT = "local"
_TENANT_DEFAULT = text(f"'{DEFAULT_TENANT}'")


class Base(DeclarativeBase):
    """Declarative base for all QUANTFLO data-layer tables."""


class Instrument(Base):
    """A tradable CME/CBOT index-futures contract (reference data)."""

    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, server_default=_TENANT_DEFAULT)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False)
    tick_size: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    point_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, server_default=text("'USD'"))
    is_micro: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "symbol", name="uq_instruments_tenant_symbol"),
    )


class Bar(Base):
    """An OHLCV bar for one instrument/timeframe/contract at a point in time.

    TimescaleDB hypertable (partitioned on ``time``); the PK includes ``time`` as
    required by Timescale. ``contract`` holds the per-contract code (e.g. ``ESH5``)
    or ``CONT`` for a stitched continuous series.
    """

    __tablename__ = "bars"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True, server_default=_TENANT_DEFAULT)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    timeframe: Mapped[str] = mapped_column(String(8), primary_key=True)
    contract: Mapped[str] = mapped_column(String(24), primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    is_rth: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_bars_lookup", "tenant_id", "instrument_id", "timeframe", "time"),
    )


class IngestionRun(Base):
    """One market-data ingestion run (audit + idempotency anchor)."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, server_default=_TENANT_DEFAULT)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True
    )
    timeframe: Mapped[str | None] = mapped_column(String(8), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'running'"))
    rows_ingested: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    rows_rejected: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_ingestion_runs_status", "tenant_id", "status", "started_at"),
    )


class DataQualityEvent(Base):
    """A recorded data-quality finding (gap / duplicate / outlier / session)."""

    __tablename__ = "data_quality_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, server_default=_TENANT_DEFAULT)
    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True
    )
    ingestion_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="SET NULL"), nullable=True
    )
    timeframe: Mapped[str | None] = mapped_column(String(8), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'warning'"))
    bar_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_dqe_lookup", "tenant_id", "instrument_id", "event_type", "created_at"),
    )


class BrokerCredential(Base):
    """Encrypted broker credentials — KMS envelope encryption, NO plaintext stored."""

    __tablename__ = "broker_credentials"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, server_default=_TENANT_DEFAULT)
    broker_name: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_api_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encryption_iv: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    kms_key_arn: Mapped[str] = mapped_column(String(256), nullable=False)
    kms_provider: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "broker_name", name="uq_broker_credentials_tenant_broker"),
    )
