#!/usr/bin/env python3
"""
Adversarial Challenge Verification Suite — Challenger 2
Empirically tests Quality Gates G07, G08, G09, G11, G12
"""

import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

WORKSPACE = Path("f:/IAM302t").resolve()
os.chdir(WORKSPACE)

def log_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

failures: list[str] = []
warnings: list[str] = []

# ==============================================================================
# GATE G07: Backend Plan Accuracy & Implementation Status
# ==============================================================================
log_header("TEST SUITE 1: GATE G07 - BACKEND PLANS IMPLEMENTATION STATUS & PATHS")

plan_dir = WORKSPACE / "docs" / "plans" / "backend_database_ai"
plan_files = sorted(plan_dir.glob("PLAN-BE-*.md"))
print(f"Discovered backend plan files: {len(plan_files)}")

if len(plan_files) != 20:
    failures.append(f"G07: Expected 20 PLAN-BE files, found {len(plan_files)}")

g07_errors = []
total_sources_checked = 0
total_tests_checked = 0
total_artifacts_checked = 0
verified_artifacts = []

for pf in plan_files:
    content = pf.read_text(encoding="utf-8")
    
    # 1. Header check
    if "## Current Implementation Status" not in content:
        g07_errors.append(f"{pf.name}: Missing '## Current Implementation Status' header")
        continue
        
    status_sec = content.split("## Current Implementation Status")[1]
    
    # 2. Check required metadata fields
    req_fields = [
        "- **Verified Implementation Status:**",
        "- **Exact Source File Paths:**",
        "- **Associated Test Suites:**",
        "- **Operational Boundaries & Verified Limitations:**"
    ]
    for rf in req_fields:
        if rf not in status_sec:
            g07_errors.append(f"{pf.name}: Missing metadata field '{rf}'")

    # 3. Check Exact Source File Paths
    m_src = re.search(r'\- \*\*Exact Source File Paths:\*\*(.*?)(?=\- \*\*Associated Test Suites:\*\*)', status_sec, re.DOTALL)
    if m_src:
        lines = m_src.group(1).strip().splitlines()
        for line in lines:
            # find paths in backticks
            for token in re.findall(r'`([^`]+)`', line):
                token_clean = token.strip()
                if token_clean:
                    total_sources_checked += 1
                    target = WORKSPACE / token_clean
                    if not target.exists():
                        g07_errors.append(f"{pf.name}: Source path does not exist: '{token_clean}'")
    else:
        g07_errors.append(f"{pf.name}: Could not isolate Exact Source File Paths block")

    # 4. Check Associated Test Suites
    m_tst = re.search(r'\- \*\*Associated Test Suites:\*\*(.*?)(?=\- \*\*Empirical Artifacts:\*\*)', status_sec, re.DOTALL)
    if m_tst:
        lines = m_tst.group(1).strip().splitlines()
        for line in lines:
            for token in re.findall(r'`([^`]+)`', line):
                # e.g. `backend/tests/test_be01.py` or with test count
                parts = token.strip().split()
                if parts and parts[0].endswith(".py"):
                    test_path = parts[0]
                    total_tests_checked += 1
                    target = WORKSPACE / test_path
                    if not target.exists():
                        g07_errors.append(f"{pf.name}: Test suite does not exist: '{test_path}'")
    else:
        g07_errors.append(f"{pf.name}: Could not isolate Associated Test Suites block")

    # 5. Check Empirical Artifacts
    m_art = re.search(r'\- \*\*Empirical Artifacts:\*\*(.*?)(?=\- \*\*Operational Boundaries & Verified Limitations:\*\*)', status_sec, re.DOTALL)
    if m_art:
        lines = m_art.group(1).strip().splitlines()
        for line in lines:
            for token in re.findall(r'`([^`]+)`', line):
                token_clean = token.strip().split(":")[0].split()[0]
                if ("/" in token_clean or "\\" in token_clean or token_clean.endswith((".yaml", ".json", ".txt", ".md", ".csv"))) and not token_clean.startswith(("sha256", "http", "None")):
                    total_artifacts_checked += 1
                    target = WORKSPACE / token_clean
                    if not target.exists():
                        g07_errors.append(f"{pf.name}: Artifact path does not exist: '{token_clean}'")
                    else:
                        verified_artifacts.append((pf.name, token_clean))

# Specific check on PLAN-BE-10 line 26 redirection
be10_file = plan_dir / "PLAN-BE-10.md"
if be10_file.exists():
    be10_content = be10_file.read_text(encoding="utf-8")
    if "be01_be09_pre_be10" in be10_content:
        g07_errors.append("PLAN-BE-10: Still contains reference to deleted 'be01_be09_pre_be10'")
    if "docs/audits/full_be01_be20_final/BE10_JEV_RUNTIME_CLIENT_AUDIT.md" not in be10_content:
        g07_errors.append("PLAN-BE-10: Missing redirected path to 'BE10_JEV_RUNTIME_CLIENT_AUDIT.md'")
    else:
        print("PASS: PLAN-BE-10 redirection link verified.")

print(f"Total Source File Paths verified: {total_sources_checked}")
print(f"Total Associated Test Suites verified: {total_tests_checked}")
print(f"Total Empirical Artifact Paths checked: {total_artifacts_checked} (verified on disk: {len(verified_artifacts)})")
for plan_name, art_path in verified_artifacts:
    print(f"  [EXISTS] {plan_name}: {art_path}")

if g07_errors:
    for e in g07_errors:
        print(f"  [FAIL] {e}")
    failures.extend(g07_errors)
else:
    print("PASS: Quality Gate G07 fully satisfied! All 20 plans have verified headers and all paths exist on disk.")


# ==============================================================================
# GATE G08: Legacy Audit Cleanup - Class A Absence & Class B/C Presence
# ==============================================================================
log_header("TEST SUITE 2: GATE G08 - CLEANUP AUDIT (CLASS A, B, C)")

g08_errors = []

# Class A: Deleted directories and files
deleted_dirs = [
    WORKSPACE / "docs" / "frontend-handoff" / "audit",
    WORKSPACE / "docs" / "audits" / "be01_be03_final_audit",
    WORKSPACE / "docs" / "audits" / "be01_be06_pre_be07",
    WORKSPACE / "docs" / "audits" / "be01_be09_pre_be10",
]

for d in deleted_dirs:
    if d.exists() and any(d.iterdir()):
        g08_errors.append(f"Class A directory still exists and is not empty: {d.relative_to(WORKSPACE)}")
    else:
        print(f"PASS: Deleted directory confirmed absent or pruned: {d.relative_to(WORKSPACE)}")

repo_cleanup_md = list((WORKSPACE / "docs" / "audits" / "repository_cleanup").glob("*.md"))
if repo_cleanup_md:
    g08_errors.append(f"Class A markdown files still exist in repository_cleanup: {[f.name for f in repo_cleanup_md]}")
else:
    print("PASS: 0 markdown files in docs/audits/repository_cleanup/")

# Class B: 22 canonical reports in full_be01_be20_final
class_b_files = sorted((WORKSPACE / "docs" / "audits" / "full_be01_be20_final").glob("*.md"))
print(f"Class B markdown reports found: {len(class_b_files)}")
if len(class_b_files) != 22:
    g08_errors.append(f"Expected 22 Class B reports, found {len(class_b_files)}")
else:
    empty_class_b = [f.name for f in class_b_files if f.stat().st_size == 0]
    if empty_class_b:
        g08_errors.append(f"Class B files are empty: {empty_class_b}")
    else:
        print("PASS: All 22 Class B reports exist and are non-empty.")

# Class C: 5 JSON files
class_c_targets = [
    WORKSPACE / "docs" / "audits" / "full_be01_be20_final" / "CHANGES_MANIFEST.json",
    WORKSPACE / "docs" / "audits" / "full_be01_be20_final" / "CLEANUP_MANIFEST.json",
    WORKSPACE / "docs" / "audits" / "repository_cleanup" / "CLEANUP_MANIFEST.json",
    WORKSPACE / "docs" / "audits" / "repository_cleanup" / "inventory_raw_summary.json",
    WORKSPACE / "docs" / "audits" / "repository_cleanup" / "temp_cache_files.json",
]

for cf in class_c_targets:
    if not cf.exists():
        g08_errors.append(f"Class C JSON file missing: {cf.relative_to(WORKSPACE)}")
    else:
        try:
            data = json.loads(cf.read_text(encoding="utf-8"))
            print(f"PASS: Class C file exists and valid JSON ({len(data)} top-level keys): {cf.relative_to(WORKSPACE)}")
        except Exception as ex:
            g08_errors.append(f"Class C JSON corrupted: {cf.relative_to(WORKSPACE)} - {ex}")

# Manifest verification
cleanup_manifest_file = WORKSPACE / "docs" / "CLEANUP_MANIFEST.json"
if not cleanup_manifest_file.exists():
    g08_errors.append("docs/CLEANUP_MANIFEST.json is missing")
else:
    try:
        manifest_data = json.loads(cleanup_manifest_file.read_text(encoding="utf-8"))
        print("PASS: docs/CLEANUP_MANIFEST.json is valid JSON.")
        class_a_manifest = manifest_data.get("class_a_deleted_transient_files", [])
        print(f"Manifest Class A deleted files count: {len(class_a_manifest)}")
        if len(class_a_manifest) != 52:
            g08_errors.append(f"Expected 52 Class A files in manifest, found {len(class_a_manifest)}")
        for item in class_a_manifest:
            f_rel = item.get("relative_path")
            if (WORKSPACE / f_rel).exists():
                g08_errors.append(f"Class A file claimed deleted still exists on disk: {f_rel}")
            else:
                pass
    except Exception as ex:
        g08_errors.append(f"docs/CLEANUP_MANIFEST.json parse error: {ex}")

if g08_errors:
    for e in g08_errors:
        print(f"  [FAIL] {e}")
    failures.extend(g08_errors)
else:
    print("PASS: Quality Gate G08 fully satisfied.")


# ==============================================================================
# GATE G09: Reference Integrity & Deep Markdown Link Crawl
# ==============================================================================
log_header("TEST SUITE 3: GATE G09 - DEEP LINK CRAWLER & LINGERING REFERENCES")

g09_errors = []

# Gather all markdown files in docs/ and README.md
md_files = sorted((WORKSPACE / "docs").rglob("*.md"))
if (WORKSPACE / "README.md").exists():
    md_files.append(WORKSPACE / "README.md")

print(f"Scanning {len(md_files)} markdown files for links and references...")

link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

total_links_found = 0
total_rel_links_checked = 0
lingering_pattern = re.compile(r'(frontend-handoff/audit|be01_be03_final_audit|be01_be06_pre_be07|be01_be09_pre_be10)')

def resolve_target(ref_file, target_str):
    target_str = target_str.strip()
    
    # Handle file:// scheme
    if target_str.startswith("file:"):
        parsed = urllib.parse.urlparse(target_str)
        local_path = urllib.request.url2pathname(parsed.path)
        # On windows, url2pathname('/F:/...') returns 'F:\\...'
        p = Path(local_path).resolve()
        return p, None
        
    # Split file and anchor
    parts = target_str.split("#")
    file_part = parts[0].strip()
    anchor_part = parts[1].strip() if len(parts) > 1 else None
    
    if not file_part:
        return ref_file, anchor_part
        
    # Try resolving relative to referencing file's parent dir
    resolved = (ref_file.parent / file_part).resolve()
    if resolved.exists():
        return resolved, anchor_part
        
    # Try resolving relative to workspace root
    resolved_root = (WORKSPACE / file_part.lstrip("/\\")).resolve()
    if resolved_root.exists():
        return resolved_root, anchor_part
        
    return resolved, anchor_part

for mf in md_files:
    rel_mf = mf.relative_to(WORKSPACE)
    content = mf.read_text(encoding="utf-8", errors="replace")
    
    # Check for lingering references to deleted audit directories
    lines = content.splitlines()
    for lnum, line in enumerate(lines, 1):
        m = lingering_pattern.search(line)
        if m:
            # If in manifest or gap analysis explaining historical cleanup
            if any(k in mf.name for k in ["CLEANUP", "GAP-ANALYSIS", "12-FRONTEND-GAP-ANALYSIS", "13-FRONTEND-TRACEABILITY-MATRIX", "DELETED", "CHANGELOG", "MIGRATION"]):
                pass
            elif "[" in line and "](" in line:
                g09_errors.append(f"{rel_mf}:{lnum} Active link target contains deleted audit path: {m.group(1)} in '{line.strip()}'")

    # Extract all markdown links
    all_links = link_pattern.findall(content) + image_pattern.findall(content)
    for _text, target in all_links:
        total_links_found += 1
        target = target.strip()
        
        # Skip web protocols
        if target.startswith(("http://", "https://", "mailto:", "ftp:")):
            continue
            
        total_rel_links_checked += 1
        resolved_path, anchor = resolve_target(mf, target)
        
        if not resolved_path.exists():
            g09_errors.append(f"{rel_mf}: Broken link '{target}' -> resolved path does not exist: {resolved_path}")

print(f"Total links found: {total_links_found}")
print(f"Total relative / file links checked: {total_rel_links_checked}")

if g09_errors:
    for e in g09_errors:
        print(f"  [FAIL] {e}")
    failures.extend(g09_errors)
else:
    print("PASS: Quality Gate G09 satisfied. 0 broken links, 0 illegal lingering references.")


# ==============================================================================
# GATE G11: Automated Baseline Audits & Cryptographic Checksums
# ==============================================================================
log_header("TEST SUITE 4: GATE G11 - BASELINE & CHECKSUM SCRIPTS EXECUTION")

scripts_to_test = [
    ("python scripts/baseline_audit.py", 0),
    ("python scripts/verify_sha256sums.py", 0),
    ("python scripts/validate_v3_package.py", 0),
]

for cmd, expected_code in scripts_to_test:
    print(f"\nRunning: {cmd} ...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(res.stdout.strip())
    if res.stderr.strip():
        print(f"STDERR: {res.stderr.strip()}")
    if res.returncode != expected_code:
        failures.append(f"G11: Command '{cmd}' failed with returncode {res.returncode} (expected {expected_code})")
    else:
        print(f"PASS: '{cmd}' returned exit code 0.")


# ==============================================================================
# GATE G12: Git Working Tree Immutability & Safety Audit
# ==============================================================================
log_header("TEST SUITE 5: GATE G12 - GIT IMMUTABILITY AUDIT")

git_status_res = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
git_lines = [line_item.strip() for line_item in git_status_res.stdout.splitlines() if line_item.strip()]

forbidden_prefixes = [
    "backend/src/x_sentinel/",
    "backend/tests/",
    "tests/",
    "models/",
    "frontend/src/",
    "frontend/public/",
    "alembic/",
]

g12_errors = []
for line in git_lines:
    status_code = line[:2]
    filepath = line[3:].strip()
    for fp in forbidden_prefixes:
        if filepath.startswith(fp):
            g12_errors.append(f"Forbidden file modification detected: {line}")

print(f"Total modified/untracked files in working tree: {len(git_lines)}")
if g12_errors:
    for e in g12_errors:
        print(f"  [FAIL] {e}")
    failures.extend(g12_errors)
else:
    print("PASS: 0 unauthorized modifications to backend Python code, models, or test suites.")


# ==============================================================================
# FINAL VERDICT
# ==============================================================================
log_header("FINAL VERIFICATION SUMMARY & VERDICT")
if failures:
    print("VERDICT: REQUEST_CHANGES")
    print(f"Total failures encountered: {len(failures)}")
    for idx, f in enumerate(failures, 1):
        print(f"  {idx}. {f}")
    sys.exit(1)
else:
    print("VERDICT: APPROVE")
    print("All Quality Gates G07, G08, G09, G11, G12 EMPIRICALLY PASSED!")
    sys.exit(0)
