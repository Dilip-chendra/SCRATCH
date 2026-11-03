-- ==============================================================================
-- SCRATCH — PostgreSQL Role Initialization & Security Bootstrap
-- Executed on fresh PostgreSQL cluster initialization.
-- ==============================================================================

-- 1. Create Migrator Role (Table Owner)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'scratch_migrator') THEN
        CREATE ROLE scratch_migrator WITH LOGIN PASSWORD 'migrator_local_secret_change_me';
    END IF;
END
$$;

-- 2. Create Application Runtime Role (Non-Superuser, Non-Owner, Strict RLS)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'scratch_app') THEN
        CREATE ROLE scratch_app WITH LOGIN PASSWORD 'app_local_secret_change_me' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;

-- 3. Grant Database-Level Permissions
GRANT CONNECT ON DATABASE scratch TO scratch_migrator;
GRANT CONNECT ON DATABASE scratch TO scratch_app;

-- 4. Schema-Level Permissions
GRANT USAGE, CREATE ON SCHEMA public TO scratch_migrator;
GRANT USAGE ON SCHEMA public TO scratch_app;

-- 5. Future Table Permissions:
-- When scratch_migrator creates tables in public schema via Alembic,
-- scratch_app automatically receives DML permissions (SELECT, INSERT, UPDATE, DELETE).
ALTER DEFAULT PRIVILEGES FOR ROLE scratch_migrator IN SCHEMA public 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO scratch_app;

ALTER DEFAULT PRIVILEGES FOR ROLE scratch_migrator IN SCHEMA public 
    GRANT USAGE, SELECT ON SEQUENCES TO scratch_app;
