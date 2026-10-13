from __future__ import annotations

import datetime
from typing import Any

from x_sentinel.jev_ai.client import JevAIClient, JevAIDisabledError
from x_sentinel.jev_ai.guardrails import (
    JevResponseValidationError,
    calculate_expected_score,
    check_authority_claims,
    check_blind_data_in_text,
    check_prompt_injection,
    compute_context_digest,
    enforce_advisory_boundary,
    normalize_option_logprobs,
    redact_sensitive_text,
    verify_detector_truth_unmodified,
)
from x_sentinel.jev_ai.prompt_builder import (
    build_decision_messages,
    build_messages,
    build_safe_context,
    project_canonical_evidence,
)
from x_sentinel.jev_ai.schemas import (
    CompareResult,
    DecisionOption,
    DecisionType,
    ExplainResult,
    JevRequest,
    JevResponse,
    ReportResult,
    TriageResult,
    TypedDecisionRequest,
    TypedDecisionResponse,
)


class JevAIOrchestrator:
    """Coordinates Jev AI workflows (explain, triage, compare, report) while enforcing

    strict advisory-only semantics, deterministic trust boundaries, and exact model contracts.

    Invariants:
    1. Pure headless execution; zero Jinja/HTML or simulated previews.
    2. Zero authority escalation: Jev AI can NEVER mutate detector verdicts,
       thresholds, or evidence.
    3. Disabled mode: Zero network calls when client is disabled.
    4. Exact Jev decision prompt formatting for choice, bool, and score decisions.
    5. Robust first-token logprob extraction, numerical normalization, and response validation.
    """

    def __init__(self, client: JevAIClient, *, max_context_chars: int = 30_000) -> None:
        self.client = client
        self.max_context_chars = max_context_chars

    def _client_model_id(self) -> str:
        val = getattr(self.client, "model_id", None)
        return val if isinstance(val, str) and val else "jev-local-TBD"

    def _client_prompt_version(self) -> str:
        val = getattr(self.client, "prompt_version", None)
        return val if isinstance(val, str) and val else "jev-v3.0.0"

    # -----------------------------------------------------------------------
    # Backward-Compatible Run Interface (PLAN-BE-10 / BE-11 compatibility)
    # -----------------------------------------------------------------------

    def run(self, request: JevRequest) -> tuple[JevResponse, str]:
        """Executes advisory prompt chat completion with safe context projection."""
        messages, input_digest = build_messages(request, max_chars=self.max_context_chars)
        response = self.client.chat(messages)
        check_blind_data_in_text(response.text)
        check_authority_claims(response.text)
        enforce_advisory_boundary(response)
        return response, input_digest

    # -----------------------------------------------------------------------
    # Typed Decision Engine (Choice, Bool, Score)
    # -----------------------------------------------------------------------

    def decide(self, request: TypedDecisionRequest) -> TypedDecisionResponse:
        """Executes a single-turn typed decision against Jev-Style Decision Model.

        Extracts first-token logprob distribution, validates probabilities, and returns
        structured advisory decision.

        Raises:
            JevAIDisabledError: When runtime client is disabled.
            JevPromptInjectionBlocked: When adversarial patterns are detected.
            JevResponseValidationError: When runtime output fails contract validation.
            JevAuthorityViolation: When response attempts authority escalation.
        """
        if not self.client.enabled:
            raise JevAIDisabledError("Jev AI runtime is disabled; decision cannot be executed")

        # Defensive scan on State and Question
        check_blind_data_in_text(request.state)
        check_prompt_injection(request.state)
        check_authority_claims(request.state)

        check_blind_data_in_text(request.question)
        check_prompt_injection(request.question)
        check_authority_claims(request.question)

        # Build exact Jev prompt messages (single-turn, independent request)
        messages, prompt_digest = build_decision_messages(
            request.state,
            request.question,
            request.options,
        )

        num_options = len(request.options)
        declared_letters = [chr(ord("A") + i) for i in range(num_options)]

        # Call LM Studio runtime requesting_max_tokens=1 and top_logprobs
        response = self.client.chat(
            messages,
            temperature=0.0,
            max_output_tokens=1,
            logprobs=True,
            top_logprobs=max(num_options, 5),
        )

        # Token extraction (strictly uppercase single option letter, no control whitespace)
        raw_text = response.text or ""
        if any(ch in raw_text for ch in ("\n", "\r", "\t")):
            raise JevResponseValidationError(
                f"Model returned decision token containing forbidden "
                f"control whitespace: {raw_text!r}"
            )
        selected_letter = raw_text.strip()

        if not selected_letter:
            raise JevResponseValidationError("Model returned empty token for decision")

        if selected_letter != selected_letter.upper():
            raise JevResponseValidationError(
                f"Selected token '{selected_letter}' must be uppercase "
                f"option letter {declared_letters}"
            )

        if selected_letter not in declared_letters:
            raise JevResponseValidationError(
                f"Selected token '{selected_letter}' is not a declared "
                f"option letter {declared_letters}"
            )

        # Logprob extraction and normalization
        if not response.logprobs:
            raise JevResponseValidationError(
                "Runtime response missing required logprobs for typed decision"
            )

        if isinstance(response.logprobs, dict) and isinstance(
            response.logprobs.get("content"), list
        ):
            content_list = response.logprobs["content"]
            if len(content_list) != 1:
                raise JevResponseValidationError(
                    f"Single-token decision invariant violated: "
                    f"expected 1 content token, got {len(content_list)}"
                )
            if isinstance(content_list[0], dict) and "token" in content_list[0]:
                first_tok = str(content_list[0]["token"]).strip()
                if first_tok and first_tok != selected_letter:
                    raise JevResponseValidationError(
                        f"Selected token '{selected_letter}' mismatch with "
                        f"logprobs content token '{first_tok}'"
                    )

        option_probabilities = normalize_option_logprobs(
            response.logprobs,
            request.options,
            allow_incomplete=False,
        )

        # Greedy consistency check: selected_letter must match highest probability option
        max_prob = max(p.probability for p in option_probabilities)
        selected_prob = next(
            p.probability for p in option_probabilities if p.letter == selected_letter
        )
        if max_prob - selected_prob > 1e-4:
            raise JevResponseValidationError(
                f"Selected token '{selected_letter}' (prob={selected_prob:.4f}) is inconsistent "
                f"with highest probability option (prob={max_prob:.4f})"
            )

        # Build distribution map
        distribution_dict = {prob.option_id: prob.probability for prob in option_probabilities}

        # Find selected option details
        selected_index = ord(selected_letter) - ord("A")
        selected_option = request.options[selected_index]

        # Calculate Score expected value if applicable
        expected_score: float | None = None
        if request.decision_type == DecisionType.SCORE:
            if request.score_levels is None:
                raise JevResponseValidationError("score_levels missing for Score decision")
            expected_score = calculate_expected_score(
                option_probabilities,
                request.score_levels,
            )

        # Calculate Bool value if applicable
        bool_value: bool | None = None
        if request.decision_type == DecisionType.BOOL:
            # First option (A) corresponds to True / Yes, second (B) to False / No
            bool_value = selected_letter == "A"

        output_digest = compute_context_digest(
            {
                "decision_type": request.decision_type.value,
                "selected_letter": selected_letter,
                "selected_option_id": selected_option.id,
                "probability_distribution": {k: round(v, 8) for k, v in distribution_dict.items()},
                "expected_score": round(expected_score, 8) if expected_score is not None else None,
                "bool_value": bool_value,
                "model_id": response.model_id,
                "prompt_version": response.prompt_version,
            }
        )

        result = TypedDecisionResponse(
            decision_type=request.decision_type,
            selected_letter=selected_letter,
            selected_option_id=selected_option.id,
            selected_label=selected_option.label,
            probabilities=option_probabilities,
            probability_distribution=distribution_dict,
            expected_score=expected_score,
            bool_value=bool_value,
            model_id=response.model_id,
            prompt_version=response.prompt_version,
            advisory_only=True,
            latency_ms=response.latency_ms,
            raw_tokens=(
                response.logprobs.get("content") if isinstance(response.logprobs, dict) else None
            ),
            context_digest=request.context_digest,
            prompt_digest=prompt_digest,
            output_digest=output_digest,
            validation_status="completed",
        )

        enforce_advisory_boundary(result)
        return result

    def decide_choice(
        self,
        state: str,
        question: str,
        options: list[str] | list[DecisionOption],
    ) -> TypedDecisionResponse:
        """Convenience method for categorical Choice decisions."""
        parsed_options = [
            opt
            if isinstance(opt, DecisionOption)
            else DecisionOption(id=f"opt_{i + 1}", label=str(opt))
            for i, opt in enumerate(options)
        ]
        req = TypedDecisionRequest(
            decision_type=DecisionType.CHOICE,
            state=state,
            question=question,
            options=parsed_options,
        )
        return self.decide(req)

    def decide_bool(
        self,
        state: str,
        proposition: str,
        *,
        yes_label: str = "Yes",
        no_label: str = "No",
    ) -> TypedDecisionResponse:
        """Convenience method for Bool decisions with calibrated polarity."""
        options = [
            DecisionOption(id="yes", label=yes_label),
            DecisionOption(id="no", label=no_label),
        ]
        req = TypedDecisionRequest(
            decision_type=DecisionType.BOOL,
            state=state,
            question=proposition,
            options=options,
        )
        return self.decide(req)

    def decide_score(
        self,
        state: str,
        question: str,
        levels: list[tuple[str, float]],
    ) -> TypedDecisionResponse:
        """Convenience method for Score decisions with expected value calculation."""
        options = [
            DecisionOption(id=f"level_{i + 1}", label=lvl[0]) for i, lvl in enumerate(levels)
        ]
        score_values = [lvl[1] for lvl in levels]
        req = TypedDecisionRequest(
            decision_type=DecisionType.SCORE,
            state=state,
            question=question,
            options=options,
            score_levels=score_values,
        )
        return self.decide(req)

    # -----------------------------------------------------------------------
    # High-Level Advisory Workflows
    # -----------------------------------------------------------------------

    def explain(
        self,
        evidence: Any,
        *,
        question: str | None = None,
    ) -> ExplainResult:
        """Executes Explain workflow: Grounded, evidence-based advisory breakdown.

        Since Jev Decision Model does not generate free-form text, explanation uses
        deterministic evidence projection combined with an optional structured triage decision.
        """
        if question is not None:
            check_blind_data_in_text(question)
            check_prompt_injection(question)
            check_authority_claims(question)

        # Safe context projection
        safe_ctx = project_canonical_evidence(evidence)
        safe_dict, _, digest = build_safe_context(safe_ctx, max_chars=self.max_context_chars)

        decision = safe_dict.get("decision", "UNKNOWN")
        malware_score = safe_dict.get("malware_score")
        suspicion = safe_dict.get("suspicion_score")
        detector_scores = safe_dict.get("detector_scores", {})
        diagnostics = safe_dict.get("detector_diagnostics", {})
        warnings = safe_dict.get("warnings", [])

        # Deterministic evidence breakdown
        breakdown = {
            "canonical_verdict": decision,
            "malware_score": malware_score,
            "suspicion_score": suspicion,
            "detector_scores": detector_scores,
            "latency_diagnostics": diagnostics.get("latency_ms", {}),
        }

        # Key factors extraction
        key_factors: list[str] = []
        for det_name, score in detector_scores.items():
            if score > 0.5:
                key_factors.append(f"{det_name} reported elevated risk ({score:.3f})")
            elif score > 0.2:
                key_factors.append(f"{det_name} reported moderate activity ({score:.3f})")

        if not key_factors:
            key_factors.append("All detectors reported baseline/quiescent signal levels")

        # Uncertainty notes
        uncertainty_notes: list[str] = []
        if malware_score is not None and 0.4 <= malware_score <= 0.6:
            uncertainty_notes.append(
                "Malware score is within the borderline uncertainty interval [0.4, 0.6]"
            )
        if warnings:
            uncertainty_notes.extend([f"Detector warning: {w}" for w in warnings])
        if not detector_scores:
            uncertainty_notes.append("No granular detector signals available in canonical evidence")

        # Recommended checks
        recommended_checks: list[str] = [
            "Verify static PE structure and import table anomalies",
            "Examine suspicious process ancestry or behavioral indicators",
            "Cross-reference telemetry with external threat intelligence if permitted",
        ]

        # Decision model triage check when client is enabled (never swallow validation errors)
        advisory_decision: TypedDecisionResponse | None = None
        if self.client.enabled:
            state_summary = (
                f"Canonical decision is '{decision}' with malware_score={malware_score} "
                f"and detector signals {detector_scores}."
            )
            effective_q = (
                redact_sensitive_text(question.strip())
                if question and question.strip()
                else "Which factor warrants highest human analyst review priority?"
            )
            advisory_decision = self.decide_choice(
                state=state_summary,
                question=effective_q,
                options=[
                    "Anomalous detector signals (M1-M5)",
                    "Borderline decision threshold score",
                    "Diagnostic telemetry latency/warnings",
                    "Standard routine verification",
                ],
            )

        summary_text = (
            f"Advisory Explanation: Canonical verdict is '{decision}' with "
            f"malware score {malware_score}. "
            f"Key contributing factors: {'; '.join(key_factors[:2])}. "
            "Advisory only: this assessment does not alter canonical detector decisions."
        )

        output_digest = compute_context_digest(
            {
                "workflow": "explain",
                "input_digest": digest,
                "summary": summary_text,
                "selected_option_id": (
                    advisory_decision.selected_option_id if advisory_decision else None
                ),
            }
        )

        result = ExplainResult(
            analysis_id=safe_dict.get("analysis_id") or safe_dict.get("request_id"),
            request_id=safe_dict.get("request_id"),
            workflow="explain",
            summary=summary_text,
            evidence_breakdown=breakdown,
            key_factors=key_factors,
            uncertainty_notes=uncertainty_notes,
            recommended_checks=recommended_checks,
            advisory_decision=advisory_decision,
            advisory_only=True,
            input_digest=digest,
            output_digest=output_digest,
            model_id=advisory_decision.model_id if advisory_decision else self._client_model_id(),
            prompt_version=(
                advisory_decision.prompt_version
                if advisory_decision
                else self._client_prompt_version()
            ),
            validation_status="completed",
            latency_ms=advisory_decision.latency_ms if advisory_decision else 0.0,
        )

        verify_detector_truth_unmodified(evidence, result)
        enforce_advisory_boundary(result)
        return result

    def triage(self, evidence: Any) -> TriageResult:
        """Executes Triage workflow: Maps canonical evidence to calibrated review priority."""
        safe_ctx = project_canonical_evidence(evidence)
        safe_dict, _, digest = build_safe_context(safe_ctx, max_chars=self.max_context_chars)

        decision = safe_dict.get("decision", "UNKNOWN")
        malware_score = safe_dict.get("malware_score", 0.0)
        signals = safe_dict.get("detector_scores", {})

        state_summary = (
            f"Sample evaluated with canonical decision '{decision}', "
            f"malware_score={malware_score:.3f}. "
            f"Detector signals: {signals}."
        )

        triage_options = [
            DecisionOption(id="immediate_escalation", label="Immediate Escalation (High Risk)"),
            DecisionOption(id="standard_review", label="Standard Priority Review"),
            DecisionOption(id="low_priority_monitor", label="Low Priority Monitoring"),
            DecisionOption(id="routine_verification", label="Routine Verification"),
        ]

        decision_resp = self.decide(
            TypedDecisionRequest(
                decision_type=DecisionType.CHOICE,
                state=state_summary,
                question="What is the recommended review priority for this detection?",
                options=triage_options,
                context_digest=digest,
            )
        )

        # Map selected option to category
        category_map = {
            "immediate_escalation": "immediate_review",
            "standard_review": "standard_review",
            "low_priority_monitor": "low_priority",
            "routine_verification": "routine_verification",
        }
        category = category_map.get(decision_resp.selected_option_id, "standard_review")

        action_map = {
            "immediate_review": (
                "Assign Tier-3 security analyst immediately; quarantine specimen pending triage."
            ),
            "standard_review": "Schedule for standard queue review within 4 hours.",
            "low_priority": "Log specimen for passive observation; review in next daily batch.",
            "routine_verification": (
                "No immediate intervention required; maintain baseline telemetry."
            ),
        }

        rec_action = action_map.get(category, "Review sample per SOP.")
        output_digest = compute_context_digest(
            {
                "workflow": "triage",
                "input_digest": digest,
                "priority_category": category,
                "selected_option_id": decision_resp.selected_option_id,
                "decision_output_digest": decision_resp.output_digest,
            }
        )

        result = TriageResult(
            analysis_id=safe_dict.get("analysis_id") or safe_dict.get("request_id"),
            request_id=safe_dict.get("request_id"),
            workflow="triage",
            priority_category=category,
            priority_label=decision_resp.selected_label,
            advisory_decision=decision_resp,
            detector_verdict=decision,
            detector_malware_score=malware_score,
            recommended_analyst_action=rec_action,
            advisory_only=True,
            input_digest=digest,
            output_digest=output_digest,
            model_id=decision_resp.model_id,
            prompt_version=decision_resp.prompt_version,
            validation_status="completed",
            latency_ms=decision_resp.latency_ms,
        )

        verify_detector_truth_unmodified(evidence, result)
        enforce_advisory_boundary(result)
        return result

    def compare(self, evidence_a: Any, evidence_b: Any) -> CompareResult:
        """Executes Compare workflow: Deterministic delta comparison + advisory risk attribution."""
        safe_ctx_a = project_canonical_evidence(evidence_a)
        safe_dict_a, _, digest_a = build_safe_context(safe_ctx_a, max_chars=self.max_context_chars)

        safe_ctx_b = project_canonical_evidence(evidence_b)
        safe_dict_b, _, digest_b = build_safe_context(safe_ctx_b, max_chars=self.max_context_chars)

        # Deterministic mathematical deltas
        score_a = safe_dict_a.get("malware_score") or 0.0
        score_b = safe_dict_b.get("malware_score") or 0.0
        delta_malware = score_b - score_a

        suspicion_a = safe_dict_a.get("suspicion_score") or 0.0
        suspicion_b = safe_dict_b.get("suspicion_score") or 0.0
        delta_suspicion = suspicion_b - suspicion_a

        signals_a = safe_dict_a.get("detector_scores", {})
        signals_b = safe_dict_b.get("detector_scores", {})
        all_signals = sorted(set(signals_a.keys()) | set(signals_b.keys()))
        signal_deltas = {
            sig: signals_b.get(sig, 0.0) - signals_a.get(sig, 0.0) for sig in all_signals
        }

        diff_summary = {
            "baseline_decision": safe_dict_a.get("decision"),
            "candidate_decision": safe_dict_b.get("decision"),
            "delta_malware_score": round(delta_malware, 4),
            "delta_suspicion_score": round(delta_suspicion, 4),
            "signal_deltas": {k: round(v, 4) for k, v in signal_deltas.items()},
        }

        # Structured comparison decision via Jev
        state_compare = (
            f"Snapshot A decision '{safe_dict_a.get('decision')}' (malware_score={score_a:.3f}). "
            f"Snapshot B decision '{safe_dict_b.get('decision')}' (malware_score={score_b:.3f}). "
            f"Score delta (B - A) = {delta_malware:+.3f}."
        )

        compare_options = [
            DecisionOption(id="snapshot_a_higher", label="Snapshot A exhibits higher anomaly risk"),
            DecisionOption(id="snapshot_b_higher", label="Snapshot B exhibits higher anomaly risk"),
            DecisionOption(id="equivalent_risk", label="Equivalent risk profile across snapshots"),
            DecisionOption(id="inconclusive", label="Inconclusive comparison based on evidence"),
        ]

        combined_digest = compute_context_digest(
            {"baseline_digest": digest_a, "candidate_digest": digest_b}
        )

        advisory_decision: TypedDecisionResponse | None = None
        if self.client.enabled:
            advisory_decision = self.decide(
                TypedDecisionRequest(
                    decision_type=DecisionType.CHOICE,
                    state=state_compare,
                    question="Which snapshot presents higher anomaly risk?",
                    options=compare_options,
                    context_digest=combined_digest,
                )
            )

        adv_label = (
            advisory_decision.selected_label
            if advisory_decision
            else "Deterministic delta computed"
        )
        summary_text = (
            f"Comparison Delta: Malware score shifted by {delta_malware:+.4f} "
            f"from Snapshot A ({score_a:.3f}) to Snapshot B ({score_b:.3f}). "
            f"Advisory comparison: {adv_label}."
        )

        output_digest = compute_context_digest(
            {
                "workflow": "compare",
                "input_digest": combined_digest,
                "deterministic_diff": diff_summary,
                "selected_option_id": (
                    advisory_decision.selected_option_id if advisory_decision else None
                ),
            }
        )

        result = CompareResult(
            baseline_id=safe_dict_a.get("analysis_id") or safe_dict_a.get("request_id"),
            candidate_id=safe_dict_b.get("analysis_id") or safe_dict_b.get("request_id"),
            request_id=safe_dict_b.get("request_id") or safe_dict_a.get("request_id"),
            workflow="compare",
            deterministic_diff=diff_summary,
            advisory_decision=advisory_decision,
            comparison_summary=summary_text,
            advisory_only=True,
            input_digest=combined_digest,
            output_digest=output_digest,
            model_id=advisory_decision.model_id if advisory_decision else self._client_model_id(),
            prompt_version=(
                advisory_decision.prompt_version
                if advisory_decision
                else self._client_prompt_version()
            ),
            validation_status="completed",
            latency_ms=advisory_decision.latency_ms if advisory_decision else 0.0,
        )

        verify_detector_truth_unmodified((evidence_a, evidence_b), result)
        enforce_advisory_boundary(result)
        return result

    def report(
        self,
        evidence: Any,
        *,
        title: str = "Analysis Advisory Report",
    ) -> ReportResult:
        """Executes Report workflow: Generates deterministic evidence-grounded report.

        Adheres strictly to model-aware boundaries: Jev Decision Model does not author
        arbitrary free-form documents; this report is constructed deterministically
        from canonical evidence and structured advisory decisions.
        """
        check_blind_data_in_text(title)
        check_prompt_injection(title)
        check_authority_claims(title)
        safe_title = redact_sensitive_text(title.strip() or "Analysis Advisory Report")

        safe_ctx = project_canonical_evidence(evidence)
        safe_dict, _, digest = build_safe_context(safe_ctx, max_chars=self.max_context_chars)

        decision = safe_dict.get("decision", "UNKNOWN")
        malware_score = safe_dict.get("malware_score", 0.0)
        suspicion = safe_dict.get("suspicion_score") or 0.0
        signals = safe_dict.get("detector_scores", {})
        provenance = safe_dict.get("provenance", {})
        diagnostics = safe_dict.get("detector_diagnostics", {})

        now_iso = datetime.datetime.now(datetime.UTC).isoformat()

        # Build markdown report deterministically
        md_lines = [
            f"# {safe_title}",
            "",
            f"**Generated:** {now_iso}  ",
            f"**Context Digest (SHA-256):** `{digest}`  ",
            "**Advisory Only:** True  ",
            "",
            "## 1. Canonical Detector Truth",
            f"- **Verdict:** `{decision}`",
            f"- **Malware Score:** `{malware_score:.4f}`",
            f"- **Suspicion Score:** `{suspicion:.4f}`",
            "",
            "## 2. Granular Detector Signals (M1–M5)",
        ]
        if signals:
            for sig, val in sorted(signals.items()):
                md_lines.append(f"- **{sig}:** `{val:.4f}`")
        else:
            md_lines.append("- *No individual signal breakdown available.*")

        md_lines.extend(
            [
                "",
                "## 3. Provenance & Artifact Integrity",
                f"- **Model Hash:** `{provenance.get('model_hash', 'N/A')}`",
                f"- **Build Digest:** `{provenance.get('build_digest', 'N/A')}`",
                f"- **Code Commit:** `{provenance.get('code_commit', 'N/A')}`",
                f"- **Threshold ID:** `{provenance.get('threshold_id', 'N/A')}`",
                "",
                "## 4. Scientific Limitations & Authority Disclaimer",
                "> [!NOTE]",
                "> This advisory analysis report is compiled deterministically "
                "from canonical detector evidence.",
                "> Jev AI acts solely as a collaborative advisory mechanism "
                "and possesses zero authority to",
                "> alter, override, or re-calibrate the scientific verdicts or "
                "thresholds produced by X-SENTINEL detectors.",
                "",
            ]
        )

        markdown_content = "\n".join(md_lines)
        detector_summary = {
            "verdict": decision,
            "malware_score": malware_score,
            "suspicion_score": suspicion,
            "signals": signals,
        }
        output_digest = compute_context_digest(
            {
                "workflow": "report",
                "input_digest": digest,
                "title": safe_title,
                "detector_summary": detector_summary,
            }
        )

        result = ReportResult(
            analysis_id=safe_dict.get("analysis_id") or safe_dict.get("request_id"),
            request_id=safe_dict.get("request_id"),
            workflow="report",
            title=safe_title,
            timestamp=now_iso,
            detector_summary=detector_summary,
            advisory_assessment={
                "provenance": provenance,
                "diagnostics": diagnostics,
            },
            limitations_disclaimer="Advisory only. Zero influence on canonical detector decisions.",
            markdown_content=markdown_content,
            advisory_only=True,
            input_digest=digest,
            output_digest=output_digest,
            model_id=self._client_model_id(),
            prompt_version=self._client_prompt_version(),
            validation_status="completed",
            latency_ms=0.0,
        )

        verify_detector_truth_unmodified(evidence, result)
        enforce_advisory_boundary(result)
        return result
