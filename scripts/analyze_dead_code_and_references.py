"""Analyze Python modules, imports, and references across X-SENTINEL V3.

This script builds a comprehensive dependency and reference map:
1. Maps all python files in backend/src, backend/tests, tests, scripts.
2. Extracts imports via AST.
3. Checks for string references (dynamic imports, configs, yaml, json, etc.).
4. Checks for empty or zero-byte files.
5. Identifies orphaned files or unreferenced modules.
"""

import ast
import os
from pathlib import Path

PROJECT_ROOT = Path("F:/IAM302t").resolve()


def get_imports(py_file: Path):
    """Extract imported module names from a python file using AST."""
    imports = set()
    try:
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
                    for alias in node.names:
                        imports.add(f"{node.module}.{alias.name}")
    except Exception as e:
        print(f"AST parse error in {py_file}: {e}")
    return imports


def main():
    print("Analyzing Python modules and references across repository...")

    # 1. Collect all python files
    all_py_files = []
    for root_dir, _, files in os.walk(PROJECT_ROOT):
        # Skip cache dirs
        if any(c in root_dir for c in [".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__", ".git"]):
            continue
        for f in files:
            if f.endswith(".py"):
                all_py_files.append((Path(root_dir) / f).relative_to(PROJECT_ROOT))

    print(f"Total non-cache Python files: {len(all_py_files)}")

    # 2. Extract imports from all python files
    file_imports = {}
    all_imported_symbols = set()
    for rel_p in all_py_files:
        full_p = PROJECT_ROOT / rel_p
        imps = get_imports(full_p)
        file_imports[str(rel_p)] = imps
        all_imported_symbols.update(imps)

    # 3. Analyze backend/src/x_sentinel modules
    backend_modules = [p for p in all_py_files if str(p).startswith("backend\\src\\x_sentinel") or str(p).startswith("backend/src/x_sentinel")]
    print(f"Backend x_sentinel modules: {len(backend_modules)}")

    # Also search entire codebase for text references to module names
    all_text_files = []
    for root_dir, _, files in os.walk(PROJECT_ROOT):
        if any(c in root_dir for c in [".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__", ".git", "datasets"]):
            continue
        for f in files:
            if f.endswith((".py", ".md", ".json", ".yaml", ".yml", ".sh", ".toml", ".txt")):
                all_text_files.append(Path(root_dir) / f)

    text_corpus = {}
    for p in all_text_files:
        try:
            rel = str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
            text_corpus[rel] = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    orphaned_candidates = []

    for mod_path in backend_modules:
        mod_rel = str(mod_path).replace("\\", "/")
        # Convert path to module dotted name: backend/src/x_sentinel/... -> x_sentinel....
        parts = mod_rel.replace("backend/src/", "").replace(".py", "").split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        dotted_name = ".".join(parts)
        base_name = parts[-1] if parts else ""

        # Check if imported by AST
        is_ast_imported = False
        importing_files = []
        for src_f, imps in file_imports.items():
            if src_f == str(mod_path):
                continue
            for imp in imps:
                if imp == dotted_name or imp.startswith(dotted_name + "."):
                    is_ast_imported = True
                    importing_files.append(src_f)
                    break

        # Check if referenced in text corpus (excluding itself)
        text_references = []
        for tf_rel, content in text_corpus.items():
            if tf_rel == mod_rel:
                continue
            if dotted_name in content or (base_name and f"{base_name}." in content):
                text_references.append(tf_rel)

        # Main app entrypoint
        if dotted_name in ["x_sentinel.main", "x_sentinel"]:
            is_ast_imported = True

        if not is_ast_imported and len(text_references) == 0:
            orphaned_candidates.append({
                "module": dotted_name,
                "path": mod_rel,
                "ast_imported": is_ast_imported,
                "text_refs_count": len(text_references),
            })

    print(f"Orphaned backend module candidates: {len(orphaned_candidates)}")
    for cand in orphaned_candidates:
        print(f"  - {cand['module']} ({cand['path']})")

    # 4. Check zero-byte / empty files
    empty_files = []
    for root_dir, _, files in os.walk(PROJECT_ROOT):
        if any(c in root_dir for c in [".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__", ".git"]):
            continue
        for f in files:
            fp = Path(root_dir) / f
            try:
                if fp.stat().st_size == 0:
                    empty_files.append(str(fp.relative_to(PROJECT_ROOT)).replace("\\", "/"))
            except Exception:
                pass

    print(f"\nEmpty (0-byte) files: {len(empty_files)}")
    for ef in empty_files:
        print(f"  - {ef}")

    # 5. Check scripts/ usage
    scripts = [p for p in all_py_files if str(p).startswith("scripts")]
    print(f"\nScripts in scripts/: {len(scripts)}")
    for sc in scripts:
        sc_rel = str(sc).replace("\\", "/")
        sc_name = Path(sc_rel).name
        refs = [tf for tf, c in text_corpus.items() if sc_name in c and tf != sc_rel]
        print(f"  {sc_name:35}: referenced in {len(refs)} files")


if __name__ == "__main__":
    main()
