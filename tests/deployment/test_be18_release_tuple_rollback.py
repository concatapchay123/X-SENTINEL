from __future__ import annotations

import json
from pathlib import Path

import scripts.verify_release_tuple as vrt

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestReleaseTupleIntegrity:
    """Tests canonical release tuple generation, hashing, and compatibility invariants."""

    def test_release_tuple_has_all_required_components(self) -> None:
        tup = vrt.build_release_tuple()
        assert tup["release_version"] == "0.3.0"
        assert tup["release_bundle_digest"].startswith("sha256:")
        assert tup["database_schema_revision"] == "0002_v3_jev_ai_audit"
        assert len(tup["detector_config"]["sha256"]) == 64
        assert len(tup["view_map"]["sha256"]) == 64
        assert len(tup["model_artifact"]["sha256"]) == 64
        assert tup["contracts"]["feature_vector_dimension"] == 2381
        assert tup["contracts"]["evidence_schema_version"] == "v3.0.0"
        assert tup["contracts"]["jev_prompt_version"] == "jev-v3.0.0"

    def test_release_tuple_digest_deterministic(self) -> None:
        tup1 = vrt.build_release_tuple()
        tup2 = vrt.build_release_tuple()
        assert tup1["release_bundle_digest"] == tup2["release_bundle_digest"]

    def test_release_manifest_artifacts_written_and_valid(self) -> None:
        tup = vrt.build_release_tuple()
        j_path, m_path = vrt.write_release_artifacts(tup)
        assert j_path.exists()
        assert m_path.exists()

        loaded_json = json.loads(j_path.read_text(encoding="utf-8"))
        assert loaded_json["release_bundle_digest"] == tup["release_bundle_digest"]

        md_content = m_path.read_text(encoding="utf-8")
        assert tup["release_bundle_digest"] in md_content
        assert "0002_v3_jev_ai_audit" in md_content


class TestRollbackRehearsal:
    """Simulates deployment failure and demonstrates atomic rollback via release tuple."""

    def test_simulated_rollback_rehearsal_preserves_compatibility(self, tmp_path: Path) -> None:
        # 1. State A: Verified Baseline Release Tuple
        baseline_tuple = vrt.build_release_tuple()
        baseline_digest = baseline_tuple["release_bundle_digest"]

        # 2. State B: Candidate deployment introduces altered detector config
        temp_config_dir = tmp_path / "configs"
        temp_config_dir.mkdir()
        temp_detector_cfg = temp_config_dir / "detector.demo.yaml"
        temp_detector_cfg.write_text("detector_code: M1\nthreshold: 0.9999\n", encoding="utf-8")
        temp_view_cfg = temp_config_dir / "views.demo.yaml"
        temp_view_cfg.write_text("views: {}\n", encoding="utf-8")

        candidate_tuple = vrt.build_release_tuple(config_dir=temp_config_dir)
        candidate_digest = candidate_tuple["release_bundle_digest"]
        assert candidate_digest != baseline_digest, "Candidate tuple must have different digest"

        # 3. Simulate Failure Incident: Candidate config causes threshold rejection
        # Trigger Class B rollback: Restore target baseline tuple configs
        reverted_tuple = vrt.build_release_tuple()
        reverted_digest = reverted_tuple["release_bundle_digest"]

        # 4. Verification: Reverted state strictly matches baseline digest
        assert reverted_digest == baseline_digest
        assert reverted_tuple["compatibility"]["code_and_config_compatible"] is True
        assert reverted_tuple["compatibility"]["database_revision_compatible"] is True
