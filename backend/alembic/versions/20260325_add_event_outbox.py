"""Add event outbox table

Revision ID: 20260325_add_event_outbox
Revises: 9980b63bbc4b
Create Date: 2026-03-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260325_add_event_outbox'
down_revision = '9980b63bbc4b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'event_outbox',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', sa.String(36), unique=True, nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('source_module', sa.String(50), nullable=False),
        sa.Column('payload', sa.Text, nullable=False),
        sa.Column('routing_key', sa.String(200), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'PUBLISHED', 'FAILED', name='outboxstatus'),
            nullable=False,
            default='PENDING'
        ),
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),
        sa.Column('max_retries', sa.Integer, nullable=False, default=5),
        sa.Column('last_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index('ix_event_outbox_event_id', 'event_outbox', ['event_id'])
    op.create_index('ix_event_outbox_event_type', 'event_outbox', ['event_type'])
    op.create_index('ix_event_outbox_status', 'event_outbox', ['status'])


def downgrade() -> None:
    op.drop_index('ix_event_outbox_status', 'event_outbox')
    op.drop_index('ix_event_outbox_event_type', 'event_outbox')
    op.drop_index('ix_event_outbox_event_id', 'event_outbox')
    op.drop_table('event_outbox')
    op.execute('DROP type if exists outboxstatus')
