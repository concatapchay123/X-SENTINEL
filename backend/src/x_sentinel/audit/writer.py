from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from x_sentinel.audit.evidence import CanonicalEvidence, compute_evidence_hash


class AuditWriteFailureError(RuntimeError):
    """Raised when writing to audit trail or database persistence fails."""


class AuditWriter:
    """Append-only audit writer for persisting events and canonical evidence to JSONL."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def append(self, event: Any) -> str:
        """Appends an arbitrary event or dataclass to the JSONL audit file.

        Preserves 100% backward compatibility with existing callers.
        """
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(event, CanonicalEvidence):
                payload = event.to_dict()
                if "evidence_hash" not in payload or not payload["evidence_hash"]:
                    payload["evidence_hash"] = event.compute_hash()
            elif is_dataclass(event):
                payload = asdict(event)
            elif hasattr(event, "__dict__"):
                payload = dict(event.__dict__)
            else:
                payload = dict(event)

            if "audit_timestamp" not in payload:
                payload["audit_timestamp"] = datetime.now(timezone.utc).isoformat()

            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(serialized + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    # fsync may fail on some memory/virtual filesystems, which is acceptable
                    pass
            return str(self.path)
        except Exception as exc:
            raise AuditWriteFailureError(
                f"Failed to append audit event to {self.path}: {exc}"
            ) from exc

    def append_evidence(self, evidence: CanonicalEvidence) -> str:
        """Appends validated canonical evidence with calculated hash to the audit trail."""
        if not isinstance(evidence, CanonicalEvidence):
            raise TypeError(f"Expected CanonicalEvidence, got {type(evidence).__name__}")
        return self.append(evidence)

    def read_events(self) -> list[dict[str, Any]]:
        """Reads all events from the audit trail."""
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    try:
                        events.append(json.loads(line_clean))
                    except json.JSONDecodeError as err:
                        raise AuditWriteFailureError(
                            f"Corrupted audit record at {self.path}:{line_num}: {err}"
                        ) from err
            return events
        except Exception as exc:
            if isinstance(exc, AuditWriteFailureError):
                raise
            raise AuditWriteFailureError(f"Failed to read audit events from {self.path}: {exc}") from exc

    def count(self) -> int:
        """Returns the number of events recorded in the audit trail."""
        return len(self.read_events())
