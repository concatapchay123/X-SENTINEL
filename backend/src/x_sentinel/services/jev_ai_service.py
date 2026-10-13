from __future__ import annotations

import copy
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from x_sentinel.audit.evidence import CanonicalEvidence, EvidenceIntegrityError
from x_sentinel.config import settings
from x_sentinel.database.models import AnalysisJob, AuditEvent, JevAIFeedback, JevAIRun
from x_sentinel.database.repositories.audit_event import AuditEventRepository
from x_sentinel.database.repositories.evidence import CanonicalEvidenceRepository
from x_sentinel.database.repositories.jev_ai import (
    _CONTROL_CHAR_RE,
    _SUPPLEMENTAL_OVERRIDE_RE,
    DuplicateFeedbackError,
    JevAIFeedbackRepository,
    JevAIRepositoryError,
    JevAIRunRepository,
    sanitize_error_message,
)
from x_sentinel.jev_ai.guardrails import (
    JevContextBlocked,
    check_authority_claims,
    check_blind_data_in_text,
    check_prompt_injection,
    classify_jev_failure,
    compute_context_digest,
)
from x_sentinel.jev_ai.orchestrator import JevAIOrchestrator
from x_sentinel.jev_ai.prompt_builder import build_safe_context, project_canonical_evidence
from x_sentinel.jev_ai.schemas import (
    CompareResult,
    ExplainResult,
    ReportResult,
    TriageResult,
)
from x_sentinel.security.auth import ANONYMOUS_USER, AuthUser, Role, ensure_persisted_user


class JevAIServiceError(Exception):
    """Structured service-layer exception mapped deterministically to HTTP error responses."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        run_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.run_id = run_id

    def to_detail(self) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "advisory_only": True,
        }
        if self.run_id is not None:
            detail["run_id"] = self.run_id
        return detail


def _is_admin(user: AuthUser | None) -> bool:
    if settings.api_auth_mode == "none" or user is None:
        return True
    if user.user_id == ANONYMOUS_USER.user_id:
        return True
    return user.has_role(Role.ADMIN.value)


def _check_job_ownership(job: AnalysisJob, user: AuthUser | None) -> None:
    if _is_admin(user):
        return
    if job.user_id is not None and user is not None and job.user_id != user.user_id:
        raise JevAIServiceError(
            status_code=403,
            code="XS_FORBIDDEN",
            message="Access denied: analysis record belongs to another user",
        )


def _check_run_ownership(
    run: JevAIRun,
    user: AuthUser | None,
    session: Session | None = None,
) -> None:
    if _is_admin(user):
        return
    if (
        run.requested_by_user_id is not None
        and user is not None
        and run.requested_by_user_id != user.user_id
    ):
        raise JevAIServiceError(
            status_code=403,
            code="XS_FORBIDDEN",
            message="Access denied: Jev AI run belongs to another user",
        )
    if run.analysis_job_id is not None and session is not None:
        job = session.get(AnalysisJob, run.analysis_job_id)
        if job is not None:
            _check_job_ownership(job, user)


def _resolve_analysis_job(session: Session, identifier: str) -> AnalysisJob:
    job: AnalysisJob | None = None
    try:
        parsed_uuid = uuid.UUID(str(identifier))
        job = session.get(AnalysisJob, parsed_uuid)
    except (ValueError, TypeError):
        pass

    if job is None:
        job = session.scalar(select(AnalysisJob).where(AnalysisJob.request_id == str(identifier)))

    if job is None:
        raise JevAIServiceError(
            status_code=404,
            code="XS_ANALYSIS_NOT_FOUND",
            message=f"Analysis record '{identifier}' was not found",
        )
    return job


def _load_canonical_evidence(session: Session, job: AnalysisJob) -> CanonicalEvidence:
    ev_repo = CanonicalEvidenceRepository(session)
    try:
        evidence = ev_repo.get_canonical_evidence(job.request_id)
        if evidence is not None:
            evidence.verify_integrity()
            return evidence
    except EvidenceIntegrityError as exc:
        raise JevAIServiceError(
            status_code=409,
            code="XS_EVIDENCE_TAMPERED",
            message=f"Canonical evidence integrity verification failed: {exc}",
        ) from exc

    raise JevAIServiceError(
        status_code=404,
        code="XS_ANALYSIS_NOT_FOUND",
        message=f"Canonical evidence for analysis '{job.request_id}' was not found",
    )


def _extract_workflow_payload(
    mode: str,
    result: ExplainResult | TriageResult | CompareResult | ReportResult,
) -> tuple[dict[str, Any], str]:
    """Extract structured decision_result dict and response_text from an orchestrator result."""
    if isinstance(result, ExplainResult):
        decision_dict = result.model_dump(mode="json")
        text = result.summary
    elif isinstance(result, TriageResult):
        decision_dict = result.model_dump(mode="json")
        text = result.recommended_analyst_action
    elif isinstance(result, CompareResult):
        decision_dict = result.model_dump(mode="json")
        text = result.comparison_summary
    elif isinstance(result, ReportResult):
        decision_dict = result.model_dump(mode="json")
        text = result.markdown_content
    else:
        raise ValueError(f"Unsupported workflow result for mode {mode!r}")

    adv = decision_dict.get("advisory_decision")
    if isinstance(adv, dict):
        adv.pop("raw_tokens", None)
    return decision_dict, text


class JevAIService:
    """Service coordinating Jev AI persistence, non-blocking execution, RBAC, and feedback."""

    def execute_workflow(
        self,
        session: Session,
        orchestrator: JevAIOrchestrator,
        *,
        analysis_id: str,
        mode: str = "explain",
        compare_with_analysis_id: str | None = None,
        focus_signals: list[str] | None = None,
        question: str | None = None,
        user: AuthUser | None = None,
    ) -> JevAIRun:
        clean_mode = (mode or "explain").strip().lower()
        if clean_mode == "docs":
            raise JevAIServiceError(
                status_code=422,
                code="XS_AI_MODE_UNSUPPORTED",
                message="Mode 'docs' is reserved for documentation QA (/v1/ai/docs/ask)",
            )
        if clean_mode not in {"explain", "triage", "compare", "report"}:
            raise JevAIServiceError(
                status_code=422,
                code="XS_INPUT_INVALID",
                message=f"Unsupported Jev AI workflow mode '{mode}'",
            )

        if clean_mode == "compare" and (
            not compare_with_analysis_id or not compare_with_analysis_id.strip()
        ):
            raise JevAIServiceError(
                status_code=422,
                code="XS_INPUT_INVALID",
                message="compare_with_analysis_id is required when mode is 'compare'",
            )

        if question is not None and _CONTROL_CHAR_RE.search(question):
            raise JevAIServiceError(
                status_code=422,
                code="XS_INPUT_INVALID",
                message="question contains forbidden control characters or NUL bytes",
            )

        # 1. Resolve canonical AnalysisJob(s) and enforce server-side ownership
        job = _resolve_analysis_job(session, analysis_id)
        _check_job_ownership(job, user)
        evidence_primary = _load_canonical_evidence(session, job)

        candidate_job: AnalysisJob | None = None
        evidence_candidate: CanonicalEvidence | None = None
        if clean_mode == "compare" and compare_with_analysis_id is not None:
            candidate_job = _resolve_analysis_job(session, compare_with_analysis_id.strip())
            _check_job_ownership(candidate_job, user)
            if candidate_job.id == job.id:
                raise JevAIServiceError(
                    status_code=422,
                    code="XS_INPUT_INVALID",
                    message="compare_with_analysis_id must reference a distinct analysis record",
                )
            evidence_candidate = _load_canonical_evidence(session, candidate_job)

        # 2. Project safe context and compute initial SHA-256 input digest
        try:
            safe_ctx_primary = project_canonical_evidence(evidence_primary)
            safe_dict_primary, _, digest_primary = build_safe_context(
                safe_ctx_primary, max_chars=orchestrator.max_context_chars
            )
            if clean_mode == "compare" and evidence_candidate is not None:
                safe_ctx_cand = project_canonical_evidence(evidence_candidate)
                safe_dict_cand, _, digest_cand = build_safe_context(
                    safe_ctx_cand, max_chars=orchestrator.max_context_chars
                )
                initial_digest = compute_context_digest(
                    {"baseline_digest": digest_primary, "candidate_digest": digest_cand}
                )
                initial_summary: dict[str, Any] = {
                    "workflow": "compare",
                    "advisory_only": True,
                    "baseline_id": safe_dict_primary.get("request_id"),
                    "candidate_id": safe_dict_cand.get("request_id"),
                    "baseline_job_id": str(job.id),
                    "candidate_job_id": str(candidate_job.id) if candidate_job else None,
                }
            else:
                initial_digest = digest_primary
                initial_summary = {
                    "workflow": clean_mode,
                    "advisory_only": True,
                    "request_id": safe_dict_primary.get("request_id"),
                    "decision": safe_dict_primary.get("decision"),
                    "malware_score": safe_dict_primary.get("malware_score"),
                    "focus_signals": focus_signals or [],
                }
        except JevContextBlocked as exc:
            raise JevAIServiceError(
                status_code=422,
                code="XS_AI_CONTEXT_BLOCKED",
                message=sanitize_error_message(str(exc)) or "Context blocked by safety guardrails",
            ) from exc

        if not settings.jev_ai_store_context_summary:
            initial_summary = {
                "workflow": clean_mode,
                "advisory_only": True,
                "retention_redacted": True,
                "baseline_id": initial_summary.get("baseline_id"),
                "candidate_id": initial_summary.get("candidate_id"),
            }

        persisted_user_id = ensure_persisted_user(session, user)
        job_uuid = job.id
        job_request_id = job.request_id
        model_id = orchestrator._client_model_id()
        prompt_version = orchestrator._client_prompt_version()

        run_repo = JevAIRunRepository(session)
        audit_repo = AuditEventRepository(session)

        # 3. Check disabled state before launching runtime
        is_disabled = (
            settings.jev_ai_mode.strip().lower() == "disabled" or not orchestrator.client.enabled
        )
        if is_disabled:
            blocked_run = run_repo.create_run(
                mode=clean_mode,
                status="blocked",
                model_id=model_id,
                prompt_version=prompt_version,
                input_digest_sha256=initial_digest,
                context_summary=initial_summary,
                analysis_job_id=job_uuid,
                requested_by_user_id=persisted_user_id,
                error_code="XS_AI_DISABLED",
                error_message="Jev AI collaborative runtime is disabled",
            )
            blocked_run_id = str(blocked_run.id)
            audit_repo.add(
                AuditEvent(
                    request_id=job_request_id,
                    user_id=persisted_user_id,
                    event_type="jev_ai.run.blocked",
                    entity_type="jev_ai_run",
                    entity_id=blocked_run_id,
                    payload={
                        "run_id": blocked_run_id,
                        "mode": clean_mode,
                        "error_code": "XS_AI_DISABLED",
                        "advisory_only": True,
                    },
                )
            )
            session.commit()
            raise JevAIServiceError(
                status_code=503,
                code="XS_AI_DISABLED",
                message="Jev AI collaborative runtime is disabled",
                run_id=blocked_run_id,
            )

        # 4. Phase 1 Transaction: Persist 'running' JevAIRun and COMMIT before external HTTP call
        run_uuid = uuid.uuid4()
        run_repo.create_run(
            run_id=run_uuid,
            mode=clean_mode,
            status="running",
            model_id=model_id,
            prompt_version=prompt_version,
            input_digest_sha256=initial_digest,
            context_summary=initial_summary,
            analysis_job_id=job_uuid,
            requested_by_user_id=persisted_user_id,
        )
        evidence_primary_copy = copy.deepcopy(evidence_primary)
        evidence_candidate_copy = (
            copy.deepcopy(evidence_candidate) if evidence_candidate is not None else None
        )
        session.commit()
        # Note: Immediately after session.commit(), no database transaction is open while
        # waiting on the external LM Studio HTTP call below.

        # 5. Phase 2: External LM Studio Orchestration (Zero Open DB Transactions)
        try:
            if question is not None and question.strip():
                stripped_q = question.strip()
                check_blind_data_in_text(stripped_q)
                check_prompt_injection(stripped_q)
                check_authority_claims(stripped_q)
                if _SUPPLEMENTAL_OVERRIDE_RE.search(stripped_q):
                    raise JevContextBlocked(
                        "Authority or detector verdict override claim detected in question"
                    )

            if clean_mode == "explain":
                workflow_result: ExplainResult | TriageResult | CompareResult | ReportResult = (
                    orchestrator.explain(evidence_primary_copy, question=question)
                )
            elif clean_mode == "triage":
                workflow_result = orchestrator.triage(evidence_primary_copy)
            elif clean_mode == "compare":
                workflow_result = orchestrator.compare(
                    evidence_primary_copy, evidence_candidate_copy
                )
            else:
                workflow_result = orchestrator.report(evidence_primary_copy)
        except Exception as exc:
            http_status, err_code, target_status = self._classify_runtime_exception(exc)
            safe_err_msg = (
                sanitize_error_message(str(exc)) or f"Jev AI execution failed ({err_code})"
            )
            try:
                run_repo.transition_run(
                    run_id=run_uuid,
                    status=target_status,
                    error_code=err_code,
                    error_message=safe_err_msg,
                )
                audit_repo.add(
                    AuditEvent(
                        request_id=job_request_id,
                        user_id=persisted_user_id,
                        event_type=f"jev_ai.run.{target_status}",
                        entity_type="jev_ai_run",
                        entity_id=str(run_uuid),
                        payload={
                            "run_id": str(run_uuid),
                            "mode": clean_mode,
                            "status": target_status,
                            "error_code": err_code,
                            "advisory_only": True,
                        },
                    )
                )
                session.commit()
            except SQLAlchemyError:
                session.rollback()

            raise JevAIServiceError(
                status_code=http_status,
                code=err_code,
                message=safe_err_msg,
                run_id=str(run_uuid),
            ) from exc

        # 6. Phase 3 Transaction: Persist 'completed' JevAIRun and AuditEvent
        decision_dict, primary_text = _extract_workflow_payload(clean_mode, workflow_result)
        final_summary: dict[str, Any] = dict(initial_summary)
        if settings.jev_ai_store_context_summary:
            final_summary["decision_result"] = decision_dict
        else:
            final_summary = {
                "workflow": clean_mode,
                "advisory_only": True,
                "retention_redacted": True,
                "baseline_id": initial_summary.get("baseline_id"),
                "candidate_id": initial_summary.get("candidate_id"),
                "decision_result": {
                    "workflow": clean_mode,
                    "advisory_only": True,
                    "baseline_id": initial_summary.get("baseline_id"),
                    "candidate_id": initial_summary.get("candidate_id"),
                },
            }

        persisted_text = primary_text if settings.jev_ai_store_response_text else None

        try:
            completed_run = run_repo.transition_run(
                run_id=run_uuid,
                status="completed",
                output_digest_sha256=workflow_result.output_digest,
                response_text=persisted_text,
                latency_ms=workflow_result.latency_ms,
                context_summary=final_summary,
                model_id=workflow_result.model_id,
                prompt_version=workflow_result.prompt_version,
            )
            audit_repo.add(
                AuditEvent(
                    request_id=job_request_id,
                    user_id=persisted_user_id,
                    event_type="jev_ai.run.completed",
                    entity_type="jev_ai_run",
                    entity_id=str(run_uuid),
                    payload={
                        "run_id": str(run_uuid),
                        "mode": clean_mode,
                        "status": "completed",
                        "input_digest_sha256": completed_run.input_digest_sha256,
                        "output_digest_sha256": completed_run.output_digest_sha256,
                        "advisory_only": True,
                    },
                )
            )
            session.commit()
            return completed_run
        except (SQLAlchemyError, JevAIRepositoryError) as exc:
            session.rollback()
            raise JevAIServiceError(
                status_code=500,
                code="XS_AI_PERSISTENCE_FAILED",
                message="Failed to persist completed Jev AI audit record; transaction rolled back",
                run_id=str(run_uuid),
            ) from exc

    @staticmethod
    def _classify_runtime_exception(exc: Exception) -> tuple[int, str, str]:
        failure = classify_jev_failure(exc)
        return failure.http_status, failure.error_code, failure.db_status

    def get_run(
        self,
        session: Session,
        run_id: str,
        *,
        user: AuthUser | None = None,
    ) -> JevAIRun:
        try:
            parsed_uuid = uuid.UUID(str(run_id))
        except (ValueError, TypeError) as exc:
            raise JevAIServiceError(
                status_code=404,
                code="XS_AI_RUN_NOT_FOUND",
                message=f"Jev AI run '{run_id}' was not found",
            ) from exc

        repo = JevAIRunRepository(session)
        run = repo.get_by_id(parsed_uuid)
        if run is None:
            raise JevAIServiceError(
                status_code=404,
                code="XS_AI_RUN_NOT_FOUND",
                message=f"Jev AI run '{run_id}' was not found",
            )

        _check_run_ownership(run, user, session=session)
        return run

    def list_runs(
        self,
        session: Session,
        *,
        analysis_id: str | None = None,
        mode: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        user: AuthUser | None = None,
    ) -> tuple[list[JevAIRun], int]:
        analysis_job_uuid: uuid.UUID | None = None
        if analysis_id is not None and analysis_id.strip():
            job = _resolve_analysis_job(session, analysis_id.strip())
            _check_job_ownership(job, user)
            analysis_job_uuid = job.id

        owner_filter: uuid.UUID | None = None
        if not _is_admin(user) and user is not None:
            owner_filter = user.user_id

        repo = JevAIRunRepository(session)
        return repo.list_runs(
            analysis_job_id=analysis_job_uuid,
            requested_by_user_id=owner_filter,
            mode=mode,
            status=status,
            limit=limit,
            offset=offset,
        )

    def submit_feedback(
        self,
        session: Session,
        *,
        run_id: str,
        rating: int | None = None,
        label: str | None = None,
        comment: str | None = None,
        user: AuthUser | None = None,
    ) -> JevAIFeedback:
        run = self.get_run(session, run_id, user=user)
        persisted_user_id = ensure_persisted_user(session, user)

        fb_repo = JevAIFeedbackRepository(session)
        audit_repo = AuditEventRepository(session)
        try:
            feedback = fb_repo.create_feedback(
                jev_ai_run_id=run.id,
                user_id=persisted_user_id,
                rating=rating,
                label=label,
                comment=comment,
            )
            audit_repo.add(
                AuditEvent(
                    request_id=str(run.id),
                    user_id=persisted_user_id,
                    event_type="jev_ai.feedback.recorded",
                    entity_type="jev_ai_feedback",
                    entity_id=str(feedback.id),
                    payload={
                        "feedback_id": str(feedback.id),
                        "jev_ai_run_id": str(run.id),
                        "rating": feedback.rating,
                        "label": feedback.label,
                        "advisory_only": True,
                    },
                )
            )
            session.commit()
            return feedback
        except DuplicateFeedbackError as exc:
            session.rollback()
            raise JevAIServiceError(
                status_code=409,
                code="XS_DUPLICATE_FEEDBACK",
                message=exc.message,
                run_id=str(run.id),
            ) from exc
        except JevAIRepositoryError as exc:
            session.rollback()
            status_map = {
                "XS_AI_RUN_NOT_FOUND": 404,
                "XS_AI_RUN_NOT_TERMINAL": 409,
                "XS_FEEDBACK_INVALID": 422,
            }
            raise JevAIServiceError(
                status_code=status_map.get(exc.code, 422),
                code=exc.code,
                message=exc.message,
                run_id=str(run.id),
            ) from exc
        except SQLAlchemyError as exc:
            session.rollback()
            raise JevAIServiceError(
                status_code=500,
                code="XS_AI_PERSISTENCE_FAILED",
                message="Failed to persist analyst feedback; transaction rolled back",
                run_id=str(run.id),
            ) from exc

    def list_feedback(
        self,
        session: Session,
        *,
        run_id: str,
        user: AuthUser | None = None,
    ) -> tuple[JevAIRun, list[JevAIFeedback]]:
        run = self.get_run(session, run_id, user=user)
        fb_repo = JevAIFeedbackRepository(session)
        return run, fb_repo.list_for_run(run.id)
