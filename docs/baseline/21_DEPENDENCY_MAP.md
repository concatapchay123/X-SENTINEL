# 21 — DEPENDENCY MAP — V3

## Runtime dependencies

```text
Frontend
  -> FastAPI contracts
      -> AnalysisService
          -> Input schema/view mapping
          -> LightGBM/SHAP
          -> M1..M5
          -> Fusion/Decision
          -> SQL Server/Audit
      -> JevAIOrchestrator (optional)
          -> canonical AnalysisResult + DetectorScores + approved evidence summary
          -> JevAIGuardrails
          -> JevAIClient
              -> LM Studio local endpoint
          -> jev_ai_runs / feedback
```

## Forbidden dependencies

- Detection modules -> Jev AI: forbidden.
- Fusion/Decision -> Jev AI: forbidden.
- Jev AI -> blind manifest/ground truth: forbidden.
- Frontend -> SQL Server directly: forbidden.
- Frontend -> detector formula implementation: forbidden.
- Jev AI -> shell/process execution: forbidden in V3.

## Plan dependencies

See `docs/plans/MASTER_PLAN_V3.md` for the full track graph.
