"""add_processed_events

Revision ID: 20260326_add_processed_events
Revises: 20260325_add_event_outbox
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa


revision = "20260326_add_processed_events"
down_revision = "20260325_add_event_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("idempotency_key", sa.String(length=255), primary_key=True),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_processed_events_event_id", "processed_events", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_processed_events_event_id", table_name="processed_events")
    op.drop_table("processed_events")
