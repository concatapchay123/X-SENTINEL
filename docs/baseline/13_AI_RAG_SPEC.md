# 13 — AI / RAG SPEC — V3

## Decision

**AI is now APPLICABLE as an OPTIONAL LOCAL COLLABORATOR.**  
**RAG/vector database remains NOT REQUIRED for the detection path.**

V3 introduces Jev AI through LM Studio using an OpenAI-compatible local endpoint. This is a support layer above canonical evidence, not part of the M1–M5 scientific detector.

## Allowed AI use

- explain detector evidence;
- triage assistance;
- compare analysis results/config versions;
- draft analyst reports;
- answer questions over approved project/runbook context.

## Disallowed AI use

- replacing LightGBM/SHAP/M1–M5/fusion;
- changing thresholds automatically;
- generating scientific metrics without canonical experiment artifacts;
- reading blind labels/hidden trigger manifests;
- executing samples or arbitrary OS commands;
- cloud egress by default.

## RAG policy

No vector DB is required in V3. If document retrieval is later added, it must use approved project docs/runbooks only, have an ADR, access-control model, provenance and evaluation plan. RAG must remain outside the canonical detector path.

## Model specifics

The exact Jev model ID, architecture, license, quantization, context window and hardware profile are **TBD from the actual local model selected in LM Studio**. Do not guess these values in code or reports.
