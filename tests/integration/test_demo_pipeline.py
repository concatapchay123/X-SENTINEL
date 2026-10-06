from pathlib import Path
from x_sentinel.services.analysis_service import AnalysisService


def test_demo_pipeline_marks_result_demo(tmp_path):
    service = AnalysisService(
        audit_path=tmp_path / "audit.jsonl",
        view_map_path=Path("configs/views.demo.yaml"),
        demo_mode=True,
    )
    result = service.analyze_vector([0.0] * 2381)
    assert result.demo_mode is True
    assert result.status == "DEMO_ONLY"
    assert "DEMO_MODE_NOT_SCIENTIFIC_EVIDENCE" in result.warnings
    assert (tmp_path / "audit.jsonl").exists()
