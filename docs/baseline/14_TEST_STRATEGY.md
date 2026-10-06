# 14 — TEST STRATEGY — V3

## Test pyramid

1. Unit: schema/views/M1–M5/fusion/audit/Jev guardrails/context builder.
2. Database: metadata/migration/up-down/drift/repository behavior.
3. Integration: vector pipeline and persistent result lifecycle.
4. API contract: core + Jev disabled/success/failure cases.
5. Frontend E2E: exact backend values, AI advisory separation, outage path.
6. Scientific: E0–E5 + blind evaluation.
7. Performance: detector P50/P95/P99 separately from Jev latency/concurrency.
8. Security: isolation, malformed input, auth/RBAC, prompt injection, local endpoint controls.
9. Reproducibility: detector repeatability and Jev run metadata/provenance.

## Jev AI acceptance tests

- AI disabled -> explicit disabled state; detector unaffected.
- LM Studio unavailable/timeout -> detector result remains accessible.
- forbidden context keys -> blocked before network call.
- non-local endpoint -> blocked under local-only policy.
- prompt-injection strings -> remain evidence, never policy/tool instructions.
- Jev output never updates canonical detector fields.
- model ID/prompt version/input digest/output digest recorded.
- frontend shows advisory label and model/run metadata.
- hallucinated authoritative verdict in mock response cannot change detector status.

## Scientific boundary

Jev helpfulness or explanation quality is evaluated separately and never counted as evidence for SC detector claims.
