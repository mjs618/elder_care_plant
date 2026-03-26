"""add_rls_policies

Revision ID: 20260326_add_rls_policies
Revises: 20260326_add_processed_events
Create Date: 2026-03-26

Enables Row-Level Security (RLS) for multi-tenant data isolation.
All tenant-scoped tables will have RLS policies that enforce
data access only within the current tenant context.

"""
from alembic import op
import sqlalchemy as sa


revision = "20260326_add_rls_policies"
down_revision = "20260326_add_processed_events"
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "patients",
    "assessments",
]


def upgrade() -> None:
    conn = op.get_bind()
    
    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID AS $$
            SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::UUID;
        $$ LANGUAGE SQL STABLE;
    """))
    
    for table in TENANT_TABLES:
        conn.execute(sa.text(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
        """))
        
        conn.execute(sa.text(f"""
            DROP POLICY IF EXISTS tenant_isolation_policy ON {table};
        """))
        
        conn.execute(sa.text(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
                USING (tenant_id = current_tenant_id())
                WITH CHECK (tenant_id = current_tenant_id());
        """))
    
    conn.execute(sa.text("""
        ALTER TABLE tenant_modules ENABLE ROW LEVEL SECURITY;
    """))
    
    conn.execute(sa.text("""
        DROP POLICY IF EXISTS tenant_isolation_policy ON tenant_modules;
    """))
    
    conn.execute(sa.text("""
        CREATE POLICY tenant_isolation_policy ON tenant_modules
            USING (tenant_id = current_tenant_id())
            WITH CHECK (tenant_id = current_tenant_id());
    """))
    
    conn.execute(sa.text("""
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    """))
    
    conn.execute(sa.text("""
        DROP POLICY IF EXISTS tenant_isolation_policy ON users;
    """))
    
    conn.execute(sa.text("""
        DROP POLICY IF EXISTS platform_admin_policy ON users;
    """))
    
    conn.execute(sa.text("""
        CREATE POLICY tenant_isolation_policy ON users
            USING (tenant_id = current_tenant_id() OR tenant_id IS NULL);
    """))
    
    conn.execute(sa.text("""
        CREATE POLICY platform_admin_policy ON users
            USING (tenant_id IS NULL);
    """))
    
    conn.execute(sa.text("""
        ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
    """))
    
    conn.execute(sa.text("""
        DROP POLICY IF EXISTS tenant_isolation_policy ON roles;
    """))
    
    conn.execute(sa.text("""
        DROP POLICY IF EXISTS platform_admin_policy ON roles;
    """))
    
    conn.execute(sa.text("""
        CREATE POLICY tenant_isolation_policy ON roles
            USING (tenant_id = current_tenant_id() OR tenant_id IS NULL);
    """))
    
    conn.execute(sa.text("""
        CREATE POLICY platform_admin_policy ON roles
            USING (tenant_id IS NULL);
    """))
    
    conn.commit()


def downgrade() -> None:
    conn = op.get_bind()
    
    for table in TENANT_TABLES:
        conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};"))
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
    
    conn.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_policy ON tenant_modules;"))
    conn.execute(sa.text("ALTER TABLE tenant_modules DISABLE ROW LEVEL SECURITY;"))
    
    conn.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_policy ON users;"))
    conn.execute(sa.text("DROP POLICY IF EXISTS platform_admin_policy ON users;"))
    conn.execute(sa.text("ALTER TABLE users DISABLE ROW LEVEL SECURITY;"))
    
    conn.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_policy ON roles;"))
    conn.execute(sa.text("DROP POLICY IF EXISTS platform_admin_policy ON roles;"))
    conn.execute(sa.text("ALTER TABLE roles DISABLE ROW LEVEL SECURITY;"))
    
    conn.execute(sa.text("DROP FUNCTION IF EXISTS current_tenant_id();"))
    
    conn.commit()
