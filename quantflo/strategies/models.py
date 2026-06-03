"""Strategy/model registry ORM models (Phase 2).

Versioned registry for researched/created/tested/validated strategies, their
evaluation metrics, the research candidates they came from, and the orchestration
pipeline tasks that move a candidate through Research -> Create -> Test. These
share the data-layer ``Base`` so a single Alembic metadata covers every table.
Every table carries ``tenant_id`` (single-tenant now, multi-tenant-ready). No
trading logic — this is registry/persistence only.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from quantflo.data.models import DEFAULT_TENANT, Base

_TENANT_DEFAULT = text(f"'{DEFAULT_TENANT}'")


class ResearchCandidate(Base):
    """A strategy/indicator idea discovered by Team 1 from a real source."""

    __tablename__ = "research_candidates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, server_default=_TENANT_DEFAULT)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)  # github | arxiv
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str | None] = mapped_column(String(64), nullable=True)
    relevance_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, server_default=text("0"))
    novelty_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, server_default=text("0"))
    dedup_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'new'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "dedup_hash", name="uq_candidate_tenant_hash"),
    )


class StrategyVersion(Base):
    """A versioned strategy in the registry, with provenance and lifecycle status."""

    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, server_default=_TENANT_DEFAULT)
    strategy_key: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_candidates.id", ondelete="SET NULL"), nullable=True
    )
    source_lineage: Mapped[str | None] = mapped_column(Text, nullable=True)
    license: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # original | permissive_attribution | clean_room
    license_provenance: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'original'")
    )
    attribution: Mapped[str | None] = mapped_column(Text, nullable=True)
    clean_room_spec: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)  # PASS@SHA
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # researched | created | tested | validated | rejected
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'researched'"))
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # none | challenger | champion
    champion_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'none'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "strategy_key", "version", name="uq_strategy_tenant_key_version"),
        Index("ix_strategy_status", "tenant_id", "status", "champion_status"),
    )


class StrategyMetric(Base):
    """A single evaluation result for a strategy version (real backtest numbers)."""

    __tablename__ = "strategy_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, server_default=_TENANT_DEFAULT)
    strategy_version_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_versions.id", ondelete="CASCADE"), nullable=False
    )
    # in_sample | out_of_sample | walk_forward | monte_carlo
    evaluation_type: Mapped[str] = mapped_column(String(24), nullable=False)
    instrument: Mapped[str | None] = mapped_column(String(16), nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sharpe: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    sortino: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    profit_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    avg_trade: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    total_return: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    commission_paid: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_metric_lookup", "tenant_id", "strategy_version_id", "evaluation_type"),
    )


class PipelineTask(Base):
    """An idempotent orchestration task moving a candidate through a pipeline stage."""

    __tablename__ = "pipeline_tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, server_default=_TENANT_DEFAULT)
    candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_candidates.id", ondelete="SET NULL"), nullable=True
    )
    strategy_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_versions.id", ondelete="SET NULL"), nullable=True
    )
    stage: Mapped[str] = mapped_column(String(16), nullable=False)  # research | create | test
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'pending'"))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_pipeline_tenant_idem"),
        Index("ix_pipeline_stage", "tenant_id", "stage", "status"),
    )
