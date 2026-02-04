"""
Revision ID: 002_create_escalations_table
Revises: 001_create_users_table
Create Date: 2025-05-27 15:00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "002_create_escalations_table"
down_revision = "001_create_users_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "escalations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("ticket_id", sa.String, nullable=False, index=True),
        sa.Column("user_id", sa.String, nullable=True),
        sa.Column("agent_id", sa.String, nullable=True),
        sa.Column("category", sa.String, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("escalation_time", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table("escalations")
