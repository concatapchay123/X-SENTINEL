from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


class AuditWriter:
    def __init__(self, path: Path):
        self.path = path

    def append(self, event: Any) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(event) if is_dataclass(event) else dict(event)
        payload["audit_timestamp"] = datetime.now(timezone.utc).isoformat()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return str(self.path)
