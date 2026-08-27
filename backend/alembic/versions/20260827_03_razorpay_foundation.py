"""Razorpay source identification and webhook idempotency.

Revision ID: 20260827_03
Revises: 20260826_02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260827_03"
down_revision: str | Sequence[str] | None = "20260826_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("merchants", sa.Column("source", sa.String(30), nullable=False, server_default="demo"))
    op.create_index("ix_merchants_source", "merchants", ["source"])
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("external_event_id", sa.String(200), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("processing_status", sa.String(30), nullable=False),
    )
    op.create_index("uq_webhook_provider_event", "webhook_events", ["provider", "external_event_id"], unique=True)


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_index("ix_merchants_source", table_name="merchants")
    op.drop_column("merchants", "source")
