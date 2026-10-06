# 29 — JEV AI DATA CONTRACT

## Default context payload

Jev AI may receive a minimized JSON-like context containing:

- analysis ID/request ID;
- canonical decision;
- malware/suspicion scores and threshold;
- M1–M5 scores + approved diagnostics;
- three-view contribution summary;
- top-K SHAP features with sanitized names/values/contributions;
- model version/config hash/view-map hash;
- latency/warnings;
- operator question/mode;
- approved runbook snippets if explicitly enabled.

## Excluded by default

- raw PE bytes;
- full 2,381-feature vector;
- secrets/API keys;
- database credentials;
- hidden trigger manifest;
- blind labels/ground truth;
- unrelated user data;
- arbitrary filesystem content.

## Optional controlled fields

Full feature vectors or richer diagnostics require an explicit config flag and a documented reason. Raw PE content remains forbidden for Jev in V3.

## Data transformations

`canonical result -> allowlist projection -> redaction -> size cap -> digest -> prompt context`.

## Output schema

Preferred structured envelope:

```json
{
  "summary": "...",
  "evidence": ["..."],
  "interpretation": ["..."],
  "uncertainties": ["..."],
  "recommended_checks": ["..."],
  "advisory_only": true
}
```

If the local model cannot guarantee JSON, store the raw text as advisory content while preserving run metadata and hashes.
