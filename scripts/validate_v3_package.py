from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

required = [
    "docs/plans/MASTER_PLAN_V3.md",
    "docs/baseline/28_JEV_AI_SPEC.md",
    "docs/baseline/29_JEV_AI_DATA_CONTRACT.md",
    "docs/baseline/30_JEV_AI_INTEGRATION_SPEC.md",
    "docs/baseline/31_JEV_AI_OPERATIONAL_GUARDRAILS.md",
    "configs/jev_ai.yaml",
    "database/migrations/versions/0002_v3_jev_ai_audit.py",
    "backend/src/x_sentinel/jev_ai/client.py",
    "backend/src/x_sentinel/jev_ai/orchestrator.py",
]

missing = [item for item in required if not (ROOT / item).exists()]
if missing:
    raise SystemExit(f"Missing V3 required files: {missing}")

dataset_entries = [p for p in (ROOT / "datasets").iterdir() if p.name != ".gitkeep"]
strict_dist = (
    os.getenv("XS_STRICT_DISTRIBUTION", "false").lower() in ("true", "1")
    or "--strict-distribution" in sys.argv
)

if strict_dist and dataset_entries:
    raise SystemExit(f"datasets/ must be empty in the distributed V3 package: {dataset_entries}")

if dataset_entries:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").exists() else ""
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8") if (ROOT / ".dockerignore").exists() else ""
    if "datasets/*" not in gitignore or "datasets/**" not in dockerignore:
        raise SystemExit("datasets/ contains local data but exclusion rules are missing from .gitignore or .dockerignore")
    print(f"datasets/ contains local datasets ({[p.name for p in dataset_entries]}) — verified excluded from Git and Docker")
else:
    print("datasets/ is empty (distribution baseline compliant)")

print("X-SENTINEL V3 package validation: PASS")
