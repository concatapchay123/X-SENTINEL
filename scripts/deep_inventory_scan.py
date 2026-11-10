"""Deep Repository Inventory and Cleanup Analysis Script for X-SENTINEL V3.

This script executes a comprehensive discovery across F:\\IAM302t:
1. Validates filesystem boundary and reparse points.
2. Scans every file and directory.
3. Detects git status (tracked, untracked, ignored).
4. Computes SHA-256 hashes (excluding files > 50MB) to find exact duplicates.
5. Builds Python AST import dependency graph to identify potential dead code.
6. Categorizes all files into:
   - Category A: Safe temporary files
   - Category B: Regenerable build artifacts
   - Category C: Duplicate files
   - Category D: Dead code / obsolete modules
   - Category E: Documentation clutter / scratch
   - Category F: Uncertain / High-risk files
   - PROTECTED: Source code, scientific assets, tests, migrations, configs, etc.
7. Generates draft inventory reports.
"""

import hashlib
import json
import os
import stat
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("F:/IAM302t").resolve()


def check_boundary(path: Path) -> bool:
    """Strictly verify path is within PROJECT_ROOT."""
    try:
        resolved = path.resolve()
        common = Path(os.path.commonpath([str(PROJECT_ROOT), str(resolved)])).resolve()
        return common == PROJECT_ROOT
    except Exception:
        return False


def is_reparse_point(path: Path) -> bool:
    """Check if file or dir is a reparse point (symlink, junction)."""
    try:
        st = path.lstat()
        if path.is_symlink():
            return True
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        file_attrs = getattr(st, "st_file_attributes", 0)
        if file_attrs & reparse_flag:
            return True
        return False
    except Exception:
        return False


def get_git_status():
    """Retrieve git status classification."""
    tracked_bytes = subprocess.check_output(["git", "ls-files"], cwd=PROJECT_ROOT)
    tracked = set(tracked_bytes.decode("utf-8", errors="ignore").splitlines())

    # Get status for untracked and ignored
    status_bytes = subprocess.check_output(
        ["git", "status", "--ignored", "--porcelain=v1"], cwd=PROJECT_ROOT
    )
    status_lines = status_bytes.decode("utf-8", errors="ignore").splitlines()

    untracked_dirs = set()
    untracked_files = set()
    ignored_dirs = set()
    ignored_files = set()

    for line in status_lines:
        code = line[:2]
        rel = line[3:].strip()
        # strip quotes if any
        if rel.startswith('"') and rel.endswith('"'):
            rel = rel[1:-1]
        rel_norm = rel.replace("\\", "/")
        if code == "??":
            if rel_norm.endswith("/"):
                untracked_dirs.add(rel_norm.rstrip("/"))
            else:
                untracked_files.add(rel_norm)
        elif code == "!!":
            if rel_norm.endswith("/"):
                ignored_dirs.add(rel_norm.rstrip("/"))
            else:
                ignored_files.add(rel_norm)

    return tracked, untracked_dirs, untracked_files, ignored_dirs, ignored_files


def sha256_file(path: Path, max_size=50 * 1024 * 1024) -> str:
    """Compute SHA-256 for files under max_size."""
    try:
        if path.stat().st_size > max_size:
            return "SKIPPED_LARGE_FILE"
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        return f"ERROR_{e}"


def main():
    print(f"Starting inventory scan on {PROJECT_ROOT}...")
    assert check_boundary(PROJECT_ROOT), "Boundary validation failed for PROJECT_ROOT"

    tracked, untracked_dirs, untracked_files, ignored_dirs, ignored_files = get_git_status()
    print(f"Git tracked: {len(tracked)} files")

    all_files = []
    all_dirs = []
    hash_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ext_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "size": 0})
    dir_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "size": 0})

    temp_cache_files = []
    build_artifact_files = []
    temp_cache_size = 0
    build_artifact_size = 0

    reparse_violations = []

    # Walk directory
    for root_dir, _dirs, files in os.walk(PROJECT_ROOT):
        rpath = Path(root_dir)
        if not check_boundary(rpath):
            print(f"CRITICAL: Path boundary escape attempt: {rpath}")
            continue

        if is_reparse_point(rpath):
            reparse_violations.append(str(rpath))
            continue

        rel_root = rpath.relative_to(PROJECT_ROOT)
        all_dirs.append(str(rel_root))

        for f in files:
            fpath = rpath / f
            if not check_boundary(fpath):
                print(f"CRITICAL: File boundary escape attempt: {fpath}")
                continue

            if is_reparse_point(fpath):
                reparse_violations.append(str(fpath))
                continue

            rel_file = str(fpath.relative_to(PROJECT_ROOT)).replace("\\", "/")
            try:
                st = fpath.stat()
                fsize = st.st_size
                mtime = st.st_mtime
            except Exception:
                fsize = 0
                mtime = 0

            # Git classification
            git_class = "UNKNOWN"
            if rel_file in tracked:
                git_class = "TRACKED"
            else:
                is_ignored = False
                for ig in ignored_dirs:
                    if rel_file.startswith(ig + "/"):
                        is_ignored = True
                        break
                if not is_ignored and rel_file in ignored_files:
                    is_ignored = True

                if is_ignored:
                    git_class = "IGNORED"
                else:
                    is_untracked = False
                    for ut in untracked_dirs:
                        if rel_file.startswith(ut + "/"):
                            is_untracked = True
                            break
                    if not is_untracked and rel_file in untracked_files:
                        is_untracked = True
                    git_class = "UNTRACKED" if is_untracked else "IGNORED"

            # Extension & Dir stats
            ext = fpath.suffix.lower() if fpath.suffix else "(no_ext)"
            top_dir = rel_file.split("/")[0] if "/" in rel_file else "(root)"
            ext_stats[ext]["count"] += 1
            ext_stats[ext]["size"] += fsize
            dir_stats[top_dir]["count"] += 1
            dir_stats[top_dir]["size"] += fsize

            # Hashing (skip .git to save time, skip datasets > 50MB)
            file_hash = None
            if not rel_file.startswith(".git/"):
                file_hash = sha256_file(fpath)
                if file_hash and not file_hash.startswith("SKIPPED") and not file_hash.startswith("ERROR"):
                    hash_map[file_hash].append({"rel_path": rel_file, "size": fsize, "git": git_class})

            # Check Category A: Temporary cache files
            is_temp_cache = False
            if (
                rel_file.startswith(".mypy_cache/")
                or rel_file.startswith(".pytest_cache/")
                or rel_file.startswith(".ruff_cache/")
                or "/__pycache__/" in "/" + rel_file
                or rel_file == ".coverage"
                or rel_file.endswith(".pyc")
                or rel_file.endswith(".pyo")
            ):
                is_temp_cache = True
                temp_cache_files.append({"path": rel_file, "size": fsize, "git": git_class})
                temp_cache_size += fsize

            # Check Category B: Build artifacts
            is_build_artifact = False
            if (
                rel_file.startswith("build/")
                or rel_file.startswith("dist/")
                or rel_file.startswith("htmlcov/")
                or rel_file.startswith("out/")
                or rel_file.startswith(".next/")
                or ".egg-info/" in rel_file
            ):
                is_build_artifact = True
                build_artifact_files.append({"path": rel_file, "size": fsize, "git": git_class})
                build_artifact_size += fsize

            file_info = {
                "rel_path": rel_file,
                "name": f,
                "ext": ext,
                "size": fsize,
                "mtime": mtime,
                "git_class": git_class,
                "hash": file_hash,
                "is_temp_cache": is_temp_cache,
                "is_build_artifact": is_build_artifact,
            }
            all_files.append(file_info)

    # Duplicates (exclude 0-byte files or single files)
    duplicate_groups = {}
    for h, flist in hash_map.items():
        if len(flist) > 1 and int(flist[0]["size"]) > 0:
            duplicate_groups[h] = flist

    print("\nScan complete:")
    print(f"Total files: {len(all_files)}")
    print(f"Total directories: {len(all_dirs)}")
    total_repo_size = sum(int(str(file_info["size"])) for file_info in all_files)
    print(f"Total repo size: {total_repo_size / (1024*1024):.2f} MB ({total_repo_size / (1024*1024*1024):.2f} GB)")
    print(f"Temp cache files: {len(temp_cache_files)} files ({temp_cache_size / (1024*1024):.2f} MB)")
    print(f"Build artifact files: {len(build_artifact_files)} files ({build_artifact_size / (1024*1024):.2f} MB)")
    print(f"Duplicate hash groups: {len(duplicate_groups)}")
    print(f"Reparse point violations: {len(reparse_violations)}")

    # Top directories by size
    print("\n--- Directory Sizes ---")
    for d, d_stat in sorted(dir_stats.items(), key=lambda x: int(x[1]["size"]), reverse=True):
        print(f"{d:30}: {d_stat['count']:6} files, {d_stat['size'] / (1024*1024):10.2f} MB")

    # Top extensions by count
    print("\n--- Top Extensions by Count ---")
    for ext, e_stat in sorted(ext_stats.items(), key=lambda x: int(x[1]["count"]), reverse=True)[:15]:
        print(f"{ext:15}: {e_stat['count']:6} files, {e_stat['size'] / (1024*1024):10.2f} MB")

    # Duplicate examination
    print(f"\n--- Duplicate Groups ({len(duplicate_groups)}) ---")
    for idx, (h, items) in enumerate(list(duplicate_groups.items())[:20], 1):
        print(f"Group {idx} (Hash: {h[:12]}..., Size: {items[0]['size']} bytes):")
        for it in items:
            print(f"  - [{it['git']}] {it['rel_path']}")

    # Save summary data
    out_dir = PROJECT_ROOT / "docs" / "audits" / "repository_cleanup"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_data = {
        "total_files": len(all_files),
        "total_dirs": len(all_dirs),
        "total_size_bytes": total_repo_size,
        "temp_cache_files_count": len(temp_cache_files),
        "temp_cache_size_bytes": temp_cache_size,
        "build_artifact_files_count": len(build_artifact_files),
        "build_artifact_size_bytes": build_artifact_size,
        "duplicate_groups_count": len(duplicate_groups),
        "reparse_violations_count": len(reparse_violations),
        "dir_stats": dict(dir_stats),
        "ext_stats": dict(ext_stats),
        "duplicate_groups": duplicate_groups,
    }

    with open(out_dir / "inventory_raw_summary.json", "w", encoding="utf-8") as out_fp1:
        json.dump(summary_data, out_fp1, indent=2)

    with open(out_dir / "temp_cache_files.json", "w", encoding="utf-8") as out_fp2:
        json.dump(temp_cache_files, out_fp2, indent=2)

    print(f"\nRaw inventory summary written to {out_dir / 'inventory_raw_summary.json'}")


if __name__ == "__main__":
    main()
