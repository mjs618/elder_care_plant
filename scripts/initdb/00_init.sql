-- PostgreSQL initialization scripts
-- Runs automatically on first container start via docker-entrypoint-initdb.d

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgvector";     -- AI vector storage (requires pgvector image)
-- CREATE EXTENSION IF NOT EXISTS "postgis";   -- Uncomment when ENABLE_POSTGIS=true

-- ── Row Level Security Setup ──────────────────────────────────────────────
-- After tables are created by Alembic, RLS policies will be applied.
-- The application sets: SET app.current_tenant_id = '<uuid>';
-- All tenant-scoped tables should then have:
--
--   ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
--   CREATE POLICY tenant_isolation ON <table>
--     USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
--
-- This is handled by the Alembic migration that creates each business table.

COMMENT ON DATABASE elder_care IS 'Elder Care Platform - Commercial SaaS Database';
