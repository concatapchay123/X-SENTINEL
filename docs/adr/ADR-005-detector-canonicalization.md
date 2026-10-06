# ADR-005 — Detector canonicalization policy

## Context
The source documents conflict on M4, Score Fusion and LightGBM configuration.

## Decision
Interfaces are implementation-ready, but a scientific run cannot be accepted until:
1. one M4 formula is frozen;
2. one fusion/calibration strategy is frozen;
3. one model/config identity is frozen;
4. exact view mapping is frozen.

[PROPOSED] M4 concept is symmetric cross-view disagreement over three view-level signals. Any historical variant may be retained only as an ablation strategy.

## Consequences
Code uses strategy interfaces/config IDs; blind runs record the exact strategy.
