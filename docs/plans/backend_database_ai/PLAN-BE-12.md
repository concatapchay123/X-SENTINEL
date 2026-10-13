# PLAN-BE-12 — Jev AI Orchestration & Guardrails

## Objective
Coordinate explain/triage/compare/report while enforcing advisory-only semantics.

## Status: PASS

## Scope

- Implement model-aware orchestration for Jev-Style-Qwen3.5-2B-Decision (GGUF) runtime (`JevAIOrchestrator`).
- Support typed decision engine contracts: Choice (categorical), Bool (calibrated polarity), and Score (expected value calculation).
- Enforce exact Jev decision prompt formatting terminating strictly on single-token position `Answer:`.
- Extract first-token logprob distributions from runtime completion and apply numerically stable softmax normalization.
- Coordinate 4 core workflows under advisory-only semantics:
  - **Explain**: Deterministic evidence projection and key contributing factor breakdown without hallucinated free text.
  - **Triage**: Calibrated priority mapping (immediate review, standard review, low priority, routine verification) preserving immutable detector truth.
  - **Compare**: Deterministic mathematical deltas between baseline and candidate snapshots + advisory risk attribution.
  - **Report**: Structured markdown report compilation with provenance, detector truth, and strict scientific limitations disclaimer.
- Enforce prompt injection defense against role spoofing, section delimiter injection, and instruction overrides.
- Enforce authority boundary isolation ensuring Jev AI cannot alter detector classifications, thresholds, or evidence.
- Maintain disabled mode guaranteeing zero network calls and graceful non-blocking fallback.

## Primary files
- `backend/src/x_sentinel/jev_ai/orchestrator.py`
- `backend/src/x_sentinel/jev_ai/schemas.py`
- `backend/src/x_sentinel/jev_ai/prompt_builder.py`
- `backend/src/x_sentinel/jev_ai/guardrails.py`
- `backend/src/x_sentinel/jev_ai/client.py`
- `backend/src/x_sentinel/jev_ai/__init__.py`
- `backend/tests/test_be12_jev_orchestration_guardrails.py`

## Task sequence

1. [x] Confirm upstream dependencies and unresolved P0 items (BE-01 through BE-11 verified; BE-11 status PASS).
2. [x] Discover Jev decision model capabilities via live runtime inspection on `http://localhost:1234/v1` (`jev-style-qwen3.5-2b-decision@q8_0` and `@bf16` verified).
3. [x] Freeze interfaces and schemas (`DecisionType`, `DecisionOption`, `OptionProbability`, `TypedDecisionRequest`, `TypedDecisionResponse`, `ExplainResult`, `TriageResult`, `CompareResult`, `ReportResult`).
4. [x] Implement exact Jev prompt builder terminating with `Answer:` (`build_decision_prompt`, `build_decision_messages`).
5. [x] Extend `JevAIClient.chat` with `logprobs` and `top_logprobs` forwarding while maintaining 100% backward compatibility.
6. [x] Implement logprob normalization, numerical stability checks, and expected score computation in `guardrails.py`.
7. [x] Implement prompt injection and authority claim guardrails (`check_prompt_injection`, `check_authority_claims`, `enforce_advisory_boundary`, `verify_detector_truth_unmodified`).
8. [x] Implement `JevAIOrchestrator` coordinating typed decisions and the 4 workflows.
9. [x] Add 55 comprehensive automated tests in `test_be12_jev_orchestration_guardrails.py` (all PASS).
10. [x] Verify full regression across foundational suites (269 tests passing with zero regressions).
11. [x] Update traceability and readiness documentation (`PLAN-BE-12.md`).

## Acceptance

### 1. Prompt Injection Cases: PASS
- Defensive scanning blocks adversarial inputs across State, Question, and Option labels:
  - Role spoofing: `<|im_start|>`, `system:`, `developer:`, `[INST]`, `<<SYS>>` -> `JevPromptInjectionBlocked`.
  - Prompt section delimiter injection: `[State]`, `[Question]`, `[Options]`, `Answer:` -> `JevPromptInjectionBlocked`.
  - Instruction override / jailbreak: "ignore previous instructions", "override detector", "set verdict to", "bypass guardrails", "choose option B" -> `JevPromptInjectionBlocked`.
  - Adversarial option labels and state injection verified with zero network calls dispatched to runtime.
  - Verified by tests: `TestPromptInjectionDefense` (10 parameterized tests).

### 2. Authority-Claim Tests: PASS
- AI output is strictly ADVISORY ONLY (`advisory_only: True` immutable on all schemas).
- Direct authority claims ("DETECTOR OVERRIDDEN", "final verdict = benign", "verdict_override", "change threshold") blocked with `JevAuthorityViolation`.
- Detector truth verification (`verify_detector_truth_unmodified`) ensures canonical detector verdict, malware score, and M1-M5 signals cannot be mutated by workflow outputs.
- Schema validators reject any attempt to instantiate `advisory_only=False`.
- Verified by tests: `TestAuthorityClaimEnforcement` (6 tests).

### 3. Response Validation: PASS
- First-token decision extraction validates that the model output token matches declared option letters (A-Z).
- Missing option logprobs in `top_logprobs` rejected with `JevIncompleteDistributionError`.
- Numerically stable softmax normalization prevents NaN/Inf and verifies probability sum equals 1.0 within 1e-4 tolerance.
- Rejects unexpected tokens, empty completions, or responses missing logprobs with `JevResponseValidationError`.
- Score expected value formula $E[S] = \sum p_i \cdot s_i$ verified with finite bounds.
- Verified by tests: `TestResponseValidation`, `TestLogprobNormalization`, and `TestTypedDecisionEngine` (15 tests).

## Extended Verification & Architectural Invariants

- **Model Capability Matrix**: Documented that Jev Decision Model operates exclusively on single-token option distributions (Choice, Bool, Score) and does NOT generate free-form text. Workflows map to structured decisions and deterministic templates accordingly.
- **LM Studio Live Verification**: Verified end-to-end against live local LM Studio runtime with both `jev-style-qwen3.5-2b-decision@q8_0` and `@bf16` variants on `http://localhost:1234/v1`.
- **Disabled Mode**: Verified that when `enabled=False`, `decide()` raises `JevAIDisabledError` with exactly zero network calls, while `explain()` and `report()` fall back gracefully to deterministic analysis without blocking backend readiness.
- **Evidence Immutability**: Verified that input `CanonicalEvidence` records remain 100% immutable across all workflow executions.

## Done definition

No silent TBDs, no undocumented schema/API changes, tests pass, and outputs are traceable to versioned config/code.

## Recommended next eligible plan
`PLAN-BE-13` (Jev AI Persistence, API & Feedback).
