# 28 — JEV AI MODEL & ROLE SPEC

## Mission

Jev AI is the local reasoning/explanation collaborator for X-SENTINEL. It converts canonical machine evidence into understandable analysis while preserving the detector as the only decision authority.

## Deployment model

- Host: LM Studio local server.
- Protocol: OpenAI-compatible `POST /v1/chat/completions`.
- Network: loopback/private host path only by default.
- Cloud egress: disabled by policy.
- Availability: optional; detector must function without it.

## Model contract

Required configurable fields:

- `model_id`
- `base_url`
- `timeout_seconds`
- `temperature`
- `max_context_chars`
- `prompt_version`
- `advisory_only=true`

Model architecture, parameter count, context length, quantization and license are `TBD` until the selected Jev model is known.

## Supported modes

- `explain`: explain one canonical analysis.
- `triage`: prioritize analyst checks and unresolved evidence.
- `compare`: compare two canonical analyses/config versions.
- `report`: draft a structured analyst/research narrative.
- `docs`: answer from approved project documentation when retrieval is implemented.

## Output requirements

Every output must distinguish:

1. facts copied from canonical evidence;
2. interpretation;
3. uncertainty/limitations;
4. recommended human checks.

It must never phrase itself as the source of the detector decision.
