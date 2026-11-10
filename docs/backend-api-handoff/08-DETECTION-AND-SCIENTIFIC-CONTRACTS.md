# X-SENTINEL V3 — DETECTION & SCIENTIFIC CONTRACTS

**Document ID:** `XS3-HANDOFF-08`  
**Version:** 3.0.0  
**Date:** 2026-10-16T14:04:49.547332+00:00  
**Classification:** Mathematical & Detection Specifications  

---

## 1. Detector Formulations & Specifications

### 1.1 M1: Top-k TreeSHAP Attribution Dominance Ratio (TADR)
Measures the concentration of feature importance within the top k features:
TADR_k(x) = sum(top_k |phi|) / (sum(all |phi|) + eps)
- Default: k=1 (Top-1 dominance), configurable up to k=10.
- Range: [0.0, 1.0]. Higher values indicate extreme concentration.

### 1.2 M2: Tabular STRIP (Shannon Entropy of Blended Predictions)
Measures vulnerability to perturbation by blending with benign reference instances (alpha=0.5).
- High score indicates abnormal low entropy under perturbation.

### 1.3 M3: View Concentration (Gini / Attribution Entropy Across Views)
Measures whether explanation mass is unnaturally concentrated in a single semantic view (Byte, Structural, or Behavioral).

### 1.4 M4: Symmetric Cross-View Disagreement
Evaluates consistency between sub-models trained on independent feature views.

### 1.5 M5: PE Semantic Plausibility Invariants
Evaluates structural integrity rules over the PE feature space. Normal compliant PE produces Score=0.0. Rule violations produce anomaly score > 0.0.
