# V3 Jev AI Persistence

The detector transaction and Jev transaction are decoupled. Canonical analysis must commit first. A later Jev failure cannot roll it back.

Recommended transaction sequence:

1. fetch immutable analysis snapshot;
2. create `jev_ai_runs(status=running)`;
3. build/redact/hash context;
4. call LM Studio outside the detector transaction;
5. store output hash/text according to retention; set completed/failed;
6. append `audit_events` entry.

Do not store hidden evaluation truth in any Jev table.
