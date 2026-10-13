from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from x_sentinel.data.schema import FEATURE_COUNT


class SplitIntegrityError(ValueError):
    """Raised when dataset splits violate zero-leakage or structural invariants."""


class SplitRole(StrEnum):
    """Canonical dataset split roles enforcing zero-leakage governance (Task 14.3)."""

    FIT = "FIT"
    VALIDATION_CLEAN = "VALIDATION_CLEAN"
    D1_CALIBRATION = "D1_CALIBRATION"
    FINAL_BLIND_EVALUATION = "FINAL_BLIND_EVALUATION"
    OOD_TEMPORAL_EVALUATION = "OOD_TEMPORAL_EVALUATION"


THREAT_MODEL_SPEC: dict[str, Any] = {
    "schema_version": "v3.0-be14",
    "input_domain": "ember_2381_static_vector",
    "feature_count": FEATURE_COUNT,
    "clean_label_only": True,
    "feature_vector_simulation_only": True,
    "binary_pe_feasibility_proven": False,
    "malware_execution_permitted": False,
    "defender_modes": ("D0", "D1"),
    "primary_defender_mode": "D1",
    "poison_rate_grid": (0.005, 0.01, 0.02),
    "attacker_goal": (
        "Induce targeted misclassification of triggered malware feature vectors as benign "
        "(label 0) while preserving clean validation accuracy and avoiding label flipping."
    ),
    "scope_disclaimer": (
        "All threat simulations operate strictly on 2,381-dimensional EMBER static PE feature "
        "vectors under a clean-label backdoor protocol. Feature-space trigger realizability "
        "does not claim end-to-end binary PE compilation or execution preservation."
    ),
}

TRIGGER_FAMILIES: dict[str, dict[str, Any]] = {
    "T-concentrated": {
        "family_id": "T-concentrated",
        "description": (
            "High-leverage concentrated trigger localized within V3 Metadata/String/Export view."
        ),
        "views": ["metadata"],
        "default_indices": (1600, 1601, 1602, 1603, 1604, 1605),
        "default_values": (0.85, 0.80, 0.75, 0.90, 0.70, 0.85),
    },
    "T-spread": {
        "family_id": "T-spread",
        "description": (
            "Low-amplitude spread trigger distributed across V2 Behavioral/Import/Section view."
        ),
        "views": ["behavioral"],
        "default_indices": (300, 450, 600, 750, 900, 1050, 1200, 1350),
        "default_values": (0.65, 0.70, 0.60, 0.75, 0.68, 0.72, 0.64, 0.69),
    },
    "T-cross": {
        "family_id": "T-cross",
        "description": (
            "Coordinated cross-view trigger spanning V1 Structural, V2 Behavioral, "
            "and V3 Metadata views."
        ),
        "views": ["structural", "behavioral", "metadata"],
        "default_indices": (50, 120, 400, 850, 1650, 1950),
        "default_values": (0.78, 0.74, 0.82, 0.76, 0.88, 0.84),
    },
}

RQ_HYPOTHESIS_MATRIX: dict[str, dict[str, Any]] = {
    "RQ1": {
        "question": (
            "Does cross-view verification (M4) improve or complement single-view attribution "
            "shift detection (M1) across concentrated, spread, and cross-view triggers?"
        ),
        "hypothesis": "H1",
        "null_hypothesis": (
            "H0_1: M4 provides no statistically significant improvement in AUROC or Recall@FPR1% "
            "over M1 on spread or cross-view triggers and zero unique catch contribution."
        ),
        "alternative_hypothesis": (
            "H1: M4 achieves higher detection sensitivity or statistically significant unique "
            "catch coverage on spread/cross-view triggers while remaining competitive on "
            "concentrated triggers."
        ),
        "metrics": ["auroc", "recall_at_fpr_1pct", "post_defense_asr", "paired_catch_miss"],
        "statistical_tests": [
            "paired_auroc_delong",
            "mcnemar_paired_test",
            "paired_bootstrap_test",
        ],
        "experiments": ["E2", "E3"],
    },
    "RQ2": {
        "question": (
            "Does multi-signal Risk Fusion outperform individual detection signals (M1..M5) "
            "across heterogeneous backdoor trigger topologies?"
        ),
        "hypothesis": "H2",
        "null_hypothesis": (
            "H0_2: Risk Fusion (Reduced M1-M4 or Full M1-M5) does not exceed the best single "
            "signal in aggregate AUROC or Recall@FPR1% across trigger families."
        ),
        "alternative_hypothesis": (
            "H2: Risk Fusion achieves superior or more consistent AUROC and Recall@FPR1% across "
            "T-concentrated, T-spread, and T-cross while respecting the locked D1 FPR threshold."
        ),
        "metrics": ["auroc", "recall_at_fpr_1pct", "post_defense_asr", "fpr"],
        "statistical_tests": [
            "paired_auroc_delong",
            "mcnemar_paired_test",
            "paired_bootstrap_test",
            "holm_bonferroni_correction",
        ],
        "experiments": ["E2", "E3", "E4"],
    },
    "RQ3": {
        "question": (
            "What is the marginal detection gain and latency cost of adding M5 "
            "(Semantic Plausibility) in Full Fusion (M1-M5) relative to Reduced Fusion (M1-M4)?"
        ),
        "hypothesis": "H3",
        "null_hypothesis": (
            "H0_3: Full Fusion (M1-M5) yields zero positive delta in Recall@FPR1% or AUROC "
            "compared to Reduced Fusion (M1-M4)."
        ),
        "alternative_hypothesis": (
            "H3: Full Fusion (M1-M5) improves Recall@FPR1% or AUROC on triggers violating "
            "physical PE invariants once authoritative feature-index mapping (OQ-01) is frozen, "
            "with explicitly quantified rule-evaluation latency overhead."
        ),
        "metrics": ["auroc", "recall_at_fpr_1pct", "delta_recall", "latency_p50_p95_p99"],
        "statistical_tests": [
            "paired_auroc_delong",
            "mcnemar_paired_test",
            "paired_bootstrap_test",
        ],
        "experiments": ["E4", "E5"],
    },
    "RQ4": {
        "question": (
            "Does D1 benign quantile calibration maintain empirical False Positive Rate near "
            "the 1% target on held-out unseen benign samples with practical runtime latency?"
        ),
        "hypothesis": "H4",
        "null_hypothesis": (
            "H0_4: Empirical FPR on unseen held-out benign test data deviates outside the "
            "expected statistical interval around 1% or violates latency budgets."
        ),
        "alternative_hypothesis": (
            "H4: Locked D1 calibration threshold controls held-out benign FPR with bounded "
            "Wilson 95% confidence interval and sub-second detector latency."
        ),
        "metrics": ["fpr", "wilson_95_ci", "latency_p50_p95_p99"],
        "statistical_tests": ["wilson_ci"],
        "experiments": ["E0", "E5"],
    },
}

EXPERIMENT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "E0": {
        "code": "E0",
        "title": "Sanity Check & Score Distributions across 4 Canonical Groups",
        "groups": (
            "clean_model_benign",
            "clean_model_triggered",
            "poisoned_model_benign",
            "poisoned_model_triggered",
        ),
        "primary_outputs": ("group_quantiles", "exceedance_rate_at_locked_threshold", "status"),
    },
    "E1": {
        "code": "E1",
        "title": "Attack Viability, Pre-Defense ASR & Clean-Trigger Control",
        "primary_outputs": (
            "eligible_count",
            "successful_attack_count",
            "asr",
            "clean_trigger_evasion_rate",
            "poisoning_associated_gain",
            "confirmed_viable",
        ),
    },
    "E2": {
        "code": "E2",
        "title": "Main Detector Comparison (M1..M5, Reduced Fusion, Full Fusion)",
        "methods": ("m1", "m2", "m3", "m4", "m5", "reduced_fusion", "full_fusion"),
        "primary_outputs": ("auroc", "recall_at_locked_fpr", "fpr", "post_defense_asr"),
    },
    "E3": {
        "code": "E3",
        "title": "Paired Sample-Level Catch/Miss Concordance Analysis",
        "primary_outputs": ("both_detect", "a_only", "b_only", "neither", "mcnemar_p_value"),
    },
    "E4": {
        "code": "E4",
        "title": "Paired Ablation Study (Single Signals vs Reduced Fusion vs Full Fusion)",
        "primary_outputs": ("delta_auroc", "delta_recall", "bootstrap_ci", "mcnemar_p_value"),
    },
    "E5": {
        "code": "E5",
        "title": "Held-Out Benign False Positive Rate, Subgroup Audit & Scoped Latency",
        "primary_outputs": (
            "held_out_benign_fpr",
            "wilson_95_ci",
            "benign_subgroups",
            "latency_by_scope",
        ),
    },
}


@dataclass(frozen=True)
class DatasetSplitManifest:
    """Immutable dataset split manifest with sample-ID hygiene and SHA-256 digest."""

    dataset_name: str
    dataset_version: str
    role: SplitRole
    sample_ids: tuple[str, ...]
    labels: tuple[int, ...]
    feature_count: int = FEATURE_COUNT
    seed: int = 42

    def __post_init__(self) -> None:
        if not self.dataset_name.strip():
            raise SplitIntegrityError("dataset_name must be non-empty.")
        if not self.dataset_version.strip():
            raise SplitIntegrityError("dataset_version must be non-empty.")
        if self.feature_count != FEATURE_COUNT:
            raise SplitIntegrityError(
                f"feature_count must equal {FEATURE_COUNT}, got {self.feature_count}."
            )
        if len(self.sample_ids) == 0:
            raise SplitIntegrityError("sample_ids cannot be empty.")
        if len(self.sample_ids) != len(self.labels):
            raise SplitIntegrityError(
                f"sample_ids length ({len(self.sample_ids)}) != labels length ({len(self.labels)})."
            )
        seen: set[str] = set()
        for sid in self.sample_ids:
            if not isinstance(sid, str) or not sid.strip():
                raise SplitIntegrityError("Every sample_id must be a non-empty string.")
            if sid in seen:
                raise SplitIntegrityError(
                    f"Duplicate sample_id '{sid}' within split role {self.role.value}."
                )
            seen.add(sid)
        for lbl in self.labels:
            if isinstance(lbl, bool) or not isinstance(lbl, int) or lbl not in (0, 1):
                raise SplitIntegrityError(
                    "Split labels must be binary integers in {0, 1} "
                    f"(unlabeled -1 must be excluded), got {lbl!r}."
                )

    @property
    def manifest_sha256(self) -> str:
        payload = {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "role": self.role.value,
            "sample_ids": list(self.sample_ids),
            "labels": list(self.labels),
            "feature_count": self.feature_count,
            "seed": self.seed,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


def audit_dataset_splits(
    splits: Sequence[DatasetSplitManifest],
    *,
    allow_multi_seed_same_role: bool = False,
) -> dict[str, Any]:
    """Audits dataset splits for zero-leakage between roles and tracks multi-seed overlap."""
    if not splits:
        raise SplitIntegrityError("At least one DatasetSplitManifest is required for audit.")

    role_to_ids: dict[SplitRole, set[str]] = {}
    role_seed_seen: set[tuple[SplitRole, int]] = set()
    repeated_across_seeds: set[str] = set()
    manifest_hashes: dict[str, str] = {}

    for split in splits:
        if split.role == SplitRole.D1_CALIBRATION and any(lbl != 0 for lbl in split.labels):
            raise SplitIntegrityError(
                "D1_CALIBRATION split must contain only benign (label=0) samples."
            )
        key = f"{split.role.value}:seed_{split.seed}"
        if (split.role, split.seed) in role_seed_seen:
            raise SplitIntegrityError(
                f"Duplicate split manifest for role {split.role.value} and seed {split.seed}."
            )
        if split.role in role_to_ids and not allow_multi_seed_same_role:
            raise SplitIntegrityError(
                f"Multiple splits provided for role {split.role.value} "
                "while allow_multi_seed_same_role=False."
            )
        role_seed_seen.add((split.role, split.seed))
        manifest_hashes[key] = split.manifest_sha256

        current_ids = set(split.sample_ids)
        if split.role in role_to_ids:
            overlap_same_role = role_to_ids[split.role].intersection(current_ids)
            repeated_across_seeds.update(overlap_same_role)
            role_to_ids[split.role].update(current_ids)
        else:
            role_to_ids[split.role] = set(current_ids)

    roles = list(role_to_ids.keys())
    for i in range(len(roles)):
        for j in range(i + 1, len(roles)):
            r1, r2 = roles[i], roles[j]
            leaked = sorted(role_to_ids[r1].intersection(role_to_ids[r2]))
            if leaked:
                raise SplitIntegrityError(
                    f"Sample ID leakage detected between {r1.value} and {r2.value}: "
                    f"{len(leaked)} overlapping IDs (first: {leaked[0]})."
                )

    sorted_repeated = sorted(repeated_across_seeds)
    return {
        "passed": True,
        "leakage_detected": False,
        "roles_audited": [r.value for r in roles],
        "manifest_hashes": manifest_hashes,
        "repeated_ids_across_seeds": sorted_repeated,
        "requires_clustered_inference": len(sorted_repeated) > 0,
    }


@dataclass(frozen=True)
class TriggerSpec:
    """Immutable specification of a vector-level trigger family."""

    family: str
    feature_indices: tuple[int, ...]
    feature_values: tuple[float, ...]
    modifiable_views: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.family not in TRIGGER_FAMILIES:
            raise ValueError(
                f"Unknown trigger family '{self.family}'. "
                f"Must be one of {sorted(TRIGGER_FAMILIES)}."
            )
        if len(self.feature_indices) == 0:
            raise ValueError("feature_indices must be non-empty.")
        if len(self.feature_indices) != len(self.feature_values):
            raise ValueError("feature_indices and feature_values must have identical length.")
        if len(set(self.feature_indices)) != len(self.feature_indices):
            raise ValueError("feature_indices must not contain duplicates.")
        for idx in self.feature_indices:
            if isinstance(idx, bool) or not isinstance(idx, int) or not (0 <= idx < FEATURE_COUNT):
                raise ValueError(
                    f"Trigger feature index {idx!r} out of range [0, {FEATURE_COUNT - 1}]."
                )
        for val in self.feature_values:
            if (
                isinstance(val, bool)
                or not isinstance(val, (int, float))
                or not math.isfinite(float(val))
            ):
                raise ValueError(f"Trigger feature value must be finite float, got {val!r}.")
        if self.modifiable_views:
            allowed_views = set(TRIGGER_FAMILIES[self.family]["views"])
            for v_name in self.modifiable_views:
                if v_name not in allowed_views:
                    raise ValueError(
                        f"TriggerSpec modifiable_views {self.modifiable_views!r} contains "
                        f"'{v_name}' which is not allowed for family '{self.family}' "
                        f"(allowed: {sorted(allowed_views)})."
                    )


@dataclass(frozen=True)
class AttackManifest:
    """Audit manifest for a clean-label poisoning construction run (Task 14.4)."""

    manifest_id: str
    trigger: TriggerSpec
    poison_rate: float
    total_train_samples: int
    poisoned_sample_ids: tuple[str, ...]
    original_labels: tuple[int, ...]
    poisoned_labels: tuple[int, ...]
    seed: int = 42
    target_label: int = 0
    source_split_role: SplitRole = SplitRole.FIT

    def __post_init__(self) -> None:
        if not self.manifest_id.strip():
            raise ValueError("manifest_id must be non-empty.")
        if not (0.0 < self.poison_rate <= 0.10):
            raise ValueError(f"poison_rate must be in (0, 0.10], got {self.poison_rate}.")
        if self.total_train_samples <= 0:
            raise ValueError("total_train_samples must be positive.")
        if len(self.poisoned_sample_ids) == 0:
            raise ValueError("poisoned_sample_ids must be non-empty.")
        if not (
            len(self.poisoned_sample_ids) == len(self.original_labels) == len(self.poisoned_labels)
        ):
            raise ValueError(
                "poisoned_sample_ids, original_labels, and poisoned_labels must have equal length."
            )


def verify_clean_label_integrity(
    manifest: AttackManifest,
    *,
    forbidden_eval_sample_ids: Sequence[str] | None = None,
) -> bool:
    """Verifies that a poisoning manifest strictly obeys the clean-label backdoor invariant."""
    if manifest.source_split_role != SplitRole.FIT:
        raise ValueError(
            f"Attack poisoning is only permitted on the FIT training split, "
            f"got role '{manifest.source_split_role}'."
        )
    if manifest.target_label not in (0, 1):
        raise ValueError(f"target_label must be 0 or 1, got {manifest.target_label}.")
    if len(set(manifest.poisoned_sample_ids)) != len(manifest.poisoned_sample_ids):
        raise ValueError("Duplicate sample_id in poisoned_sample_ids.")
    n_poisoned = len(manifest.poisoned_sample_ids)
    if n_poisoned > manifest.total_train_samples:
        raise ValueError(
            f"Poisoning budget denominator mismatch: poisoned count ({n_poisoned}) "
            f"exceeds total_train_samples ({manifest.total_train_samples})."
        )
    expected_poisoned = manifest.poison_rate * float(manifest.total_train_samples)
    if abs(float(n_poisoned) - expected_poisoned) > max(
        1.0, 1e-6 * float(manifest.total_train_samples)
    ):
        raise ValueError(
            f"Poisoning budget denominator mismatch: {n_poisoned} / {manifest.total_train_samples} "
            f"({n_poisoned / manifest.total_train_samples:.6f}) does not match declared "
            f"poison_rate={manifest.poison_rate:.6f}."
        )
    if forbidden_eval_sample_ids is not None:
        overlap = set(manifest.poisoned_sample_ids).intersection(set(forbidden_eval_sample_ids))
        if overlap:
            raise ValueError(
                f"Evaluation/calibration leakage in AttackManifest: {len(overlap)} poisoned "
                f"sample IDs overlap with forbidden split."
            )
    for sid, orig, pois in zip(
        manifest.poisoned_sample_ids,
        manifest.original_labels,
        manifest.poisoned_labels,
        strict=True,
    ):
        if orig != pois:
            raise ValueError(
                f"Clean-label violation: labels were flipped for sample '{sid}' ({orig} -> {pois})."
            )
        if pois != manifest.target_label:
            raise ValueError(
                f"Clean-label violation: poisoned sample '{sid}' has label {pois} "
                f"!= target_label {manifest.target_label}."
            )
    return True


def apply_vector_trigger(
    features: Sequence[float],
    trigger: TriggerSpec,
) -> list[float]:
    """Applies a vector-level trigger to a copy of a 2381-dim feature vector."""
    if len(features) != FEATURE_COUNT:
        raise ValueError(f"Expected {FEATURE_COUNT} features, got {len(features)}.")
    out = [float(x) for x in features]
    for idx, val in zip(trigger.feature_indices, trigger.feature_values, strict=True):
        out[idx] = float(val)
    return out
