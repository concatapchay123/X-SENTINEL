from __future__ import annotations

import concurrent.futures
import time
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from x_sentinel.audit.evidence import CanonicalEvidence
from x_sentinel.database.models import Base
from x_sentinel.database.repositories.evidence import CanonicalEvidenceRepository
from x_sentinel.jev_ai.client import JevAIConnectionError, JevAITimeout
from x_sentinel.services.jev_ai_service import JevAIService, JevAIServiceError

from infrastructure.monitoring.percentiles import BenchmarkSummary


@pytest.fixture
def mock_db_session():
    engine = create_engine("sqlite:///:memory:")
    # Normalize T-SQL N'...' server_defaults and SQLite BigInteger autoincrement
    for col in Base.metadata.tables["audit_events"].columns:
        if col.name == "id":
            from sqlalchemy import Integer
            col.type = Integer()
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.server_default is not None:
                text_str = str(col.server_default.arg)
                if "N'" in text_str:
                    col.server_default.arg.text = text_str.replace("N'", "'")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def sample_canonical_evidence(mock_db_session) -> CanonicalEvidence:
    ev = CanonicalEvidence(
        request_id="req-ai-load-test-001",
        run_id="run-ai-load-test-001",
        timestamp="2026-10-13T10:00:00+00:00",
        code_commit="git_commit_hash_v3_canonical_0002",
        build_digest="sha256:build_digest_x_sentinel_v3_baseline",
        input_id="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        input_mode="vector",
        view_map_hash="276be235642b655efab3b8e2bd26af0dde4617ccac0d4d63195c636ee408b5cb",
        model_hash="509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2",
        model_config_hash="a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
        detector_config_hash="b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123a1",
        seed=42,
        malware_score=0.88,
        signals={"m1": 0.45, "m2": 0.1, "m3": 0.65, "m4": 0.0, "m5": 0.0},
        fusion_score=0.72,
        threshold_id="THRESH-V3-DEFAULT",
        decision="QUARANTINE",
        latency_ms={"end_to_end": 4.5, "model": 2.1, "signals": 1.2, "fusion": 0.4},
        demo_mode=False,
    ).with_hash()

    repo = CanonicalEvidenceRepository(mock_db_session)
    repo.persist(evidence=ev, auto_commit=True)
    return ev


class TestAITimeoutScenarios:
    def test_connect_timeout_classification_and_isolation(
        self, mock_db_session, sample_canonical_evidence
    ) -> None:
        service = JevAIService()
        mock_orchestrator = MagicMock()
        mock_orchestrator._client_model_id.return_value = "jev-local-test"
        mock_orchestrator._client_prompt_version.return_value = "jev-v3.0.0"
        mock_orchestrator.client.enabled = True
        mock_orchestrator.max_context_chars = 30000

        mock_orchestrator.explain.side_effect = JevAITimeout(
            "Connection timeout after 2.0s", timeout_type="connect", timeout_seconds=2.0
        )

        with pytest.raises(JevAIServiceError) as exc_info:
            service.execute_workflow(
                session=mock_db_session,
                orchestrator=mock_orchestrator,
                analysis_id=sample_canonical_evidence.request_id,
                mode="explain",
            )

        assert exc_info.value.status_code == 504
        assert exc_info.value.code == "XS_AI_TIMEOUT"

        # Verify detector evidence remained 100% untouched and authoritative
        repo = CanonicalEvidenceRepository(mock_db_session)
        evidence = repo.get_canonical_evidence(sample_canonical_evidence.request_id)
        assert evidence is not None
        assert evidence.decision == "QUARANTINE"
        assert evidence.evidence_hash == sample_canonical_evidence.evidence_hash

        # Verify failed/timed-out latency was observed in Prometheus and persisted in DB
        import uuid

        from sqlalchemy import select
        from x_sentinel.database.models import JevAIRun

        from infrastructure.monitoring.metrics import get_metrics_registry

        reg = get_metrics_registry()
        hist_summary = reg.histogram("jev_latency_ms").get_summary()
        assert hist_summary["count"] > 0, "Failed timeout request must be observed in jev_latency_ms histogram"

        run_id_val = uuid.UUID(exc_info.value.run_id)
        failed_run = mock_db_session.scalar(select(JevAIRun).where(JevAIRun.id == run_id_val))
        assert failed_run is not None
        assert failed_run.latency_ms is not None and failed_run.latency_ms >= 0.0
        assert failed_run.status == "failed"
        assert failed_run.error_code == "XS_AI_TIMEOUT"

    def test_read_timeout_classification(
        self, mock_db_session, sample_canonical_evidence
    ) -> None:
        service = JevAIService()
        mock_orchestrator = MagicMock()
        mock_orchestrator._client_model_id.return_value = "jev-local-test"
        mock_orchestrator._client_prompt_version.return_value = "jev-v3.0.0"
        mock_orchestrator.client.enabled = True
        mock_orchestrator.max_context_chars = 30000

        mock_orchestrator.explain.side_effect = JevAITimeout(
            "Read timeout after 60.0s", timeout_type="read", timeout_seconds=60.0
        )

        with pytest.raises(JevAIServiceError) as exc_info:
            service.execute_workflow(
                session=mock_db_session,
                orchestrator=mock_orchestrator,
                analysis_id=sample_canonical_evidence.request_id,
                mode="explain",
            )

        assert exc_info.value.status_code == 504
        assert exc_info.value.code == "XS_AI_TIMEOUT"

    def test_runtime_connection_refused_classification(
        self, mock_db_session, sample_canonical_evidence
    ) -> None:
        service = JevAIService()
        mock_orchestrator = MagicMock()
        mock_orchestrator._client_model_id.return_value = "jev-local-test"
        mock_orchestrator._client_prompt_version.return_value = "jev-v3.0.0"
        mock_orchestrator.client.enabled = True
        mock_orchestrator.max_context_chars = 30000

        mock_orchestrator.explain.side_effect = JevAIConnectionError(
            "Failed to connect to LM Studio: connection refused"
        )

        with pytest.raises(JevAIServiceError) as exc_info:
            service.execute_workflow(
                session=mock_db_session,
                orchestrator=mock_orchestrator,
                analysis_id=sample_canonical_evidence.request_id,
                mode="explain",
            )

        assert exc_info.value.status_code == 503
        assert exc_info.value.code == "XS_AI_UNAVAILABLE"


class TestAILoadBenchmarking:
    def test_mock_load_benchmark_latency_and_throughput(self) -> None:
        """Simulate high-throughput concurrent load against mock advisory runtime."""
        num_requests = 30
        concurrency = 4
        latencies: list[float] = []
        failures = 0

        def run_mock_inference(req_id: int) -> float:
            start = time.perf_counter()
            # Simulate mocked token extraction + guardrail overhead (approx 15ms)
            time.sleep(0.015)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return elapsed_ms

        start_all = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(run_mock_inference, i) for i in range(num_requests)]
            for f in concurrent.futures.as_completed(futures):
                try:
                    lat = f.result()
                    latencies.append(lat)
                except Exception:
                    failures += 1
        total_duration = time.perf_counter() - start_all

        summary = BenchmarkSummary.from_samples(
            latencies,
            component="jev_ai_mock",
            workload="simulated_decision_tokens",
            warmup_count=3,
            failures=failures,
            total_test_duration_s=total_duration,
        )

        assert summary.sample_count == num_requests
        assert summary.failure_count == 0
        assert summary.p50_ms > 10.0
        assert summary.p95_ms > 10.0
        assert summary.throughput_ops_per_sec > 50.0  # Concurrency boosts throughput
        assert summary.error_rate == 0.0
