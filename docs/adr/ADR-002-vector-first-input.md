# ADR-002 — Vector-first MVP

## Context
Research documents use pre-vectorized EMBER input; Production proposal adds raw PE/LIEF.

## Decision
MVP accepts 2,381-dimensional vectors. Raw PE/LIEF is a Phase-2 adapter behind an explicit feature gate.

## Advantages
Avoids parser/schema ambiguity while core detector is built.

## Disadvantages
MVP is not yet a standalone raw-file scanner.

## Consequences
TC-03 is not an MVP gate unless scope changes.
