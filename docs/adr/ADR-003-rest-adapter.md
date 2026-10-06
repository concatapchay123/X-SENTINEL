# ADR-003 — REST adapter for UI/core separation

## Context
Source mentions optional REST/gRPC but has no contract. Streamlit UI still needs a clean backend boundary.

## Decision
[PROPOSED] Use FastAPI REST for MVP integration.

## Alternatives
Streamlit imports core directly; gRPC.

## Advantages
Contract tests, clean separation, future deployment flexibility.

## Disadvantages
Adds a local network hop.

## Consequences
API changes are contract-first.
