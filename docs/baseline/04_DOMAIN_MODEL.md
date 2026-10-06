# 04 — DOMAIN MODEL — V3

## Canonical detector domain

- `AnalysisJob`
- `AnalysisResult`
- `SignalResult` for M1–M5
- `ModelVersion`
- `Alert`
- `Artifact`
- `AuditEvent`
- `ExperimentRun`

## Identity/authorization domain

- `User`
- `Role`
- `UserRole`

## Jev AI advisory domain

- `JevAIRun`: immutable-ish invocation metadata/output tied optionally to an analysis job.
- `JevAIFeedback`: operator evaluation of an AI output.
- `JevContext`: minimized allowlisted detector evidence.
- `JevResponse`: advisory text + model/prompt metadata.

## Invariants

1. `AnalysisResult` does not depend on `JevAIRun`.
2. `JevAIRun` may reference an `AnalysisJob`; the reverse dependency is never required for canonical decision completion.
3. Blind truth is not a domain object available to application runtime.
4. Jev output is annotation, not a new detector signal M6.
