from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import httpx
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session
from x_sentinel.audit.evidence import CanonicalEvidence


class DatabaseFaultInjector:
    """Deterministic fault injector for SQLAlchemy database sessions and engines."""

    @staticmethod
    @contextmanager
    def fail_on_commit(
        session: Session,
        exception: Exception | None = None,
    ) -> Generator[MagicMock, None, None]:
        """Intercepts session.commit and raises an error, verifying fail-closed rollback."""
        exc = exception or OperationalError(
            statement="COMMIT TRANSACTION",
            params={},
            orig=Exception("Simulated SQL Server connection drop during commit"),
        )
        orig_commit = session.commit
        mock_commit = MagicMock(side_effect=exc)
        session.commit = mock_commit  # type: ignore[method-assign]
        try:
            yield mock_commit
        finally:
            session.commit = orig_commit  # type: ignore[method-assign]

    @staticmethod
    @contextmanager
    def fail_on_flush(
        session: Session,
        exception: Exception | None = None,
    ) -> Generator[MagicMock, None, None]:
        """Intercepts session.flush and raises an error."""
        exc = exception or SQLAlchemyError("Simulated flush constraint violation")
        orig_flush = session.flush
        mock_flush = MagicMock(side_effect=exc)
        session.flush = mock_flush  # type: ignore[method-assign]
        try:
            yield mock_flush
        finally:
            session.flush = orig_flush  # type: ignore[method-assign]


class ModelFaultInjector:
    """Deterministic fault injector for LightGBM and SHAP model services."""

    @staticmethod
    @contextmanager
    def fail_on_infer(
        model_service: Any,
        exception: Exception | None = None,
    ) -> Generator[MagicMock, None, None]:
        """Intercepts model_service.infer to simulate model crashes or memory exhaustion."""
        exc = exception or RuntimeError("Simulated Booster inference failure: SIGSEGV in C++ core")
        orig_infer = model_service.infer
        mock_infer = MagicMock(side_effect=exc)
        model_service.infer = mock_infer
        try:
            yield mock_infer
        finally:
            model_service.infer = orig_infer

    @staticmethod
    @contextmanager
    def inject_nan_prediction(
        model_service: Any,
    ) -> Generator[MagicMock, None, None]:
        """Forces model_service.infer to return NaN or non-finite values."""
        orig_infer = model_service.infer
        mock_infer = MagicMock(return_value=(float("nan"), [float("nan")] * 2381))
        model_service.infer = mock_infer
        try:
            yield mock_infer
        finally:
            model_service.infer = orig_infer


class AuditFaultInjector:
    """Deterministic fault injector for append-only audit log writers."""

    @staticmethod
    @contextmanager
    def fail_on_write(
        writer: Any,
        exception: Exception | None = None,
    ) -> Generator[MagicMock, None, None]:
        """Forces writer.append to fail, simulating disk full (ENOSPC) or permissions drop."""
        from x_sentinel.audit.writer import AuditWriteFailureError

        exc = exception or AuditWriteFailureError(
            "Simulated POSIX/Windows IO write failure: [Errno 28] No space left on device"
        )
        orig_append = writer.append
        mock_append = MagicMock(side_effect=exc)
        writer.append = mock_append
        try:
            yield mock_append
        finally:
            writer.append = orig_append


class TransportFaultInjector:
    """Deterministic HTTP transport fault simulation for Jev AI / LM Studio calls."""

    @staticmethod
    def timeout_transport() -> httpx.MockTransport:
        """Transport that raises ConnectTimeout or ReadTimeout."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Simulated LM Studio inference read timeout after 30.0s", request=request)
        return httpx.MockTransport(handler)

    @staticmethod
    def connection_refused_transport() -> httpx.MockTransport:
        """Transport that simulates LM Studio server offline (connection refused)."""
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Simulated ConnectionRefusedError: [Errno 111] Connection refused", request=request)
        return httpx.MockTransport(handler)

    @staticmethod
    def http_error_transport(status_code: int = 502, message: str = "Bad Gateway") -> httpx.MockTransport:
        """Transport that returns an upstream HTTP error status."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=status_code,
                content=json.dumps({"error": {"message": message, "code": status_code}}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
        return httpx.MockTransport(handler)

    @staticmethod
    def malformed_json_transport() -> httpx.MockTransport:
        """Transport that returns corrupted/truncated JSON bytes."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                content=b'{"choices": [{"message": {"content": "Incomplete text... ',
                headers={"Content-Type": "application/json"},
            )
        return httpx.MockTransport(handler)

    @staticmethod
    def missing_logprobs_transport() -> httpx.MockTransport:
        """Transport for decision model missing required logprobs object."""
        def handler(request: httpx.Request) -> httpx.Response:
            payload = {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "A"},
                        "finish_reason": "stop",
                        # Intentionally missing "logprobs"
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 1, "total_tokens": 101},
            }
            return httpx.Response(
                status_code=200,
                content=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
        return httpx.MockTransport(handler)

    @staticmethod
    def incomplete_options_transport() -> httpx.MockTransport:
        """Transport with logprobs missing expected candidate tokens."""
        def handler(request: httpx.Request) -> httpx.Response:
            payload = {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "YES"},
                        "finish_reason": "stop",
                        "logprobs": {
                            "content": [
                                {
                                    "token": "YES",
                                    "logprob": -0.05,
                                    "top_logprobs": [
                                        # Only "YES" present, "NO" missing completely
                                        {"token": "YES", "logprob": -0.05}
                                    ],
                                }
                            ]
                        },
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 1, "total_tokens": 101},
            }
            return httpx.Response(
                status_code=200,
                content=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
        return httpx.MockTransport(handler)


class EvidenceTamperInjector:
    """Helper for tampering canonical evidence objects to test tamper-detection gates."""

    @staticmethod
    def tamper_hash(evidence: CanonicalEvidence) -> CanonicalEvidence:
        """Corrupts the cryptographic SHA-256 evidence hash."""
        tampered_dict = evidence.to_dict()
        tampered_dict["evidence_hash"] = "0" * 64
        return CanonicalEvidence.from_dict(tampered_dict)

    @staticmethod
    def tamper_detector_verdict(evidence: CanonicalEvidence, new_verdict: str = "PASS") -> CanonicalEvidence:
        """Alters the canonical decision inside the payload without updating the hash."""
        tampered_dict = evidence.to_dict()
        tampered_dict["decision"] = new_verdict
        # Keep original evidence_hash to cause integrity mismatch
        return CanonicalEvidence.from_dict(tampered_dict)
