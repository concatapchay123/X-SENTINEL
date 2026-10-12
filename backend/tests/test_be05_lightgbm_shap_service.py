from __future__ import annotations

import concurrent.futures
import math
from pathlib import Path
from typing import Any

import pytest
from x_sentinel.data.schema import (
    FEATURE_COUNT,
    DimensionMismatchError,
    InvalidDataTypeError,
    NonFiniteValueError,
    StructuralShapeError,
)
from x_sentinel.detection.m1_tadr import m1_tadr
from x_sentinel.model.demo import DemoModelService
from x_sentinel.model.lightgbm_service import (
    LightGBMService,
    ModelArtifactNotFoundError,
    ModelCompatibilityError,
    ModelConfigUnresolvedError,
    ModelInferenceResult,
    ModelIntegrityError,
    ModelMetadata,
    clear_model_cache,
    compute_artifact_sha256,
    load_model_service,
)
from x_sentinel.model.shap_service import SHAPExplanation, SHAPService
from x_sentinel.services.analysis_service import AnalysisService

# Known approved EMBER 2018 LightGBM artifact
EMBER_MODEL_PATH = Path("datasets/ember2018/ember_model_2018.txt")
EMBER_MODEL_SHA256 = "509de4a83e2d76b69fb3025ced0429e5f40f6a95ca40122b9eedd03317fff5e2"


# ---------------------------------------------------------------------------
# Task 5.1 & 5.2 — Model Loading, Identity & Artifact Integrity Tests
# ---------------------------------------------------------------------------


def test_compute_artifact_sha256_matches_canonical():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    computed_hash = compute_artifact_sha256(EMBER_MODEL_PATH)
    assert computed_hash == EMBER_MODEL_SHA256


def test_compute_artifact_sha256_missing_file_raises(tmp_path: Path):
    missing_file = tmp_path / "does_not_exist.bin"
    with pytest.raises(ModelArtifactNotFoundError, match="Model artifact file does not exist"):
        compute_artifact_sha256(missing_file)


def test_load_valid_approved_lightgbm_model():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(
        model_path=EMBER_MODEL_PATH,
        expected_sha256=EMBER_MODEL_SHA256,
        version="ember2018-v1",
    )
    assert service.actual_sha256 == EMBER_MODEL_SHA256
    assert service.expected_sha256 == EMBER_MODEL_SHA256
    assert service.version == "ember2018-v1"
    assert service.feature_count == FEATURE_COUNT
    assert service.num_trees == 1000
    assert not service.demo_mode
    assert service.status == "SCIENTIFIC_APPROVED"

    meta = service.metadata
    assert isinstance(meta, ModelMetadata)
    assert meta.version == "ember2018-v1"
    assert meta.status == "SCIENTIFIC_APPROVED"
    assert meta.adapter == "lightgbm"
    assert meta.artifact_sha256 == EMBER_MODEL_SHA256
    assert meta.feature_count == FEATURE_COUNT
    assert meta.num_trees == 1000
    assert meta.objective == "binary sigmoid:1"


def test_load_missing_artifact_raises_not_found(tmp_path: Path):
    missing_path = tmp_path / "non_existent_model.txt"
    with pytest.raises(ModelArtifactNotFoundError, match="Model artifact file does not exist"):
        LightGBMService(model_path=missing_path, expected_sha256="abc123")


def test_load_corrupted_or_invalid_artifact_format(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt_model.txt"
    corrupt_file.write_text("THIS IS NOT A VALID LIGHTGBM MODEL FILE", encoding="utf-8")
    actual_hash = compute_artifact_sha256(corrupt_file)
    with pytest.raises(ModelIntegrityError, match="Failed to load LightGBM model"):
        LightGBMService(model_path=corrupt_file, expected_sha256=actual_hash)


def test_checksum_mismatch_raises_integrity_error():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    with pytest.raises(ModelIntegrityError, match="Artifact checksum mismatch"):
        LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=wrong_hash)


def test_dimension_mismatch_raises_compatibility_error(tmp_path: Path):
    import lightgbm as lgb
    import numpy as np

    X = np.random.randn(20, 10).astype(np.float32)
    y = np.random.randint(0, 2, size=20)
    ds = lgb.Dataset(X, label=y, free_raw_data=False)
    booster = lgb.train({"objective": "binary", "verbosity": -1}, ds, num_boost_round=2)
    dummy_model_path = tmp_path / "dummy_10_features.txt"
    booster.save_model(str(dummy_model_path))

    dummy_hash = compute_artifact_sha256(dummy_model_path)
    with pytest.raises(ModelCompatibilityError, match="expected 2381, got 10"):
        LightGBMService(
            model_path=dummy_model_path,
            expected_sha256=dummy_hash,
            feature_count=FEATURE_COUNT,
        )


def test_loader_scientific_config_fails_closed_due_to_oq02():
    with pytest.raises(ModelConfigUnresolvedError, match="unresolved pending freeze of OQ-02"):
        load_model_service("configs/model.scientific.yaml", allow_demo=False)


def test_loader_demo_config_rejected_when_demo_disallowed():
    with pytest.raises(ModelIntegrityError, match="Demo model adapter is not permitted"):
        load_model_service("configs/model.demo.yaml", allow_demo=False)


def test_loader_demo_config_returns_demo_service():
    service = load_model_service("configs/model.demo.yaml", allow_demo=True)
    assert isinstance(service, DemoModelService)
    assert service.demo_mode is True


def test_loader_frozen_candidate_loads_lightgbm_service():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    config = {
        "status": "FROZEN_CANDIDATE",
        "adapter": "lightgbm",
        "version": "ember2018-v1",
        "model_path": str(EMBER_MODEL_PATH),
        "model_sha256": EMBER_MODEL_SHA256,
        "feature_count": 2381,
    }
    service = load_model_service(config, allow_demo=False)
    assert isinstance(service, LightGBMService)
    assert service.actual_sha256 == EMBER_MODEL_SHA256


def test_loader_from_file_frozen_candidate():
    config_file = Path("configs/model.ember2018.yaml")
    if not config_file.exists() or not EMBER_MODEL_PATH.exists():
        pytest.skip("ember2018 model or config not found")
    service = load_model_service(config_file, allow_demo=False)
    assert isinstance(service, LightGBMService)
    assert service.version == "ember2018-v1"


def test_loader_caching_behavior():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    clear_model_cache()
    config = {
        "status": "FROZEN_CANDIDATE",
        "adapter": "lightgbm",
        "version": "ember2018-v1",
        "model_path": str(EMBER_MODEL_PATH),
        "model_sha256": EMBER_MODEL_SHA256,
        "feature_count": 2381,
    }
    svc1 = load_model_service(config, allow_demo=False, model_cache=True)
    svc2 = load_model_service(config, allow_demo=False, model_cache=True)
    assert svc1 is svc2  # exact same cached instance

    clear_model_cache()
    svc3 = load_model_service(config, allow_demo=False, model_cache=True)
    assert svc3 is not svc1  # freshly reloaded instance after cache clear


def test_loader_invalid_inputs_raise():
    with pytest.raises(ValueError, match="config_source must be provided"):
        load_model_service(None)

    with pytest.raises(FileNotFoundError, match="Model configuration file not found"):
        load_model_service("non_existent_config.yaml")

    with pytest.raises(TypeError, match="Unsupported config_source type"):
        load_model_service(12345)  # type: ignore

    with pytest.raises(ValueError, match="Unsupported model adapter"):
        load_model_service(
            {
                "status": "READY",
                "adapter": "unknown_ai_adapter",
                "model_path": "path.bin",
                "model_sha256": "123",
            }
        )


# ---------------------------------------------------------------------------
# Task 5.3 — LightGBM Inference Service Tests
# ---------------------------------------------------------------------------


def test_inference_valid_vector():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    vector = [0.0] * FEATURE_COUNT
    res = service.infer(vector)

    assert isinstance(res, ModelInferenceResult)
    assert 0.0 <= res.score <= 1.0
    assert len(res.shap_values) == FEATURE_COUNT
    assert res.model_version == "ember2018-v1"
    assert res.artifact_sha256 == EMBER_MODEL_SHA256
    assert not res.demo_mode
    assert len(res.warnings) == 0

    # Test unpacking compatibility with AnalysisService: `score, shap = service.infer(vector)`
    score, shap = res
    assert score == res.score
    assert shap == res.shap_values


def test_inference_rejects_invalid_vector_shape():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    with pytest.raises(DimensionMismatchError, match="expected 2381 features"):
        service.infer([0.0] * 100)
    with pytest.raises(DimensionMismatchError, match="expected 2381 features"):
        service.infer([0.0] * 2382)


def test_inference_rejects_non_finite_values():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    bad_vector = [0.0] * FEATURE_COUNT
    bad_vector[42] = float("nan")
    with pytest.raises(NonFiniteValueError, match="feature\\[42\\] is NaN"):
        service.infer(bad_vector)

    bad_vector[42] = float("inf")
    with pytest.raises(NonFiniteValueError, match="feature\\[42\\] is infinite"):
        service.infer(bad_vector)

    bad_vector[42] = float("-inf")
    with pytest.raises(NonFiniteValueError, match="feature\\[42\\] is infinite"):
        service.infer(bad_vector)


def test_inference_rejects_invalid_types():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)

    with pytest.raises(StructuralShapeError, match="vector input is None"):
        service.infer(None)  # type: ignore

    with pytest.raises(StructuralShapeError, match="not a valid vector sequence"):
        service.infer("not a sequence")  # type: ignore

    bad_vector: list[Any] = [0.0] * FEATURE_COUNT
    bad_vector[10] = True
    with pytest.raises(InvalidDataTypeError, match="is a boolean"):
        service.infer(bad_vector)

    bad_vector[10] = "string_value"
    with pytest.raises(InvalidDataTypeError, match="is a string"):
        service.infer(bad_vector)


def test_inference_determinism():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    vector = [float(i * 0.01) for i in range(FEATURE_COUNT)]

    res1 = service.infer(vector)
    res2 = service.infer(vector)

    assert res1.score == res2.score
    assert res1.raw_score == res2.raw_score
    assert res1.base_value == res2.base_value
    assert res1.shap_values == res2.shap_values


def test_inference_batch():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    v1 = [0.0] * FEATURE_COUNT
    v2 = [1.0] * FEATURE_COUNT
    batch_res = service.infer_batch([v1, v2])

    assert len(batch_res) == 2
    assert batch_res[0].score == service.infer(v1).score
    assert batch_res[1].score == service.infer(v2).score
    assert batch_res[0].shap_values == service.infer(v1).shap_values
    assert batch_res[1].shap_values == service.infer(v2).shap_values

    # Empty batch returns empty list
    assert service.infer_batch([]) == []


# ---------------------------------------------------------------------------
# Task 5.4 — Local SHAP Explainability Tests
# ---------------------------------------------------------------------------


def test_shap_explanation_shape_and_alignment():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    vector = [0.0] * FEATURE_COUNT
    res = service.infer(vector)

    assert res.explanation is not None
    assert isinstance(res.explanation, SHAPExplanation)
    assert len(res.explanation) == FEATURE_COUNT
    assert len(res.explanation.values) == FEATURE_COUNT
    assert isinstance(res.explanation.base_value, float)

    # Sequence protocol test: indexing and slicing
    assert isinstance(res.explanation[0], float)
    assert len(res.explanation[0:255]) == 255
    assert list(res.explanation) == res.shap_values

    # Dict conversion
    d = res.explanation.to_dict()
    assert d["feature_count"] == FEATURE_COUNT
    assert len(d["values"]) == FEATURE_COUNT


def test_shap_additivity():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    vector = [0.5] * FEATURE_COUNT
    res = service.infer(vector)

    assert res.explanation is not None
    assert res.explanation.check_additivity(tolerance=1e-4)

    # Direct mathematical verification: sum(shap) + base_value == raw_score
    shap_sum = sum(res.shap_values)
    expected_margin = shap_sum + res.base_value
    assert math.isclose(expected_margin, res.raw_score, rel_tol=1e-5, abs_tol=1e-5)

    # Sigmoid link check: score == 1 / (1 + exp(-raw_score))
    expected_prob = 1.0 / (1.0 + math.exp(-res.raw_score))
    assert math.isclose(expected_prob, res.score, rel_tol=1e-5, abs_tol=1e-5)


def test_shap_base_value_is_constant_across_samples():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    v1 = [0.0] * FEATURE_COUNT
    v2 = [1.0] * FEATURE_COUNT
    v3 = [-0.5] * FEATURE_COUNT

    res1 = service.infer(v1)
    res2 = service.infer(v2)
    res3 = service.infer(v3)

    assert math.isclose(res1.base_value, res2.base_value, rel_tol=1e-7)
    assert math.isclose(res1.base_value, res3.base_value, rel_tol=1e-7)


def test_shap_service_direct_batch_and_error_handling():
    shap_svc = SHAPService(feature_count=FEATURE_COUNT)
    assert shap_svc.explain_batch(None, []) == []

    with pytest.raises(TypeError, match="does not support SHAP predict method"):
        shap_svc.explain(object(), [0.0] * FEATURE_COUNT)

    with pytest.raises(TypeError, match="does not support SHAP predict method"):
        shap_svc.explain_batch(object(), [[0.0] * FEATURE_COUNT])


# ---------------------------------------------------------------------------
# Task 5.5 — Demo Mode & Scientific Mode Separation Tests
# ---------------------------------------------------------------------------


def test_demo_mode_output_distinctly_marked():
    demo_service = DemoModelService()
    vector = [1.0] * FEATURE_COUNT
    res = demo_service.infer(vector)

    assert res.demo_mode is True
    assert res.status == "DEMO_ONLY"
    assert "DEMO_MODE_NOT_SCIENTIFIC_EVIDENCE" in res.warnings
    assert res.artifact_sha256 == "DEMO_MOCK_NO_ARTIFACT"

    # Backward compatible unpacking
    score, shap = res
    assert 0.0 <= score <= 1.0
    assert len(shap) == FEATURE_COUNT

    # Batch demo
    batch = demo_service.infer_batch([vector, vector])
    assert len(batch) == 2
    assert batch[0].demo_mode is True


def test_scientific_service_rejects_demo_mode():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    assert service.demo_mode is False
    res = service.infer([0.0] * FEATURE_COUNT)
    assert res.demo_mode is False
    assert res.status == "SCIENTIFIC_APPROVED"
    assert "DEMO_MODE_NOT_SCIENTIFIC_EVIDENCE" not in res.warnings


def test_no_silent_fallback_when_artifact_tampered(tmp_path: Path):
    # If artifact is corrupted or tampered, it must fail closed and NOT fallback to demo
    fake_model = tmp_path / "tampered_model.txt"
    fake_model.write_text("corrupted content", encoding="utf-8")
    with pytest.raises(ModelIntegrityError):
        load_model_service(
            {
                "status": "FROZEN_CANDIDATE",
                "adapter": "lightgbm",
                "model_path": str(fake_model),
                "model_sha256": "wrong_hash",
            },
            # even with allow_demo=True, scientific config error must not fallback to demo
            allow_demo=True,
        )



# ---------------------------------------------------------------------------
# Task 5.6 & 5.7 — Downstream Integration & Concurrency Tests
# ---------------------------------------------------------------------------


def test_integration_with_m1_tadr():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    vector = [0.1 * i for i in range(FEATURE_COUNT)]
    _, shap = service.infer(vector)

    tadr = m1_tadr(shap)
    assert isinstance(tadr, float)
    assert 0.0 <= tadr <= 1.0


def test_integration_with_analysis_service():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)

    # In demo mode, AnalysisService can accept the LightGBMService directly
    analysis_svc = AnalysisService(
        audit_path=Path("artifacts/audit/test_events.jsonl"),
        view_map_path=Path("configs/views.demo.yaml"),
        demo_mode=True,
        model_service=service,
    )
    vector = [0.0] * FEATURE_COUNT
    result = analysis_svc.analyze_vector(vector)
    assert result.status == "DEMO_ONLY"
    assert 0.0 <= result.malware_score <= 1.0
    assert "m1" in result.signals
    assert "m3" in result.signals


def test_concurrent_inference_thread_safety():
    if not EMBER_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {EMBER_MODEL_PATH}")
    service = LightGBMService(model_path=EMBER_MODEL_PATH, expected_sha256=EMBER_MODEL_SHA256)
    vector = [0.0] * FEATURE_COUNT

    def run_inference():
        res = service.infer(vector)
        return res.score, res.raw_score, res.shap_values[:5]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(run_inference) for _ in range(12)]
        results = [f.result() for f in futures]

    first_score, first_raw, first_shap = results[0]
    for sc, raw, sh in results[1:]:
        assert sc == first_score
        assert raw == first_raw
        assert sh == first_shap
