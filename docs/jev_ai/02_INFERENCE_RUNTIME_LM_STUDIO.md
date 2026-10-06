# LM Studio Runtime

## Development
1. Load the chosen Jev model.
2. Start the local OpenAI-compatible server.
3. Verify `/v1/models`.
4. Configure X-SENTINEL environment variables.
5. Test a non-sensitive health prompt before enabling operator UI.

## Networking
- host process: `localhost:1234`;
- Docker Desktop: `host.docker.internal:1234`;
- never expose the LM Studio port to untrusted networks without an explicit security design.

## Resource policy
Use strict request timeout, context cap and low concurrency until actual hardware benchmarks are recorded.
