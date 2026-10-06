# 12 — SECURITY SPEC — V3

## Trust boundaries

1. Untrusted vector/file input -> validator/parser.
2. Detection runtime -> no hidden manifest/ground truth.
3. Evaluation scorer -> truth only after frozen predictions.
4. Frontend/API -> authenticated/authorized when network deployment enabled.
5. Canonical evidence -> Jev context builder -> local LM Studio.
6. Sample-derived strings/import names -> untrusted prompt data, never instructions.

## Core controls

- Never execute uploaded binaries.
- Static-only raw PE parsing if Phase 2 enabled.
- Restrict payload/file sizes and validate schema.
- Prevent path traversal and arbitrary filesystem reads.
- Secrets only in environment/secret manager.
- CORS allowlist; network auth/RBAC before public exposure.
- Separate blind ground-truth custody.
- Non-root containers and dependency scanning.
- Least-privilege SQL Server logins/roles; encrypted backups in production.

## Jev AI controls

- Disabled by default.
- Local-host endpoint allowlist by default.
- No cloud fallback.
- Allowlist context projection.
- Reject keys representing blind labels, hidden manifests, raw PE, secrets or DB credentials.
- Prompt size/time/concurrency limits.
- No shell/process/tool execution.
- Jev cannot change model/config/threshold/decision.
- UI must label outputs as `AI advisory`.
- Store model/prompt/input/output digests for audit.
- Retain raw prompt/response only according to explicit policy.

## Prompt injection

All PE-derived strings, imports, exports and user-supplied text are hostile data. They are quoted/serialized under an already-established system policy. They cannot grant tools, alter guardrails, request secrets or redefine authority.

## Fail closed / fail independent

A Jev block/timeout/network error returns an AI-specific failure. The canonical detector result remains available and unchanged.
