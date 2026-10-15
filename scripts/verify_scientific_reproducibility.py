#!/usr/bin/env python3
"""Scientific Reproducibility & Metric Verification Script for X-SENTINEL V3.

Independently loads frozen evaluation runs from artifacts/evaluation/be14_candidate_suite,
verifies file SHA-256 digests against checksums.sha256,
and recomputes all scientific metrics from raw_predictions.jsonl to confirm zero drift.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "backend" / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend" / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from x_sentinel.evaluation.runner import recompute_metrics_from_raw, verify_run_artifacts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scientific_reproducibility")

CANDIDATE_RUNS = [
    "e0_distributions_seed42",
    "e1_t_concentrated_seed42",
    "e1_t_cross_seed42",
    "e1_t_spread_seed42",
    "e2_pooled_seed42",
    "e2_t_concentrated_seed42",
    "e2_t_cross_seed42",
    "e2_t_spread_seed42",
    "e3_paired_catch_miss_seed42",
    "e4_ablation_seed42",
    "e5_fpr_latency_seed42",
]


def verify_all_candidate_runs(suite_dir: Path | None = None) -> dict[str, Any]:
    if suite_dir is None:
        suite_dir = PROJECT_ROOT / "artifacts" / "evaluation" / "be14_candidate_suite"

    results: dict[str, Any] = {}
    all_passed = True

    for run_name in CANDIDATE_RUNS:
        run_path = suite_dir / run_name
        if not run_path.is_dir():
            logger.error("Run directory missing: %s", run_path)
            results[run_name] = {"status": "MISSING_DIR", "verified": False}
            all_passed = False
            continue

        try:
            art_ver = verify_run_artifacts(run_path)
            recomputed = recompute_metrics_from_raw(run_path)
            mismatches = recomputed.get("mismatches", [])

            run_ok = art_ver["checksum_verified"] and len(mismatches) == 0
            if not run_ok:
                all_passed = False

            results[run_name] = {
                "status": "PASS" if run_ok else "FAIL",
                "checksum_verified": art_ver["checksum_verified"],
                "file_hashes": art_ver.get("file_hashes", {}),
                "mismatches": mismatches,
                "experiment": recomputed.get("experiment"),
            }
            logger.info(
                "Run %s: checksum=%s mismatches=%d status=%s",
                run_name,
                art_ver["checksum_verified"],
                len(mismatches),
                "PASS" if run_ok else "FAIL",
            )
        except Exception as exc:
            logger.error("Error evaluating run %s: %s", run_name, exc)
            results[run_name] = {"status": "ERROR", "error": str(exc), "verified": False}
            all_passed = False

    return {
        "overall_status": "PASS" if all_passed else "FAIL",
        "total_runs": len(CANDIDATE_RUNS),
        "passed_runs": sum(1 for r in results.values() if r.get("status") == "PASS"),
        "runs": results,
    }


def main() -> int:
    rep = verify_all_candidate_runs()
    print(json.dumps(rep, indent=2))
    return 0 if rep["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
