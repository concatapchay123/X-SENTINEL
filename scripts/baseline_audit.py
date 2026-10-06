from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    ".env.example",
    "docker-compose.yml",
    "pyproject.toml",
    "docs/baseline/00_PROJECT_BASELINE.md",
    "docs/baseline/07_DATABASE_SPEC.md",
    "docs/baseline/28_JEV_AI_SPEC.md",
    "docs/baseline/31_JEV_AI_OPERATIONAL_GUARDRAILS.md",
    "docs/plans/MASTER_PLAN_V3.md",
    "docs/database/DATABASE_RULES.md",
    "database/alembic.ini",
    "database/migrations/env.py",
    "database/migrations/versions/0001_v2_multiuser.py",
    "database/migrations/versions/0002_v3_jev_ai_audit.py",
    "database/schema/schema.sql",
    "backend/src/x_sentinel/database/models.py",
    "backend/src/x_sentinel/database/health.py",
    "backend/src/x_sentinel/jev_ai/client.py",
    "backend/src/x_sentinel/jev_ai/guardrails.py",
    "scripts/check_schema_drift.py",
]
missing = [p for p in REQUIRED if not (ROOT / p).exists()]
be_plans = sorted((ROOT / "docs/plans/backend_database_ai").glob("PLAN-BE-*.md"))
fe_plans = sorted((ROOT / "docs/plans/frontend").glob("PLAN-FE-*.md"))
legacy = sorted((ROOT / "docs/plans/legacy_v2").glob("PLAN-*.md"))

if len(be_plans) < 20:
    missing.append(f"expected >=20 backend/database/AI plans; found {len(be_plans)}")
if len(fe_plans) < 10:
    missing.append(f"expected >=10 frontend plans; found {len(fe_plans)}")
if len(legacy) < 24:
    missing.append(f"expected >=24 legacy V2 plans; found {len(legacy)}")

dataset_dir = ROOT / "datasets"
strict_dist = (
    os.getenv("XS_STRICT_DISTRIBUTION", "false").lower() in ("true", "1")
    or "--strict-distribution" in sys.argv
)

if not dataset_dir.exists():
    missing.append("datasets directory missing")
else:
    non_gitkeep = [p for p in dataset_dir.iterdir() if p.name != ".gitkeep"]
    if strict_dist and non_gitkeep:
        missing.append("datasets directory must be empty in V3 distribution package")
    else:
        gitignore = (
            (ROOT / ".gitignore").read_text(encoding="utf-8")
            if (ROOT / ".gitignore").exists()
            else ""
        )
        dockerignore = (
            (ROOT / ".dockerignore").read_text(encoding="utf-8")
            if (ROOT / ".dockerignore").exists()
            else ""
        )
        if "datasets/*" not in gitignore:
            missing.append(
                "datasets/* rule missing from .gitignore (dataset exclusion policy violation)"
            )
        if "datasets/**" not in dockerignore:
            missing.append(
                "datasets/** rule missing from .dockerignore (dataset exclusion policy violation)"
            )

if missing:
    raise SystemExit("BASELINE AUDIT FAILED:\n- " + "\n- ".join(missing))

dataset_status = (
    "empty datasets/ (distribution mode)"
    if not [p for p in dataset_dir.iterdir() if p.name != ".gitkeep"]
    else "local datasets preserved & excluded from Git/Docker"
)
print(
    f"BASELINE AUDIT PASS: {len(REQUIRED)} core files, {len(be_plans)} BE plans, {len(fe_plans)} FE plans, {len(legacy)} legacy plans, {dataset_status}"
)
