# X-SENTINEL V3 — RESIDUAL RISK REGISTER
## Systemic, Scientific, Cybersecurity & Operational Risk Assessment

> **Assessment Date:** 2026-10-15  
> **Auditor Panel:** Site Reliability & Risk Governance Board  
> **Canonical Target Reference:** `docs/baseline/26_RISK_REGISTER.md`, `PLAN-BE-20.md`  

---

### Risk Severity Heatmap Matrix

| Probability \ Impact | Low | Medium | High | Critical |
|---|---|---|---|---|
| **High** | — | — | **RSK-01** (FPR Shift) | — |
| **Medium** | — | **RSK-03** (SHAP Latency) | **RSK-02** (Scientific Freeze) | **RSK-05** (Poisoned Drift) |
| **Low** | **RSK-06** (AI Outage) | **RSK-04** (LIEF Drift) | **RSK-07** (Blind Contam) | — |

---

### Detailed Risk Entries

| Risk ID | Category | Risk Description | Prob. | Impact | Severity | Mitigating Controls | Contingency / Fallback Plan | Owner |
|---|---|---|---|---|---|---|---|---|
| **RSK-01** | Scientific | **False Positive Alarm Rate Divergence in Production**: Using preliminary calibration threshold $\tau_{\text{locked}} = 0.46885$ on production samples may result in higher than acceptable false alarm rates ($> 1\%$). | High | High | **HIGH** | The system supports runtime dynamic threshold overrides via `configs/detector.yaml` without code changes. | Operators can operate in D0 alert budget mode or adjust threshold based on local validation data. Recalibrate D1 on official benign partition. | Principal ML Scientist |
| **RSK-02** | Scientific | **Unresolved Scientific View Map & Model Freeze (`OQ-01`, `OQ-02`)**: Running strict scientific evaluation mode raises `ExperimentBlockedError` because feature partitions and model hashes are not promoted into `*.scientific.yaml`. | Med | High | **HIGH** | System enforces fail-closed execution. Production operates on fully verified `configs/views.demo.yaml` and `configs/model.ember2018.yaml`. | Promote verified view partitions and model hashes into scientific configuration files via formal Change Request. | Research Lead |
| **RSK-03** | Performance | **TreeSHAP Latency Spikes Under Concurrent Load**: When large batches of files are analyzed concurrently, TreeSHAP CPU computation (~1.2s/sample) may saturate available CPU cores and increase API response latency. | Med | Med | **MEDIUM** | Fast-path fallback mechanism allows computing LightGBM + M1/M4/M5 without TreeSHAP in under 45ms. Concurrency semaphore limits active jobs to 50. | Scale Uvicorn worker processes horizontally; offload TreeSHAP explanations to asynchronous Celery/RQ background queue. | Site Reliability Engineer |
| **RSK-04** | Security | **LIEF 1.0 vs 0.9 Feature Drift in Phase 2 Raw PE**: Upgrading or running raw PE feature extraction against varying versions of LIEF or NumPy may introduce subtle floating-point drift in section and entropy features. | Low | Med | **LOW** | Production API endpoint `/v1/analyze/file` remains gated HTTP 501 (`XS_FEATURE_DISABLED`). Comprehensive test suite (`test_raw_pe_equivalence.py`) audits exact drift. | Maintain production gating until a frozen C++ LIEF 0.9.0 container is validated against bit-exact legacy benchmarks. | Malware Research Engineer |
| **RSK-05** | Scientific | **Backdoor Evasion by Novel Unmodeled Trigger Families**: Clean-label evasion attacks using trigger patterns outside the 3 studied families (`T-concentrated`, `T-spread`, `T-cross`) may evade individual M1–M5 detectors. | Med | Crit | **HIGH** | Multi-view cross-signal fusion combines structural, behavioral, and metadata views, requiring an adversary to evade multiple orthogonal detection mechanisms simultaneously. | Expand threat simulation runner with additional trigger architectures (e.g., relocation table manipulation, DOS stub padding). | Principal Security Architect |
| **RSK-06** | AI Operational | **LM Studio Local Runtime Process Failure**: Local LM Studio or vLLM process crashes or experiences GPU out-of-memory errors during analyst triage sessions. | Low | Low | **LOW** | Two-phase transaction commit guarantees zero database lock leakage. Detection core has zero runtime AI dependencies. | API returns advisory error envelope; analyst UI falls back to deterministic rule-based template. Restart LM Studio service. | AI Integration Specialist |
| **RSK-07** | Security | **Evaluation Data Contamination Across Process Boundaries**: Operators or automated scripts accidentally expose blind evaluation ground-truth labels to detector inference pipelines. | Low | High | **MEDIUM** | `BlindCustodyGuard` blocks filesystem path traversal (`../`), sanitizes environment variables, and rejects payloads containing ground-truth keywords. | Isolate evaluation environments in separate Docker containers with distinct database credentials and read-only filesystem mounts. | Security Auditor |

---

### Risk Governance Conclusion

The system implements robust architectural controls to isolate operational, security, and performance risks. The primary residual risks (**RSK-01**, **RSK-02**, **RSK-05**) reside in the scientific research domain and are transparently documented as gating prerequisites prior to safety-critical automated production deployments.
