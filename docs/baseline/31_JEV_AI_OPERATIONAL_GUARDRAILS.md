# 31 — JEV AI OPERATIONAL GUARDRAILS

## Hard rules

1. Advisory only.
2. Local endpoint allowlist only.
3. No arbitrary tool/shell execution.
4. No blind ground truth/hidden manifests.
5. No raw PE bytes in prompts.
6. No automatic model/config/threshold changes.
7. No scientific acceptance based solely on AI prose.
8. No silent fallback to cloud APIs.
9. Context is allowlist-based, not denylist-only.
10. Every AI run is attributable to model ID + prompt version + evidence digest.

## Prompt-injection resilience

Treat all sample-derived text, strings/import names and analyst-uploaded content as untrusted data. Wrap it as evidence, never as system instructions. Do not allow PE strings to modify policies or request tools.

## Human review

For high/critical alerts, AI recommendations are suggestions only. Human/SOC workflow and canonical detector policy decide disposition.

## Privacy/retention

Keep response retention minimal and configurable. Store hashes and metadata when full text is not required. Provide a policy-controlled purge mechanism in a future implementation plan.
