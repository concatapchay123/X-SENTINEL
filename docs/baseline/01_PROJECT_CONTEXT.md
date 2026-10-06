# 01 — PROJECT CONTEXT

## Problem

A suspect LightGBM malware classifier can be exposed to individual files containing a backdoor trigger. X-SENTINEL attempts to flag suspicious **inputs at inference time** by comparing attribution/semantic behavior across three static feature views rather than retraining the suspect model.

## Existing concepts from the source documents

- Static EMBER2018 feature vector with 2,381 dimensions.
- Three semantic views: Structural, Behavioral/API, Metadata/String.
- M1 TADR and M2 tabular STRIP baselines.
- M3 View Contribution, M4 Cross-View, M5 Semantic Plausibility.
- Trigger families: T-concentrated, T-spread, T-cross.
- Defender modes D0 (no trusted reference) and D1 (trusted benign reference).
- Experiments E0–E5.
- Production concept: ingestion → parse → model/SHAP → detector → alert/quarantine → dashboard.
- Targets/protocols: ASR gate >50% for research continuation, >80% production target if adopted; D1 FPR target ≤1%; P95 latency target <10ms/file; 8ms breaker is a production proposal.

## Stakeholders / roles

- Research/Product owner: approves scientific and product scope.
- Data/Model engineer: data mapping, LightGBM, model lifecycle.
- Threat engineer: trigger generation, poison/manifest custody.
- Detector engineer: M1–M5 and score fusion.
- Evaluation engineer: E0–E5, statistics, blind scoring, dashboard/evidence.
- SOC/operator: uses the dashboard and exported audit evidence.
- Reviewer/acceptance board: checks reproducibility and evidence.

## Primary user flows

1. Analyst submits a vector/sample reference.
2. System validates schema and mode.
3. Model returns score + SHAP explanation.
4. Detector computes M1–M5.
5. Fusion/calibration produces suspicion score and decision.
6. System writes immutable-ish audit evidence.
7. Dashboard renders decision and view breakdown.
8. Evaluation runner reuses the same core to execute E0–E5/blind tests.

## Constraints

- No actual scientific result is available in the source material.
- Exact canonical M4/Fusion/model config had conflicts in the source documents.
- No relational DB was specified.
- REST/gRPC was only mentioned, not contracted.
- Raw PE/LIEF and vector-only research paths must remain separated.

## Product-first strategy

The repository is optimized to build the executable pipeline first and continuously emit evidence for the later report. All report tables/figures should eventually be generated from `artifacts/evidence/`.
