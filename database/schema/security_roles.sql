-- ==============================================================================
-- X-SENTINEL V3 Canonical Database Security & Least-Privilege Architecture
-- Microsoft SQL Server (T-SQL) - Role-Based Security Enforcement (PLAN-BE-15)
-- ==============================================================================
-- Objective:
--   Implement defense-in-depth database permissions enforcing least privilege,
--   immutable audit trails, canonical detector result protection, and blind
--   manifest custody boundaries.
--
-- DO NOT grant db_owner or sysadmin to application runtime identities.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Create Dedicated Application Roles
-- ------------------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'xs_app_role' AND type = 'R')
BEGIN
    CREATE ROLE xs_app_role;
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'xs_readonly_role' AND type = 'R')
BEGIN
    CREATE ROLE xs_readonly_role;
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'xs_evaluation_role' AND type = 'R')
BEGIN
    CREATE ROLE xs_evaluation_role;
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'xs_migration_role' AND type = 'R')
BEGIN
    CREATE ROLE xs_migration_role;
END;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'xs_custody_admin_role' AND type = 'R')
BEGIN
    CREATE ROLE xs_custody_admin_role;
END;
GO

-- ------------------------------------------------------------------------------
-- 2. Configure Application Runtime Role (xs_app_role)
-- ------------------------------------------------------------------------------
-- Grants operational SELECT, INSERT, UPDATE needed for live API processing.
-- Explicitly DENIES UPDATE/DELETE on immutable audit and evidence tables.

GRANT SELECT, INSERT, UPDATE ON dbo.analysis_jobs TO xs_app_role;
GRANT SELECT, INSERT ON dbo.analysis_results TO xs_app_role;
GRANT SELECT, INSERT ON dbo.detector_scores TO xs_app_role;
GRANT SELECT, INSERT, UPDATE ON dbo.alerts TO xs_app_role;
GRANT SELECT, INSERT ON dbo.artifacts TO xs_app_role;
GRANT SELECT, INSERT ON dbo.audit_events TO xs_app_role;
GRANT SELECT, INSERT, UPDATE ON dbo.users TO xs_app_role;
GRANT SELECT ON dbo.roles TO xs_app_role;
GRANT SELECT ON dbo.user_roles TO xs_app_role;
GRANT SELECT ON dbo.model_versions TO xs_app_role;
GRANT SELECT, INSERT, UPDATE ON dbo.experiment_runs TO xs_app_role;
GRANT SELECT, INSERT, UPDATE ON dbo.jev_ai_runs TO xs_app_role;
GRANT SELECT, INSERT ON dbo.jev_ai_feedback TO xs_app_role;

-- IMMUTABILITY ENFORCEMENT:
-- Application runtime can never tamper with or delete audit events or canonical results
DENY UPDATE, DELETE ON dbo.audit_events TO xs_app_role;
DENY UPDATE, DELETE ON dbo.analysis_results TO xs_app_role;
DENY DELETE ON dbo.detector_scores TO xs_app_role;
DENY DELETE ON dbo.artifacts TO xs_app_role;
DENY DELETE ON dbo.jev_ai_runs TO xs_app_role;
DENY UPDATE, DELETE ON dbo.jev_ai_feedback TO xs_app_role;

-- ------------------------------------------------------------------------------
-- 3. Configure Read-Only / Auditor Role (xs_readonly_role)
-- ------------------------------------------------------------------------------
GRANT SELECT ON SCHEMA::dbo TO xs_readonly_role;
DENY INSERT, UPDATE, DELETE ON SCHEMA::dbo TO xs_readonly_role;

-- ------------------------------------------------------------------------------
-- 4. Configure Evaluation Scoring Role (xs_evaluation_role)
-- ------------------------------------------------------------------------------
GRANT SELECT ON dbo.analysis_jobs TO xs_evaluation_role;
GRANT SELECT ON dbo.analysis_results TO xs_evaluation_role;
GRANT SELECT ON dbo.detector_scores TO xs_evaluation_role;
GRANT SELECT, INSERT, UPDATE ON dbo.experiment_runs TO xs_evaluation_role;
DENY INSERT, UPDATE, DELETE ON dbo.analysis_results TO xs_evaluation_role;
DENY INSERT, UPDATE, DELETE ON dbo.detector_scores TO xs_evaluation_role;

-- ------------------------------------------------------------------------------
-- 5. Configure Migration Role (xs_migration_role)
-- ------------------------------------------------------------------------------
-- Alembic migration runner requires DDL permissions on dbo schema
GRANT ALTER, CREATE TABLE, REFERENCES ON SCHEMA::dbo TO xs_migration_role;

-- ------------------------------------------------------------------------------
-- 6. Research Blind Custody Schema Boundary (Defense-in-Depth)
-- ------------------------------------------------------------------------------
-- Invariant: Application schema contains ZERO blind ground-truth tables.
-- If research custody tables exist in database, they MUST reside in schema [custody].

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'custody')
BEGIN
    EXEC('CREATE SCHEMA custody AUTHORIZATION xs_custody_admin_role;');
END;
GO

-- Block application runtime and defense from custody schema
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::custody TO xs_app_role;
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::custody TO xs_readonly_role;
GO
