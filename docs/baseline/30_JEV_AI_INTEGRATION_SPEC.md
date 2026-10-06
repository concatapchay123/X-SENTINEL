# 30 — JEV AI INTEGRATION SPEC

## Integration pattern

Jev AI is called **after** canonical detector evidence is committed.

```text
Analyze request
 -> Detection Core
 -> Persist canonical result
 -> return detector result
 -> optional Jev request
      -> build minimized context
      -> guardrails
      -> LM Studio
      -> persist AI run
      -> return advisory response
```

## Endpoint configuration

Development host default: `http://localhost:1234/v1`.

Docker Desktop default recommendation: `http://host.docker.internal:1234/v1`.

All values are environment-configurable. Do not hard-code a model name.

## Timeout/failure

- AI timeout does not alter analysis status.
- AI 5xx/network error maps to `XS_AI_UNAVAILABLE`.
- blocked context maps to `XS_AI_CONTEXT_BLOCKED`.
- UI keeps detector result visible and offers retry.

## Versioning

Persist:

- model ID;
- prompt version;
- context digest;
- output digest;
- relevant detector analysis ID;
- latency/status.

This makes AI narratives reproducible enough for audit without treating them as scientific ground truth.
