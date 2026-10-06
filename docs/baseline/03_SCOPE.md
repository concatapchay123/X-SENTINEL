# 03 — SCOPE & DELIVERY — V3

## Phase 1 / MVP detector

- user-supplied local datasets, with distributed `datasets/` folder empty;
- EMBER 2,381-vector canonical input;
- schema validation and versioned 3-view mapping;
- LightGBM + SHAP;
- M1–M5;
- fusion/D0/D1/decision;
- Microsoft SQL Server operational persistence;
- evidence/audit/history/alerts;
- FastAPI contracts;
- Streamlit operator frontend;
- test/CI/Docker foundation.

## V3 Jev AI collaboration

In scope as optional local capability:

- LM Studio OpenAI-compatible client;
- exact model identity configuration;
- allowlisted context builder/redaction;
- explain/triage/compare/report modes;
- AI run audit/feedback;
- frontend advisory panel;
- guardrail and outage tests.

Not part of the detector scientific formula or acceptance metrics.

## Phase 2

- raw PE/LIEF static parser after schema-equivalence gate;
- hardened quarantine/object storage;
- full auth/RBAC for network deployment;
- richer observability/performance controls.

## Future / optional

- React/Next.js frontend replacement behind same API;
- worker queue;
- model registry;
- governed document retrieval/RAG for project docs only;
- selected external integrations through separate ADRs.

## Out of scope

- malware execution/detonation;
- endpoint auto-remediation;
- Jev AI autonomous shell/tool execution;
- Jev AI changing detector thresholds/model/config;
- blind truth exposure to detector/Jev AI;
- cloud LLM fallback without approved ADR;
- claiming scientific performance before actual E0–E5 evidence.
