from __future__ import annotations

from pathlib import Path
import uuid

from x_sentinel.audit.writer import AuditWriter
from x_sentinel.data.schema import validate_vector
from x_sentinel.data.views import load_view_map
from x_sentinel.detection.m1_tadr import m1_tadr
from x_sentinel.detection.m3_view import m3_view_concentration, view_contributions
from x_sentinel.domain import AnalysisResult
from x_sentinel.fusion.engine import demo_fusion
from x_sentinel.model.demo import DemoModelService


class AnalysisService:
    def __init__(self, audit_path: Path, view_map_path: Path, demo_mode: bool = True):
        self.demo_mode = demo_mode
        self.audit = AuditWriter(audit_path)
        self.view_map = load_view_map(view_map_path, allow_demo=demo_mode)
        if not demo_mode:
            raise RuntimeError(
                "Scientific mode remains gated until model/M4/fusion/view-map configs are frozen"
            )
        self.model = DemoModelService()

    def analyze_vector(self, features: list[float], request_id: str | None = None) -> AnalysisResult:
        vector = validate_vector(features)
        rid = request_id or str(uuid.uuid4())
        malware_score, shap = self.model.infer(vector)
        views = self.view_map.split(vector)
        shap_views = {
            "structural": shap[self.view_map.structural.start:self.view_map.structural.stop],
            "behavioral": shap[self.view_map.behavioral.start:self.view_map.behavioral.stop],
            "metadata": shap[self.view_map.metadata.start:self.view_map.metadata.stop],
        }
        contrib = view_contributions(shap_views)
        signals = {
            "m1": m1_tadr(shap),
            "m2": 0.0,
            "m3": m3_view_concentration(contrib),
            "m4": 0.0,
            "m5": 0.0,
        }
        suspicion = demo_fusion(signals)
        result = AnalysisResult(
            request_id=rid,
            status="DEMO_ONLY",
            demo_mode=True,
            malware_score=malware_score,
            signals=signals,
            suspicion_score=suspicion,
            threshold=None,
            view_contributions=contrib,
            warnings=["DEMO_MODE_NOT_SCIENTIFIC_EVIDENCE"],
        )
        evidence_ref = self.audit.append(result)
        return AnalysisResult(**{**result.__dict__, "evidence_ref": evidence_ref})
