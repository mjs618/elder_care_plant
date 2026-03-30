"""add pending upgrade fields to tenant version bindings

Revision ID: 20260330_add_pending_upgrade_fields
Revises: 20260326_refresh_tokens_rls
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260330_add_pending_upgrade_fields"
down_revision: Union[str, None] = "20260326_refresh_tokens_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant_version_bindings",
        sa.Column("pending_platform_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "tenant_version_bindings",
        sa.Column("pending_module_versions", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_tenant_version_bindings_pending_platform_version_id",
        "tenant_version_bindings",
        ["pending_platform_version_id"],
    )
    op.create_foreign_key(
        "fk_tenant_version_bindings_pending_platform_version_id",
        "tenant_version_bindings",
        "platform_versions",
        ["pending_platform_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tenant_version_bindings_pending_platform_version_id",
        "tenant_version_bindings",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_tenant_version_bindings_pending_platform_version_id",
        table_name="tenant_version_bindings",
    )
    op.drop_column("tenant_version_bindings", "pending_module_versions")
    op.drop_column("tenant_version_bindings", "pending_platform_version_id")
