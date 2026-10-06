# Jev AI Integration Runbook

1. Confirm detector/API/DB healthy.
2. Start LM Studio local server.
3. Record exact model ID.
4. Enable `XS_JEV_AI_ENABLED=true`.
5. Call AI status endpoint.
6. Run one sanitized explain request.
7. Verify DB audit row and response label.
8. Test timeout/unavailable behavior.
9. Enable frontend Jev panel only after steps 1–8 pass.
