"""strategy registry: research_candidates, strategy_versions, strategy_metrics, pipeline_tasks

Revision ID: 0002_strategy_registry
Revises: 0001_initial_schema
Create Date: 2026-06-03
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_strategy_registry"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT = sa.text("'local'")
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "research_candidates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default=_TENANT, nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("license", sa.String(64), nullable=True),
        sa.Column("relevance_score", sa.Numeric(6, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("novelty_score", sa.Numeric(6, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("dedup_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), server_default=sa.text("'new'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.UniqueConstraint("tenant_id", "dedup_hash", name="uq_candidate_tenant_hash"),
    )

    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default=_TENANT, nullable=False),
        sa.Column("strategy_key", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("candidate_id", sa.BigInteger(), nullable=True),
        sa.Column("source_lineage", sa.Text(), nullable=True),
        sa.Column("license", sa.String(64), nullable=True),
        sa.Column("license_provenance", sa.String(32), server_default=sa.text("'original'"), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("clean_room_spec", sa.Text(), nullable=True),
        sa.Column("provenance_sha", sa.String(64), nullable=True),
        sa.Column("parameters", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(16), server_default=sa.text("'researched'"), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("champion_status", sa.String(16), server_default=sa.text("'none'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["research_candidates.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "tenant_id", "strategy_key", "version", name="uq_strategy_tenant_key_version"
        ),
    )
    op.create_index(
        "ix_strategy_status", "strategy_versions", ["tenant_id", "status", "champion_status"]
    )

    op.create_table(
        "strategy_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default=_TENANT, nullable=False),
        sa.Column("strategy_version_id", sa.BigInteger(), nullable=False),
        sa.Column("evaluation_type", sa.String(24), nullable=False),
        sa.Column("instrument", sa.String(16), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sharpe", sa.Numeric(20, 8), nullable=True),
        sa.Column("sortino", sa.Numeric(20, 8), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(20, 8), nullable=True),
        sa.Column("profit_factor", sa.Numeric(20, 8), nullable=True),
        sa.Column("win_rate", sa.Numeric(20, 8), nullable=True),
        sa.Column("avg_trade", sa.Numeric(20, 8), nullable=True),
        sa.Column("total_return", sa.Numeric(20, 8), nullable=True),
        sa.Column("trade_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("commission_paid", sa.Numeric(20, 8), nullable=True),
        sa.Column("detail", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_metric_lookup",
        "strategy_metrics",
        ["tenant_id", "strategy_version_id", "evaluation_type"],
    )

    op.create_table(
        "pipeline_tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(64), server_default=_TENANT, nullable=False),
        sa.Column("candidate_id", sa.BigInteger(), nullable=True),
        sa.Column("strategy_version_id", sa.BigInteger(), nullable=True),
        sa.Column("stage", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["research_candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_pipeline_tenant_idem"),
    )
    op.create_index("ix_pipeline_stage", "pipeline_tasks", ["tenant_id", "stage", "status"])


def downgrade() -> None:
    op.drop_table("pipeline_tasks")
    op.drop_table("strategy_metrics")
    op.drop_table("strategy_versions")
    op.drop_table("research_candidates")
