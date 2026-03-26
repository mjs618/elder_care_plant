"""add version management tables

Revision ID: 20260326_add_version_management
Revises: 20260326_fix_gender_enum
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20260326_add_version_management'
down_revision: Union[str, None] = '20260326_fix_gender_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'platform_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('major', sa.Integer(), nullable=False),
        sa.Column('minor', sa.Integer(), nullable=False),
        sa.Column('patch', sa.Integer(), nullable=False),
        sa.Column('pre_release', sa.String(50), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'RELEASED', 'DEPRECATED', 'RETIRED', name='versionstatus'), nullable=False),
        sa.Column('release_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('breaking_changes', sa.Text(), nullable=True),
        sa.Column('migration_guide', sa.Text(), nullable=True),
        sa.Column('is_lts', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('lts_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('min_database_version', sa.String(50), nullable=True),
        sa.Column('module_versions', postgresql.JSONB(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version'),
    )
    op.create_index('ix_platform_versions_status', 'platform_versions', ['status'])
    op.create_index('ix_platform_versions_version', 'platform_versions', ['version'])

    op.create_table(
        'version_changelogs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('change_type', sa.Enum('FEATURE', 'ENHANCEMENT', 'BUGFIX', 'SECURITY', 'BREAKING', 'DEPRECATION', name='changetype'), nullable=False),
        sa.Column('module_slug', sa.String(100), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('issue_id', sa.String(50), nullable=True),
        sa.Column('pull_request_id', sa.String(50), nullable=True),
        sa.Column('impact_level', sa.String(20), nullable=False, server_default='low'),
        sa.Column('affected_apis', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['platform_version_id'], ['platform_versions.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_version_changelogs_platform_version_id', 'version_changelogs', ['platform_version_id'])
    op.create_index('ix_version_changelogs_change_type', 'version_changelogs', ['change_type'])
    op.create_index('ix_version_changelogs_module_slug', 'version_changelogs', ['module_slug'])

    op.create_table(
        'module_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('module_slug', sa.String(100), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'RELEASED', 'DEPRECATED', 'RETIRED', name='versionstatus'), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('min_platform_version', sa.String(50), nullable=True),
        sa.Column('max_platform_version', sa.String(50), nullable=True),
        sa.Column('dependencies', postgresql.JSONB(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(), nullable=True),
        sa.Column('api_version', sa.String(20), nullable=True),
        sa.Column('database_migrations', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_module_versions_module_slug', 'module_versions', ['module_slug'])
    op.create_index('ix_module_versions_module_version', 'module_versions', ['module_slug', 'version'], unique=True)

    op.create_table(
        'version_compatibilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_version', sa.String(50), nullable=False),
        sa.Column('target_version', sa.String(50), nullable=False),
        sa.Column('compatibility_level', sa.Enum('FULL', 'PARTIAL', 'NONE', name='compatibilitylevel'), nullable=False),
        sa.Column('upgrade_path', postgresql.JSONB(), nullable=True),
        sa.Column('migration_steps', postgresql.JSONB(), nullable=True),
        sa.Column('estimated_downtime_minutes', sa.Integer(), nullable=True),
        sa.Column('data_migration_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rollback_supported', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_version_compatibilities_source_version', 'version_compatibilities', ['source_version'])
    op.create_index('ix_version_compatibilities_target_version', 'version_compatibilities', ['target_version'])
    op.create_index('ix_version_compat_source_target', 'version_compatibilities', ['source_version', 'target_version'], unique=True)

    op.create_table(
        'tenant_version_bindings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('module_versions', postgresql.JSONB(), nullable=True),
        sa.Column('upgrade_scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('upgrade_status', sa.String(20), nullable=True),
        sa.Column('last_upgrade_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('upgrade_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['platform_version_id'], ['platform_versions.id']),
    )
    op.create_index('ix_tenant_version_bindings_tenant_id', 'tenant_version_bindings', ['tenant_id'])
    op.create_index('ix_tenant_version_bindings_platform_version_id', 'tenant_version_bindings', ['platform_version_id'])

    op.create_table(
        'version_rollbacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('performed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('data_backup_location', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_version_id'], ['platform_versions.id']),
        sa.ForeignKeyConstraint(['to_version_id'], ['platform_versions.id']),
    )
    op.create_index('ix_version_rollbacks_tenant_id', 'version_rollbacks', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('version_rollbacks')
    op.drop_table('tenant_version_bindings')
    op.drop_table('version_compatibilities')
    op.drop_table('module_versions')
    op.drop_table('version_changelogs')
    op.drop_table('platform_versions')
    
    op.execute('DROP TYPE IF EXISTS versionstatus')
    op.execute('DROP TYPE IF EXISTS changetype')
    op.execute('DROP TYPE IF EXISTS compatibilitylevel')
