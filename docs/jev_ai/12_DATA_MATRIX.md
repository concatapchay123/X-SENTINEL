# Jev AI Data Matrix

| Data | Jev default access | Stored in Jev run? | Notes |
|---|---:|---:|---|
| Canonical decision/scores | Yes | summary/hash | source of truth remains detector |
| M1–M5 diagnostics | Yes, allowlisted | summary/hash | sanitize first |
| Top-K SHAP | Yes | summary/hash | default K from config |
| Full 2,381 vector | No | No | explicit future opt-in only |
| Raw PE bytes | No | No | forbidden in V3 |
| Sample strings/import names | Limited | optional summary | treat as untrusted text |
| Blind labels/manifests | Never | Never | hard isolation |
| Approved docs/runbooks | Future optional | provenance | retrieval requires ADR |
| User question | Yes | policy-dependent | may contain sensitive text; redact/retain minimally |
| Jev response | Yes | configurable | always advisory |
