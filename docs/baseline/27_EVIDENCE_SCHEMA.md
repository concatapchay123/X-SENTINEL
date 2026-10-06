# 27 — EVIDENCE SCHEMA

Every non-demo acceptance analysis should eventually include:

```json
{
  "request_id": "...",
  "run_id": "...",
  "timestamp": "...",
  "code_commit": "...",
  "build_digest": "...",
  "input_id": "...",
  "input_mode": "vector",
  "view_map_hash": "...",
  "model_hash": "...",
  "model_config_hash": "...",
  "detector_config_hash": "...",
  "seed": 42,
  "malware_score": 0.0,
  "signals": {"m1": 0.0, "m2": 0.0, "m3": 0.0, "m4": 0.0, "m5": 0.0},
  "fusion_score": 0.0,
  "threshold_id": "...",
  "decision": "PASS|ALERT|QUARANTINE",
  "latency_ms": {"end_to_end": 0.0},
  "demo_mode": false
}
```

Acceptance scripts must reject `demo_mode=true` as scientific evidence.
