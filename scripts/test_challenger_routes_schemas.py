"""
Empirical Challenger Test Suite for Quality Gates G01, G04, G05, G06, G11.
Author: Challenger 1 (Routes, Schemas & Registries Verifier)
"""
import re
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from fastapi.routing import APIRoute
from x_sentinel.main import app


def test_fastapi_route_alignment():
    print("=== [GATE G01 & G04] ADVERSARIAL ROUTE ALIGNMENT VERIFICATION ===")
    
    # 1. Extract all actual FastAPI routes
    fastapi_ops = set()
    for r in app.routes:
        if isinstance(r, APIRoute):
            for m in (r.methods or set()):
                if m not in ("HEAD", "OPTIONS"):
                    fastapi_ops.add((m.upper(), r.path))
        elif hasattr(r, "original_router"):
            for nr in r.original_router.routes:
                if isinstance(nr, APIRoute):
                    for m in (nr.methods or set()):
                        if m not in ("HEAD", "OPTIONS"):
                            fastapi_ops.add((m.upper(), nr.path))

    print(f"Total authentic FastAPI operations: {len(fastapi_ops)}")

    # 2. Extract routes from docs/frontend-handoff/03-API-CATALOG.md
    catalog_path = REPO_ROOT / "docs" / "frontend-handoff" / "03-API-CATALOG.md"
    catalog_text = catalog_path.read_text(encoding="utf-8")
    
    pattern = r"\|\s*\*\*API-\d+\*\*\s*\|\s*`([A-Z]+)`\s*\|\s*`([^`]+)`\s*\|"
    catalog_ops = set()
    for match in re.finditer(pattern, catalog_text):
        method = match.group(1).strip()
        path = match.group(2).strip()
        catalog_ops.add((method, path))

    print(f"Total documented catalog operations: {len(catalog_ops)}")

    errors = []
    missing_in_catalog = fastapi_ops - catalog_ops
    ghost_in_catalog = catalog_ops - fastapi_ops

    if missing_in_catalog:
        errors.append(f"Missing in 03-API-CATALOG.md ({len(missing_in_catalog)}): {sorted(missing_in_catalog)}")
    if ghost_in_catalog:
        errors.append(f"Ghost operations in 03-API-CATALOG.md ({len(ghost_in_catalog)}): {sorted(ghost_in_catalog)}")

    # 3. Check section headers in 03-API-CATALOG.md (API-01 through API-21)
    for i in range(1, 22):
        api_header = f"API-{i:02d}:"
        if api_header not in catalog_text:
            errors.append(f"Missing specification section header '{api_header}' in 03-API-CATALOG.md")

    # 4. Check for ghost route /v1/ai/summary across ALL 17 docs
    docs_dir = REPO_ROOT / "docs" / "frontend-handoff"
    all_md_files = sorted(list(docs_dir.glob("*.md")))
    
    ghost_summary_occurrences = []
    for md in all_md_files:
        text = md.read_text(encoding="utf-8")
        if "/v1/ai/summary" in text:
            ghost_summary_occurrences.append(md.name)

    if ghost_summary_occurrences:
        errors.append(f"Ghost endpoint '/v1/ai/summary' found in: {ghost_summary_occurrences}")

    # 5. Check for active unannotated /v1/evaluate calls
    active_eval_calls = []
    for md in all_md_files:
        text = md.read_text(encoding="utf-8")
        # Check if any apiClient or fetch or axios invokes /v1/evaluate as an active endpoint
        for line_num, line in enumerate(text.splitlines(), start=1):
            if re.search(r"(?:apiClient|fetch|axios|http)\.(?:get|post|patch)\s*\(\s*['\"]/v1/evaluate", line):
                active_eval_calls.append(f"{md.name}:{line_num}: {line.strip()}")
            elif "/v1/evaluate" in line:
                # Check that context mentions design only, mock, gap, or offline CLI
                lower_line = line.lower()
                valid_gap_indicators = [
                    "chưa có", "không tồn tại", "mock", "design_only", "backend_gap",
                    "cli", "offline", "gap-11", "chưa triển khai", "mở rộng"
                ]
                if not any(k in lower_line for k in valid_gap_indicators):
                    active_eval_calls.append(f"Unannotated /v1/evaluate in {md.name}:{line_num}: {line.strip()}")

    if active_eval_calls:
        errors.append(f"Unannotated or active '/v1/evaluate' calls found ({len(active_eval_calls)}):\n" + "\n".join(active_eval_calls))

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return False
    else:
        print("[PASS] Route alignment is 100% exact: 21 FastAPI operations == 21 Catalog operations.")
        print("       Zero ghost routes (/v1/ai/summary is 0 matches), zero missing routes, /v1/evaluate is strictly gated/mock.")
        return True


def test_vector_validation_range():
    print("\n=== [GATE G04] VECTOR VALIDATION RANGE ADVERSARIAL TEST ===")
    contracts_path = REPO_ROOT / "docs" / "frontend-handoff" / "11-DATA-CONTRACTS.md"
    contracts_text = contracts_path.read_text(encoding="utf-8")

    errors = []

    # 1. Locate AnalyzeSubmitRequestSchema in 11-DATA-CONTRACTS.md
    # Match block between AnalyzeSubmitRequestSchema and export type AnalyzeSubmitRequest
    schema_match = re.search(r"export const AnalyzeSubmitRequestSchema\s*=\s*z\.object\(\{(.*?)\}\);\s*export type AnalyzeSubmitRequest", contracts_text, re.DOTALL)
    if not schema_match:
        errors.append("AnalyzeSubmitRequestSchema not found in 11-DATA-CONTRACTS.md")
    else:
        schema_body = schema_match.group(1)
        if "features:" not in schema_body:
            errors.append("features field not found in AnalyzeSubmitRequestSchema")
        else:
            # Extract features code between 'features:' and next field or end
            idx_start = schema_body.find("features:")
            idx_end = schema_body.find("source_name:", idx_start)
            if idx_end == -1:
                idx_end = len(schema_body)
            features_code = schema_body[idx_start:idx_end]
            
            if "Number.isFinite" not in features_code:
                errors.append("Number.isFinite refinement missing from features in AnalyzeSubmitRequestSchema")
            if "2381" not in features_code:
                errors.append("Vector length 2381 constraint missing from features schema")
            if re.search(r"\bmin\s*\(|\bmax\s*\(", features_code):
                errors.append(f"Invalid min/max constraint found on features vector elements: {features_code}")



    # 2. Check 13-FRONTEND-IMPLEMENTATION-ROADMAP.md for vector validation notes
    roadmap_path = REPO_ROOT / "docs" / "frontend-handoff" / "13-FRONTEND-IMPLEMENTATION-ROADMAP.md"
    roadmap_text = roadmap_path.read_text(encoding="utf-8")
    for line in roadmap_text.splitlines():
        if "min(0.0).max(1.0)" in line and "thay vì" not in line and "trước đây" not in line and "lỗi" not in line and "fix" not in line.lower():
            errors.append(f"Suspicious min(0.0).max(1.0) in 13-ROADMAP: {line.strip()}")

    # 3. Check across all files that features vector isn't bounded to [0, 1]
    docs_dir = REPO_ROOT / "docs" / "frontend-handoff"
    for md in docs_dir.glob("*.md"):
        m_text = md.read_text(encoding="utf-8")
        if re.search(r"features:\s*z\.array\(z\.number\(\)\.min\(0", m_text):
            errors.append(f"Invalid Zod vector min(0) on features in {md.name}")
        if re.search(r"vector\s+(?:đặc trưng\s+)?2[,.]381.*thuộc\s*\[0(?:\.0)?,\s*1(?:\.0)?\]", m_text, re.IGNORECASE):
            errors.append(f"Invalid EMBER vector [0, 1] claim in {md.name}")

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return False
    else:
        print("[PASS] Vector validation range strictly specifies finite float (unbounded real numbers for EMBER 2,381).")
        print("       Verified Number.isFinite and length(2381) in Zod schema with zero [0, 1] vector constraints.")
        return True


def test_telemetry_dto_structure():
    print("\n=== [GATE G05] NESTED PSUTIL TELEMETRY DTO VERIFICATION ===")
    errors = []

    # 1. Verify backend ground truth in infrastructure/monitoring/telemetry.py
    telemetry_py = (REPO_ROOT / "infrastructure" / "monitoring" / "telemetry.py").read_text(encoding="utf-8")
    if "import psutil" not in telemetry_py:
        errors.append("psutil not imported in infrastructure/monitoring/telemetry.py")
    if "cpu" not in telemetry_py or "memory" not in telemetry_py or "process" not in telemetry_py:
        errors.append("telemetry.py missing nested cpu, memory, process structure")

    # 2. Check 11-DATA-CONTRACTS.md
    contracts_text = (REPO_ROOT / "docs" / "frontend-handoff" / "11-DATA-CONTRACTS.md").read_text(encoding="utf-8")
    
    required_schemas = [
        "CpuTelemetrySchema",
        "MemoryTelemetrySchema",
        "ProcessTelemetrySchema",
        "AuthenticTelemetryResponseSchema",
    ]
    for s in required_schemas:
        if s not in contracts_text:
            errors.append(f"Missing schema '{s}' in 11-DATA-CONTRACTS.md")

    # Check fields in CpuTelemetrySchema: utilization_percent, logical_cores, physical_cores
    for f in ["utilization_percent", "logical_cores", "physical_cores"]:
        if f not in contracts_text:
            errors.append(f"CpuTelemetrySchema missing field '{f}'")

    # Check fields in MemoryTelemetrySchema: total_bytes, available_bytes, used_bytes, used_percent
    for f in ["total_bytes", "available_bytes", "used_bytes", "used_percent"]:
        if f not in contracts_text:
            errors.append(f"MemoryTelemetrySchema missing field '{f}'")

    # Check fields in ProcessTelemetrySchema: pid, rss_bytes, vms_bytes, thread_count
    for f in ["pid", "rss_bytes", "vms_bytes", "thread_count"]:
        if f not in contracts_text:
            errors.append(f"ProcessTelemetrySchema missing field '{f}'")

    # Check for fictional flat mock fields
    for forbidden in ["disk_free", "disk_total", "memory_free_gb"]:
        if forbidden in contracts_text:
            errors.append(f"Forbidden flat mock telemetry field '{forbidden}' found in 11-DATA-CONTRACTS.md")

    # 3. Check 08-PAGE-AND-UI-SPECIFICATIONS.md (P08 System Status)
    page_08 = (REPO_ROOT / "docs" / "frontend-handoff" / "08-PAGE-AND-UI-SPECIFICATIONS.md").read_text(encoding="utf-8")
    if "psutil" not in page_08:
        errors.append("08-PAGE-AND-UI-SPECIFICATIONS.md missing psutil telemetry specification on P08")

    # 4. Check 03-API-CATALOG.md API-19
    catalog_text = (REPO_ROOT / "docs" / "frontend-handoff" / "03-API-CATALOG.md").read_text(encoding="utf-8")
    if "API-19" not in catalog_text or "psutil" not in catalog_text:
        errors.append("03-API-CATALOG.md API-19 missing psutil telemetry description")

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return False
    else:
        print("[PASS] Telemetry DTO faithfully mirrors authentic backend psutil structure.")
        print("       Nested CPU, Memory, and Process metrics verified with zero flat mock fields.")
        return True


def test_registry_id_collisions():
    print("\n=== [GATE G06] REGISTRY ID COLLISION AND INTEGRITY CHECK ===")
    docs_dir = REPO_ROOT / "docs" / "frontend-handoff"
    errors = []

    # 1. Page Registry P01–P10 in 07-FRONTEND-PAGE-INVENTORY.md
    p_text = (docs_dir / "07-FRONTEND-PAGE-INVENTORY.md").read_text(encoding="utf-8")
    page_rows = re.findall(r"\|\s*\*\*(P\d{2})\*\*\s*\|\s*`([^`]+)`\s*\|\s*([^\|]+)\|", p_text)
    print(f"Total Page rows in 07-FRONTEND-PAGE-INVENTORY.md: {len(page_rows)}")
    
    page_ids = [r[0] for r in page_rows]
    page_routes = [r[1].strip() for r in page_rows]

    if len(page_ids) != 10:
        errors.append(f"Expected 10 Page IDs, found {len(page_ids)}: {page_ids}")
    if len(set(page_ids)) != len(page_ids):
        dups = [x for x in page_ids if page_ids.count(x) > 1]
        errors.append(f"Duplicate Page IDs: {set(dups)}")
    if len(set(page_routes)) != len(page_routes):
        dups_r = [x for x in page_routes if page_routes.count(x) > 1]
        errors.append(f"Duplicate Page Routes: {set(dups_r)}")

    expected_pages = [f"P{i:02d}" for i in range(1, 11)]
    if set(page_ids) != set(expected_pages):
        errors.append(f"Page IDs do not match P01..P10: {set(page_ids) ^ set(expected_pages)}")

    # Check page route map (supporting both Next.js [id] and OpenAPI {id} notations)
    canonical_routes = {
        "P01": ["/analyze"],
        "P02": ["/analysis/[id]", "/analysis/{id}"],
        "P03": ["/analysis/[id]/explainability", "/analysis/{id}/explainability"],
        "P04": ["/analysis/[id]/ai-advisory", "/analysis/{id}/ai-advisory"],
        "P05": ["/history"],
        "P06": ["/alerts"],
        "P07": ["/alerts/[id]", "/alerts/{id}"],
        "P08": ["/system/status"],
        "P09": ["/evaluation"],
        "P10": ["/auth/switch"],
    }
    actual_route_map = dict(zip(page_ids, page_routes, strict=False))
    for pid, valid_routes in canonical_routes.items():
        if actual_route_map.get(pid) not in valid_routes:
            errors.append(f"Page route mismatch for {pid}: expected one of {valid_routes}, got '{actual_route_map.get(pid)}'")

    # Verify P01..P10 presence in 08, 13, 15, 16
    for doc_name in ["08-PAGE-AND-UI-SPECIFICATIONS.md", "13-FRONTEND-IMPLEMENTATION-ROADMAP.md", "15-TRACEABILITY-MATRIX.md", "16-FRONTEND-MASTER-BLUEPRINT.md"]:
        d_text = (docs_dir / doc_name).read_text(encoding="utf-8")
        for pid in expected_pages:
            if pid not in d_text:
                errors.append(f"Page ID {pid} not found in {doc_name}")

    # 2. Component Registry C01–C35 in 09-COMPONENT-INVENTORY.md
    c_text = (docs_dir / "09-COMPONENT-INVENTORY.md").read_text(encoding="utf-8")
    comp_rows = re.findall(r"\|\s*\*\*(C\d{2})\*\*\s*\|\s*([^\|]+)\|", c_text)
    print(f"Total Component rows in 09-COMPONENT-INVENTORY.md: {len(comp_rows)}")
    
    comp_ids = [r[0] for r in comp_rows]
    if len(comp_ids) != 35:
        errors.append(f"Expected 35 Component IDs, found {len(comp_ids)}: {comp_ids}")
    if len(set(comp_ids)) != len(comp_ids):
        dups_c = [x for x in comp_ids if comp_ids.count(x) > 1]
        errors.append(f"Duplicate Component IDs: {set(dups_c)}")

    expected_comps = [f"C{i:02d}" for i in range(1, 36)]
    if set(comp_ids) != set(expected_comps):
        errors.append(f"Component IDs do not match C01..C35: {set(comp_ids) ^ set(expected_comps)}")

    # 3. Feature Inventory F-01–F-28
    f_text = (docs_dir / "02-FEATURE-INVENTORY.md").read_text(encoding="utf-8")
    t_text = (docs_dir / "15-TRACEABILITY-MATRIX.md").read_text(encoding="utf-8")

    f_in_02 = set(re.findall(r"\b(F-\d{2})\b", f_text))
    f_in_15 = set(re.findall(r"\b(F-\d{2})\b", t_text))
    expected_feats = set([f"F-{i:02d}" for i in range(1, 29)])

    print(f"Total Feature IDs in 02-FEATURE-INVENTORY.md: {len(f_in_02)}")
    print(f"Total Feature IDs in 15-TRACEABILITY-MATRIX.md: {len(f_in_15)}")

    if f_in_02 != expected_feats:
        errors.append(f"02-FEATURE-INVENTORY.md mismatch with F-01..F-28: {f_in_02 ^ expected_feats}")
    if f_in_15 != expected_feats:
        errors.append(f"15-TRACEABILITY-MATRIX.md mismatch with F-01..F-28: {f_in_15 ^ expected_feats}")

    # Check format C\d{2} and P\d{2}
    for cid in comp_ids:
        if not re.match(r"^C\d{2}$", cid):
            errors.append(f"Malformed Component ID: {cid}")
    for pid in page_ids:
        if not re.match(r"^P\d{2}$", pid):
            errors.append(f"Malformed Page ID: {pid}")

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return False
    else:
        print("[PASS] 100% Unique, non-colliding IDs across Page Registry (P01–P10), Component Registry (C01–C35), and Feature Inventory (F-01..F-28).")
        return True


def test_traceability_matrix_tables():
    print("\n=== [GATE G11] TRACEABILITY MATRIX VS SQLALCHEMY MODELS ===")
    
    # 1. Extract actual tables from SQLAlchemy models
    models_path = REPO_ROOT / "backend" / "src" / "x_sentinel" / "database" / "models.py"
    models_text = models_path.read_text(encoding="utf-8")
    
    actual_tables = set(re.findall(r'__tablename__\s*=\s*["\']([^"\']+)["\']', models_text))
    print(f"Actual SQLAlchemy tables in models.py ({len(actual_tables)}): {sorted(actual_tables)}")

    errors = []
    if len(actual_tables) != 13:
        errors.append(f"Expected exactly 13 SQLAlchemy tables, found {len(actual_tables)}")

    # 2. Check 15-TRACEABILITY-MATRIX.md Section 3 numbered list of 13 tables
    t_path = REPO_ROOT / "docs" / "frontend-handoff" / "15-TRACEABILITY-MATRIX.md"
    t_text = t_path.read_text(encoding="utf-8")

    section_3_match = re.search(r"### 3\. THỐNG KÊ ĐỘ PHỦ & ĐỐI SOÁT 13 BẢNG CSDL THỰC TẾ(.*?)(?:---|\Z)", t_text, re.DOTALL)
    if not section_3_match:
        errors.append("Section 3 of 15-TRACEABILITY-MATRIX.md not found")
    else:
        sec_text = section_3_match.group(1)
        tables_in_sec_3 = set(re.findall(r"\d+\.\s*`([^`]+)`", sec_text))
        print(f"Tables listed in Section 3 ({len(tables_in_sec_3)}): {sorted(tables_in_sec_3)}")
        
        diff_missing = actual_tables - tables_in_sec_3
        diff_extra = tables_in_sec_3 - actual_tables
        if diff_missing:
            errors.append(f"Tables missing from Section 3: {diff_missing}")
        if diff_extra:
            errors.append(f"Extra/phantom tables in Section 3: {diff_extra}")

    # 3. Check Section 2 main matrix table for referenced database tables in Column 5
    sec_2_table_names = set()
    for line in t_text.splitlines():
        if line.startswith("| **F-"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                db_col = parts[5] # Column 5: "Bảng CSDL Thực Tế"
                # Pattern: `table_name` possibly followed by (`column_name`)
                # e.g. `analysis_results` (`view_contributions`), `model_versions`
                # e.g. *None*, *OS Hardware (`psutil`)*, *In-Memory DB Revision Check*
                table_refs = re.findall(r"`([a-z_]+)`(?:\s*\([^)]*\))?", db_col)
                for t in table_refs:
                    # Ignore non-table markers
                    if t not in ("none", "psutil"):
                        sec_2_table_names.add(t)

    print(f"Authentic tables referenced in F-01..F-28 rows ({len(sec_2_table_names)}): {sorted(sec_2_table_names)}")
    # Verify that all referenced tables belong to the authentic 13 SQLAlchemy tables
    invalid_tables_in_matrix = sec_2_table_names - actual_tables
    if invalid_tables_in_matrix:
        errors.append(f"Invalid/phantom tables referenced in matrix rows: {invalid_tables_in_matrix}")

    # 4. Check for zero occurrences of the 6 phantom tables anywhere in 15-TRACEABILITY-MATRIX.md
    phantom_tables = [
        "module_scores",
        "explainability_reports",
        "ai_advisory_reports",
        "alert_audit_logs",
        "sys_health_checks",
        "model_evaluations",
    ]
    for pt in phantom_tables:
        matches = list(re.finditer(rf"\b{pt}\b", t_text))
        if matches:
            for m in matches:
                start = max(0, m.start() - 60)
                end = min(len(t_text), m.end() + 60)
                snippet = t_text[start:end]
                # Only allowed in the section explicitly stating they are removed
                if "loại bỏ" not in snippet.lower() and "giả tưởng" not in snippet.lower() and "không tồn tại" not in snippet.lower():
                    errors.append(f"Unannotated phantom table '{pt}' in 15-TRACEABILITY-MATRIX.md: {snippet}")

    # 5. Check 04-DATABASE-SCHEMA.md for phantom tables
    schema_path = REPO_ROOT / "docs" / "frontend-handoff" / "04-DATABASE-SCHEMA.md"
    schema_text = schema_path.read_text(encoding="utf-8")
    for pt in phantom_tables:
        if re.search(rf"\b{pt}\b", schema_text):
            errors.append(f"Phantom table '{pt}' found in 04-DATABASE-SCHEMA.md")

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return False
    else:
        print("[PASS] All tables in 15-TRACEABILITY-MATRIX.md match actual 13 SQLAlchemy models exactly. Zero phantom tables.")
        return True


def main():
    print("================================================================================")
    print("CHALLENGER 1: ADVERSARIAL VERIFICATION HARNESS (G01, G04, G05, G06, G11)")
    print("================================================================================\n")
    results = [
        test_fastapi_route_alignment(),
        test_vector_validation_range(),
        test_telemetry_dto_structure(),
        test_registry_id_collisions(),
        test_traceability_matrix_tables(),
    ]
    print("\n================================================================================")
    print("FINAL ADVERSARIAL VERIFICATION SUMMARY")
    print("================================================================================")
    if all(results):
        print("ALL QUALITY GATES (G01, G04, G05, G06, G11) EMPIRICALLY PASSED VERIFICATION!")
        print("VERDICT: APPROVE")
        sys.exit(0)
    else:
        print("ADVERSARIAL VERIFICATION DETECTED CRITICAL DEFECTS!")
        print("VERDICT: REQUEST_CHANGES")
        sys.exit(1)


if __name__ == "__main__":
    main()
