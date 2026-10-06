from __future__ import annotations

import pytest

from x_sentinel.jev_ai.guardrails import JevContextBlocked, validate_context, validate_local_endpoint
from x_sentinel.jev_ai.prompt_builder import build_messages
from x_sentinel.jev_ai.schemas import JevContext, JevRequest


def test_jev_context_accepts_minimized_detector_evidence() -> None:
    req = JevRequest(context=JevContext(decision="alert", detector_scores={"M1": 0.4}))
    messages, digest = build_messages(req)
    assert messages[0]["role"] == "system"
    assert len(digest) == 64


def test_jev_context_blocks_blind_ground_truth() -> None:
    with pytest.raises(JevContextBlocked):
        validate_context({"ground_truth": "poisoned"})


def test_jev_context_blocks_raw_pe() -> None:
    with pytest.raises(JevContextBlocked):
        validate_context({"nested": {"raw_pe": "MZ..."}})


def test_jev_endpoint_must_be_local() -> None:
    validate_local_endpoint("http://localhost:1234/v1")
    with pytest.raises(JevContextBlocked):
        validate_local_endpoint("https://example.com/v1")
