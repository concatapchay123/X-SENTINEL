# Concurrency & Transaction Rules

- Microsoft SQL Server is shared; do not rely on in-process locks for cross-instance correctness.
- `analysis_jobs.request_id` unique constraint is the durable idempotency guard.
- Create job/result/score/alert mutations inside explicit transactions.
- Do not hold DB transactions open while computing SHAP/model inference; persist state before/after compute in short transactions.
- Background-job claiming should use a durable queue or `SELECT ... FOR UPDATE SKIP LOCKED` only after an approved design task.
- Retry serialization/deadlock failures only at transaction boundaries with bounded backoff.
- Never implement uniqueness only in frontend/backend pre-checks; enforce it in DB constraints.
