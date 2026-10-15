# X-SENTINEL V3 — REPRODUCIBILITY GUIDE
## Protocol, Instructions & Verification Steps for Independent Scientific & Software Audit

> **Target Version:** v0.3.0  
> **Repository Commit:** Git HEAD (`99797ff`)  
> **Release Bundle Digest:** `sha256:41818297801e359e988086fe6702eba4f75403c9d6f87863c69186dfbc7306eb`  

---

### 1. Levels of Reproducibility

An independent auditor must differentiate between distinct tiers of reproducibility:

1. **Source & Build Reproducibility**: Compiling and packaging the application with exact pinned dependencies without network deviations.
2. **Environment & Migration Reproducibility**: Converging on identical database schema (`0002_v3_jev_ai_audit`) from scratch.
3. **Detector Inference Reproducibility**: Generating bit-exact deterministic M1–M5 signals, LightGBM inference scores, and fusion decisions from fixed feature vectors.
4. **Scientific Metric Recomputation**: Independently recomputing AUROC, FPR, Recall, Wilson score confidence intervals, McNemar tests, and Clustered DeLong tests from immutable raw per-sample prediction records (`raw_predictions.jsonl`).
5. **Full Threat Experiment Reproduction**: Re-executing clean-label trigger synthesis, LightGBM TreeSHAP extraction, and blind evaluation from raw datasets.
6. **Jev AI Operational Reproducibility**: Verifying typed decision contracts, prompt formatting, and advisory boundary enforcement against a local LM Studio instance.
7. **Deployment & Container Reproducibility**: Building hardened Docker images and validating multi-container compose specifications.

---

### 2. System & Environment Prerequisites

- **Operating System**: Linux (Ubuntu 22.04 LTS / Debian 12) or Windows (10 / 11 / Server 2022).
- **Python Runtime**: Python 3.11 or 3.12 (CPython 64-bit).
- **C/C++ Build Environment**: MSVC Build Tools (Windows) or `build-essential` (Linux) for native extensions.
- **Hardware Profile**:
  - Minimum: 8 GB RAM, 4 CPU cores, 10 GB disk space.
  - Recommended for full TreeSHAP + STRIP benchmarks: 16 GB RAM, 8 CPU cores.
- **Optional External Services**:
  - Microsoft SQL Server 2022 (for live multi-user persistence integration).
  - LM Studio with `Jev-Style-Qwen3.5-2B-Decision` loaded on `http://localhost:1234/v1` (for live Jev AI inference).

---

### 3. Step-by-Step Reproduction Instructions

#### Step 1: Environment Setup & Activation

```bash
# Clone or navigate to the repository root
cd F:\IAM302t

# Create and activate a clean virtual environment
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\activate

# Linux / macOS:
source .venv/bin/activate

# Install dependencies in editable mode with development packages
pip install -e ".[dev]"
```

#### Step 2: Package Validation & Baseline Constitution Audit

```bash
# Verify baseline documentation, plan inventory, and dataset exclusions
python scripts/baseline_audit.py

# Verify package structure and import paths
python scripts/validate_v3_package.py

# Verify strict prohibition of unapproved vector database dependencies
python scripts/verify_no_vector_db.py
```

*Expected Result*: All 3 scripts report `PASS` with zero errors.

#### Step 3: Secret Sanitization Verification

```bash
# Scan entire workspace for exposed credentials, keys, or passwords
python scripts/scan_secrets.py --path .
```

*Expected Result*: `[+] SUCCESS: No exposed production credentials discovered. Secret scan PASS.`

#### Step 4: Code Standards & Strict Type Checking

```bash
# Verify PEP8 and Ruff linter compliance
ruff check backend frontend tests scripts database infrastructure

# Verify Mypy strict type safety across 101 source files
mypy backend/src tests/integration tests/security tests/fixtures tests/deployment scripts
```

*Expected Result*:
- `All checks passed!`
- `Success: no issues found in 101 source files`

#### Step 5: Execute Complete Automated Test Suite (993 Tests)

```bash
# Set PYTHONPATH and execute pytest
pytest -q
```

*Expected Result*: `993 passed in ~128s` with 0 failures and 0 errors.

#### Step 6: Recompute E0–E5 Scientific Metrics from Frozen Raw Predictions

```bash
# Execute standalone scientific recomputation script
python scripts/verify_scientific_reproducibility.py
```

*Expected Output*:
```text
Run e0_distributions_seed42: checksum=True mismatches=0 status=PASS
Run e1_t_concentrated_seed42: checksum=True mismatches=0 status=PASS
Run e1_t_cross_seed42: checksum=True mismatches=0 status=PASS
Run e1_t_spread_seed42: checksum=True mismatches=0 status=PASS
Run e2_pooled_seed42: checksum=True mismatches=0 status=PASS
Run e2_t_concentrated_seed42: checksum=True mismatches=0 status=PASS
Run e2_t_cross_seed42: checksum=True mismatches=0 status=PASS
Run e2_t_spread_seed42: checksum=True mismatches=0 status=PASS
Run e3_paired_catch_miss_seed42: checksum=True mismatches=0 status=PASS
Run e4_ablation_seed42: checksum=True mismatches=0 status=PASS
Run e5_fpr_latency_seed42: checksum=True mismatches=0 status=PASS
Overall Status: PASS (11 / 11 runs verified)
```

#### Step 7: Verify Release Tuple & Checksums

```bash
# Verify release tuple integrity
python scripts/verify_release_tuple.py --verify-only

# Verify 10-gate release checklist
python scripts/release_gate.py

# Verify full repository SHA-256 checksum manifest
python scripts/verify_sha256sums.py
```

*Expected Result*:
- `RELEASE TUPLE VERIFIED`
- `ALL RELEASE CHECKLIST GATES PASSED (100% GREEN)`
- `Manifest Verification: PASS` with negative tests passing.

---

### 4. Numerical Tolerances & Consistency Standards

When recomputing statistics across different hardware platforms or Python minor versions:

- **AUROC / FPR / Recall**: Exact match or tolerance $\le 10^{-6}$.
- **Wilson Score Intervals**: Exact match to analytic closed-form boundaries ($\le 10^{-6}$).
- **DeLong Variance & Z-scores**: Tolerance $\le 10^{-4}$ (due to floating point summation order).
- **Bootstrap Recomputations**: Bounded by fixed pseudo-random seed (`seed=42`). Using identical seed reproduces exact confidence intervals.
- **Deterministic Checksums**: Bit-exact SHA-256 match ($0.0$ diff).
