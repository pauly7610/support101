"""Create LLM cost tracking tables

Revision ID: 004_create_cost_tracking
Revises: 003_create_learning_tables
Create Date: 2026-02-06 17:00:00

Creates tables for LLM cost tracking persistence:
- llm_usage_records: Individual LLM API call records with token counts and costs
- llm_budget_alerts: Budget threshold alerts
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004_create_cost_tracking"
down_revision = "003_create_learning_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "llm_usage_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("timestamp", sa.Float, nullable=False, index=True),
        sa.Column("model", sa.String(128), nullable=False, index=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=False),
        sa.Column("completion_tokens", sa.Integer, nullable=False),
        sa.Column("total_tokens", sa.Integer, nullable=False),
        sa.Column("estimated_cost_usd", sa.Float, nullable=False),
        sa.Column("request_type", sa.String(64), server_default="chat"),
        sa.Column("tenant_id", sa.String(128), server_default="", index=True),
        sa.Column("agent_id", sa.String(128), server_default=""),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_llm_usage_records_model_tenant",
        "llm_usage_records",
        ["model", "tenant_id"],
    )
    op.create_index(
        "ix_llm_usage_records_timestamp_tenant",
        "llm_usage_records",
        ["timestamp", "tenant_id"],
    )

    op.create_table(
        "llm_budget_alerts",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("timestamp", sa.Float, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("current_spend_usd", sa.Float, nullable=False),
        sa.Column("budget_usd", sa.Float, nullable=False),
        sa.Column("percentage", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("llm_budget_alerts")
    op.drop_table("llm_usage_records")
