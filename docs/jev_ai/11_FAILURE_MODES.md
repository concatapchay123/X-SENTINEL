# Jev AI Failure Modes

| Failure | Required behavior |
|---|---|
| LM Studio offline | Detector works; AI shows unavailable |
| Timeout | Abort AI request; preserve canonical result |
| Oversized context | truncate approved fields or block |
| Forbidden key/data | block before network call |
| Invalid response | store failure metadata; no authority change |
| Hallucinated verdict | UI labels advisory; human ignores; feedback/audit |
| Prompt injection string | treat as quoted data; never policy |
