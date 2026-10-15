# PLAN-BE-15 — Security, RBAC & Blind Isolation

## Status: COMPLETE / ACCEPTED (100% Pass)

## Objective
Implement server-side authorization, secret management and blind custody boundaries.

## Scope
- Define and implement canonical server-side RBAC and fine-grained permissions matching `docs/baseline/19_PERMISSION_MATRIX.md`.
- Enforce strict object-level authorization (IDOR/BOLA prevention) across Analysis, History, Evidence, and Jev AI services.
- Provide comprehensive secret scanning utilities and automated repo auditing with guaranteed zero critical leaks.
- Implement blind custody barriers preventing DEFENSE_DETECTOR access to attack/poison manifests and hidden ground truth labels.
- Provide least-privilege SQL Server database roles and ensure write/delete immutability on audit logs and analysis results.

## Primary Files
- `backend/src/x_sentinel/security/policy.py`: Canonical `Permission` enum, `ROLE_PERMISSIONS` matrix, and authorization helpers.
- `backend/src/x_sentinel/security/auth.py`: `AuthUser` model with derived permissions, `require_permissions` dependency, and `assert_job_ownership` IDOR validator.
- `backend/src/x_sentinel/security/secrets.py`: Multi-pattern credential scanner, diagnostic redaction engine, and whitelisting.
- `backend/src/x_sentinel/security/blind_custody.py`: Blind custody enforcement, path traversal defense, DB schema isolation check, and safe context sanitizer.
- `backend/src/x_sentinel/security/audit.py`: Security audit event recorder with guaranteed masking for `dbo.audit_events`.
- `backend/src/x_sentinel/security/__init__.py`: Security module public exports.
- `backend/src/x_sentinel/database/repositories/analysis.py`: Added `user_id` filtering for history scoping.
- `backend/src/x_sentinel/services/history_service.py`: Added ownership and scope enforcement for `list_history` and `get_analysis_detail`.
- `backend/src/x_sentinel/services/evidence_service.py`: Added `assert_job_ownership` enforcement for `get_canonical_evidence`.
- `backend/src/x_sentinel/api/routes.py`: Passed authenticated `AuthUser` context to History and Evidence services.
- `database/schema/security_roles.sql`: T-SQL least-privilege roles (`xs_app_role`, `xs_readonly_role`, `xs_evaluation_role`, `xs_migration_role`, `xs_custody_admin_role`) and immutability `DENY UPDATE, DELETE` directives.
- `scripts/scan_secrets.py`: CLI automated secret scan utility.
- `backend/tests/test_be15_security_rbac_blind.py`: 29 comprehensive security tests covering RBAC, IDOR, secrets, blind custody, and DB roles.

## Acceptance Criteria Validation

1. **Negative Authorization (PASS)**:
   - Unauthenticated requests rejected with HTTP 401 (`XS_UNAUTHENTICATED`).
   - Forged or expired Bearer tokens rejected with HTTP 401.
   - Inactive user accounts rejected with HTTP 403 (`XS_FORBIDDEN`).
   - Role-based permission checks enforce strict matrix:
     - `OPERATOR` denied access to evidence and alert mutations.
     - `EVALUATOR` denied access to live analysis submission.
     - `OPERATOR` and `EVALUATOR` denied access to Jev AI workflows.
   - Forged headers (`X-Role`, `X-User-Id`) cannot escalate privileges.
   - Cross-user object access (IDOR/BOLA) on `/v1/analysis/{id}` and `/v1/analysis/{id}/evidence` blocked with HTTP 403.
   - History queries automatically scoped to authenticated owner for non-admin roles.

2. **Secret Scan (PASS)**:
   - Scanned entire repository codebase, configuration files, and tracking artifacts.
   - Automated scan verified 0 unwhitelisted production secrets.
   - Diagnostics and `/v1/config/status` endpoints verified leak-free with passwords and connection strings redacted.
   - Logs and error messages scrubbed via `redact_sensitive_text` and `redact_sensitive_dict`.

3. **Blind Manifest Access Denial (PASS)**:
   - Poisoning manifests (`data/poisoning_manifests/*`) and hidden ground-truth labels isolated behind `BlindCustodyGuard`.
   - Direct file access, directory traversal (`../`, `%2e%2e`, null bytes) rejected with `BlindCustodyViolationError`.
   - Ingestion payloads containing manifest or ground-truth injection tokens blocked from detector pipelines.
   - Process environment variables scrubbed of unredacted manifest secrets.
   - Application database schema confirmed free of hidden evaluation-only ground truth tables.
   - Jev AI Safe Context Builder (`BE-11`) verified to reject any poisoned/blind tokens.
   - Post-hoc threshold tuning explicitly forbidden during evaluation.

## Test Verification
- BE-15 Dedicated Suite: `29 passed in 5.24s` (`backend/tests/test_be15_security_rbac_blind.py`).
- Code Quality & Style: `ruff check` passed with zero errors across all modified files.
- Secret Scan CLI: `python scripts/scan_secrets.py --path .` completed with 0 findings (PASS).
- System Regression Suite: 413 unit, integration, and contract tests across BE-01 through BE-15 passing with zero regressions.

## Done Definition
No silent TBDs, no undocumented schema/API changes, all tests pass, and outputs are traceable to versioned config/code.
Ready for BE-16.
