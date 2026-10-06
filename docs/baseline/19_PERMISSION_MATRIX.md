# 19 — PERMISSION MATRIX — V3 TARGET

Final roles are subject to auth ADR. This matrix expresses minimum server-side boundaries.

| Capability | Admin | Analyst | Evaluator | Detection runtime | Jev AI runtime |
|---|---:|---:|---:|---:|---:|
| Submit/read own analyses | Yes | Yes | As needed | process only | No direct client access |
| Read canonical result/evidence | Yes | Yes | Yes | Yes | only allowlisted context |
| Invoke Jev explain/triage | Yes | Yes | Optional | No | executes request |
| Read Jev outputs | Yes | Yes | Optional | No | own generated output |
| Submit Jev feedback | Yes | Yes | Optional | No | No |
| Change scientific config | controlled | No | No | No | **No** |
| Read hidden manifest before scoring | No | No | custody role only | **No** | **No** |
| Score frozen predictions vs truth | No | No | Yes | No | No |
| Access raw PE bytes | controlled Phase 2 | upload only | controlled | static parser only | **No** |
| Execute shell/tools | admin ops only | No | No | No | **No** |

Frontend capability hiding is convenience only; backend authorization is authoritative.
