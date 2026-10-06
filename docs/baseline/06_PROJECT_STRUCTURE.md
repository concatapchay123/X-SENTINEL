# 06 — PROJECT STRUCTURE — V3

```text
X_SENTINEL_V3/
├── backend/
│   └── src/x_sentinel/
│       ├── api/
│       ├── audit/
│       ├── data/
│       ├── database/
│       ├── detection/
│       ├── evaluation/
│       ├── fusion/
│       ├── jev_ai/          # optional local collaborator
│       ├── model/
│       ├── security/
│       └── services/
├── database/
│   ├── migrations/
│   ├── schema/
│   └── scripts/
├── frontend/
├── configs/
├── datasets/                # EMPTY in distributed ZIP; user supplies locally
├── models/
├── artifacts/
├── docs/
│   ├── baseline/
│   ├── database/
│   ├── jev_ai/
│   └── plans/
│       ├── backend_database_ai/
│       ├── frontend/
│       └── legacy_v2/
├── infrastructure/
├── scripts/
└── tests/
```

## Boundary rule

Detector/fusion modules must not import from `x_sentinel.jev_ai`. Jev AI consumes detector outputs; it never becomes an upstream dependency.
