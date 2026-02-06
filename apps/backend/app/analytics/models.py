"""SQLAlchemy models for LLM cost tracking persistence."""

import sqlalchemy as sa
from apps.backend.app.core.db import Base


class LLMUsageRecord(Base):
    __tablename__ = "llm_usage_records"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    timestamp = sa.Column(sa.Float, nullable=False, index=True)
    model = sa.Column(sa.String(128), nullable=False, index=True)
    provider = sa.Column(sa.String(64), nullable=False)
    prompt_tokens = sa.Column(sa.Integer, nullable=False)
    completion_tokens = sa.Column(sa.Integer, nullable=False)
    total_tokens = sa.Column(sa.Integer, nullable=False)
    estimated_cost_usd = sa.Column(sa.Float, nullable=False)
    request_type = sa.Column(sa.String(64), default="chat")
    tenant_id = sa.Column(sa.String(128), default="", index=True)
    agent_id = sa.Column(sa.String(128), default="")
    metadata_ = sa.Column("metadata", sa.JSON, nullable=True)
    created_at = sa.Column(
        sa.DateTime, server_default=sa.func.now(), nullable=False
    )


class LLMBudgetAlert(Base):
    __tablename__ = "llm_budget_alerts"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    timestamp = sa.Column(sa.Float, nullable=False)
    message = sa.Column(sa.Text, nullable=False)
    current_spend_usd = sa.Column(sa.Float, nullable=False)
    budget_usd = sa.Column(sa.Float, nullable=False)
    percentage = sa.Column(sa.Float, nullable=False)
    created_at = sa.Column(
        sa.DateTime, server_default=sa.func.now(), nullable=False
    )
