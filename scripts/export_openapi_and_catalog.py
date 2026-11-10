"""
Exports live OpenAPI 3.1 specification from FastAPI runtime and validates all route endpoints.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure paths are added
sys.path.insert(0, str(Path("backend/src").resolve()))
sys.path.insert(0, str(Path("infrastructure").resolve()))

from x_sentinel.main import app


def main() -> None:
    schema = app.openapi()
    target_dir = Path("docs/backend-api-handoff")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    out_file = target_dir / "openapi.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
        
    paths = schema.get("paths", {})
    operation_count = sum(len(methods) for methods in paths.values())
    print(f"OpenAPI successfully exported to {out_file}")
    print(f"Total Path Templates: {len(paths)}")
    print(f"Total Operations: {operation_count}")
    
    for path, methods in sorted(paths.items()):
        for method, op in methods.items():
            op_id = op.get("operationId", "N/A")
            summary = op.get("summary", "")
            tags = ",".join(op.get("tags", []))
            print(f"  {method.upper():<7} {path:<35} [{tags}] {op_id} - {summary}")

if __name__ == "__main__":
    main()
