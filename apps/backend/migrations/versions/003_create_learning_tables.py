"""
Revision ID: 003_create_learning_tables
Revises: 002_create_escalations_table
Create Date: 2026-02-06 15:30:00

Creates tables for the continuous learning system:
- golden_paths: Proven resolution patterns from HITL feedback
- activity_events: Activity stream events (Redis fallback persistence)
- playbooks: Extracted playbooks from resolution patterns
- playbook_steps: Individual steps within a playbook
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "003_create_learning_tables"
down_revision = "002_create_escalations_table"
branch_labels = None
depends_on = None


def upgrade():
    # Golden paths — successful resolutions stored from HITL feedback
    op.create_table(
        "golden_paths",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("fingerprint", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("input_query", sa.Text, nullable=False),
        sa.Column("response", sa.Text, nullable=False),
        sa.Column("agent_blueprint", sa.String(128), nullable=True),
        sa.Column("tenant_id", sa.String(128), nullable=True, index=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("success_count", sa.Integer, server_default="1", nullable=False),
        sa.Column("failure_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("csat_score", sa.Float, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Activity events — persisted from Redis Streams for durability
    op.create_table(
        "activity_events",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("stream_id", sa.String(128), nullable=True, index=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(128), nullable=True, index=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("data", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_activity_events_type_tenant", "activity_events", ["event_type", "tenant_id"]
    )

    # Playbooks — extracted resolution patterns
    op.create_table(
        "playbooks",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(128), nullable=True, index=True),
        sa.Column("tenant_id", sa.String(128), nullable=True, index=True),
        sa.Column("trigger_pattern", sa.Text, nullable=True),
        sa.Column("success_rate", sa.Float, nullable=True),
        sa.Column("sample_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Playbook steps — ordered steps within a playbook
    op.create_table(
        "playbook_steps",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column(
            "playbook_id",
            sa.Integer,
            sa.ForeignKey("playbooks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("action_config", sa.JSON, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("timeout_seconds", sa.Integer, nullable=True),
        sa.Column("fallback_action", sa.String(64), nullable=True),
    )
    op.create_index("ix_playbook_steps_order", "playbook_steps", ["playbook_id", "step_order"])


def downgrade():
    op.drop_table("playbook_steps")
    op.drop_table("playbooks")
    op.drop_table("activity_events")
    op.drop_table("golden_paths")
