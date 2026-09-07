"""
Batch-sequential loop v0 orchestrator (spec.md §5.3, T2.7):

    propose/receive candidates -> trust score (UQ + novelty) -> flag if below threshold
        -> batch (dedupe near-duplicates, cap by DES-run budget)
        -> DES backend  <- swappable: SyntheticDESBackend (now) / ManualWorklistDESBackend (28-Aug, T2.9)
        -> ingest results -> append to training data -> retrain per-KPI models
        -> recalibrate UQ (refit conformal quantiles / QRF on updated data)

v0 scope (spec.md §5.5): a single demonstrative pass, not repeated/robust
multi-round validation. KPI scope is passed in (kpi_scope.DEMO_4 or
kpi_scope.all_kpi_slugs()) -- this module never hardcodes which KPIs run,
per the "generic by default" requirement (spec.md §5.1.1 tier 1).

"Retrain" is deliberately NOT experimenting_ml/src/retrain.py's full
19-model/hyperparameter-search pipeline -- that's a training-time tool, far
too heavy to call inside an active-learning loop iteration. Retraining here
is simpler and already built: each KPI's UQEstimator (T2.3) already knows
how to rebuild and .fit() the exact registered architecture, so "retrain"
is just calling .fit() again on the updated data.

Two DES backends, two shapes (spec.md §7 item 9): SyntheticDESBackend's
simulate() is synchronous, so run_loop() below does propose -> flag ->
batch -> simulate -> retrain in one call. ManualWorklistDESBackend can't be
synchronous (a human has to type ~130 fields into AnyLogic Cloud between
export and results coming back), so that path is split into
export_manual_round() (propose -> flag -> batch -> export worklist) and
ingest_manual_round() (ingest real results -> retrain), called on either
side of the real manual AnyLogic Cloud run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .des_backend.base import DESBackend
from .novelty import NoveltyScorer
from .trust import TrustDecision, calibrate_thresholds_per_kpi, decide, trust_score
from .uq.dispatch import get_uq_estimator, load_registry

# kpi_slug, registry -> UQEstimator. Every function below defaults to
# dispatch.get_uq_estimator (T2.1's generic, registry-driven routing --
# DEMO_4's mechanism, unchanged). Pass proven6.get_proven_uq_estimator
# instead to run the same machinery against PROVEN_6's benchmarked winning
# methods (spec.md §7 item 13) -- the two KPI sets never mix within one call.
EstimatorFactory = Callable[[str, Optional[Dict[str, Any]]], Any]


def _kpi_scale(y: np.ndarray) -> float:
    """Normalizing scale for a KPI's interval width (spec.md §5.1: "e.g.
    training std or IQR"). Floored above 0 -- normalized_width() rejects a
    zero/negative scale, and a KPI with near-zero training variance would
    otherwise divide by ~0 and blow up every trust score."""
    std = float(np.std(y))
    return max(std, 1e-6)


def fit_kpi_estimators(
    kpi_slugs: List[str],
    X_train: pd.DataFrame,
    Y_train: pd.DataFrame,
    registry: Optional[Dict[str, Any]] = None,
    estimator_factory: Optional[EstimatorFactory] = None,
) -> Dict[str, Any]:
    """kpi_slug -> a fitted UQEstimator. Defaults to T2.1's generic,
    registry-driven dispatch (bagged-tree/GPR/conformal by registry.json,
    never hardcoded) -- pass estimator_factory=proven6.get_proven_uq_estimator
    to use PROVEN_6's benchmarked methods instead (spec.md §7 item 13).

    Rows with a NaN value for a given KPI are dropped before fitting THAT
    KPI's estimator (checked per-KPI, not once for the whole batch) --
    real case, not hypothetical: T2.10's design deliberately persists every
    KPI a manual round's results file has, leaving the rest as NaN rather
    than discarding rows (spec.md §7 item 12). That means a later round
    ingesting fewer KPIs than a KPI's own dispatch needs will otherwise put
    NaN into that KPI's training target -- caught in production, 5-Sep,
    when a DEMO_4 retrain crashed on exactly this (CatBoost refusing a NaN
    target) for a round whose real results only covered 14 of 20 KPIs."""
    reg = registry if registry is not None else load_registry()
    outputs = reg.get("outputs", {})
    factory = estimator_factory or get_uq_estimator
    X = X_train.to_numpy(dtype=float)

    estimators: Dict[str, Any] = {}
    for slug in kpi_slugs:
        if slug not in outputs:
            raise KeyError(f"{slug!r} not in registry outputs")
        raw_key = outputs[slug]["raw_key"]
        if raw_key not in Y_train.columns:
            raise KeyError(f"{raw_key!r} (for {slug!r}) not in Y_train columns")
        y = Y_train[raw_key].to_numpy(dtype=float)
        mask = ~np.isnan(y)
        if not mask.all():
            dropped = int((~mask).sum())
            X_fit, y_fit = X[mask], y[mask]
        else:
            dropped = 0
            X_fit, y_fit = X, y
        est = factory(slug, reg)
        est.fit(X_fit, y_fit)
        est._n_rows_dropped_for_nan_target = dropped  # surfaced for callers that want to warn on this
        estimators[slug] = est
    return estimators


def compute_trust_scores(
    kpi_slugs: List[str],
    candidates: pd.DataFrame,
    uq_estimators: Dict[str, Any],
    novelty_scorer: NoveltyScorer,
    kpi_scales: Dict[str, float],
) -> Dict[Any, Dict[str, float]]:
    """candidate index -> {kpi_slug: trust_score}. Novelty is per-candidate,
    shared across every KPI for that row (spec.md §5.1) -- computed once,
    not per KPI."""
    X = candidates.to_numpy(dtype=float)
    novelty = novelty_scorer.score(X)

    scores: Dict[Any, Dict[str, float]] = {idx: {} for idx in candidates.index}
    for slug in kpi_slugs:
        result = uq_estimators[slug].predict_with_uncertainty(X)
        widths = result.normalized_width(kpi_scales[slug])
        for i, idx in enumerate(candidates.index):
            scores[idx][slug] = trust_score(float(widths[i]), float(novelty[i]))
    return scores


def calibrate(
    kpi_slugs: List[str],
    calibration_points: pd.DataFrame,
    uq_estimators: Dict[str, Any],
    novelty_scorer: NoveltyScorer,
    kpi_scales: Dict[str, float],
    quantile: float = 0.9,
) -> Dict[str, float]:
    """Per-KPI thresholds (spec.md §7 item 3, mentor-confirmed default),
    calibrated from calibration_points' own trust scores. v0 simplification,
    documented not hidden: calibrates in-sample against the training set
    itself rather than a held-out fold -- fine for a first demonstrative
    pass (spec.md §5.5), a real deployment would use OOF/CV points instead."""
    scores = compute_trust_scores(kpi_slugs, calibration_points, uq_estimators, novelty_scorer, kpi_scales)
    per_kpi_arrays = {
        slug: np.array([scores[idx][slug] for idx in calibration_points.index])
        for slug in kpi_slugs
    }
    return calibrate_thresholds_per_kpi(per_kpi_arrays, quantile=quantile)


def propose_and_flag(
    kpi_slugs: List[str],
    candidate_pool: pd.DataFrame,
    uq_estimators: Dict[str, Any],
    novelty_scorer: NoveltyScorer,
    thresholds: Dict[str, float],
    kpi_scales: Dict[str, float],
    max_batch_size: Optional[int] = None,
) -> Tuple[pd.DataFrame, Dict[Any, TrustDecision]]:
    """Backend-agnostic: scores every candidate, flags per the mentor's
    "any KPI over its own threshold" rule, and caps the flagged set at
    max_batch_size (spec.md §5.3's "cap by DES-run budget") -- takes the
    highest-risk candidates first (max trust score across their flagged
    KPIs), not an arbitrary order, so a capped batch is still the most
    useful one to actually run."""
    if candidate_pool.empty:
        raise ValueError("candidate_pool is empty")

    scores = compute_trust_scores(kpi_slugs, candidate_pool, uq_estimators, novelty_scorer, kpi_scales)
    decisions: Dict[Any, TrustDecision] = {
        idx: decide(scores[idx], thresholds) for idx in candidate_pool.index
    }
    flagged_ids = [idx for idx, d in decisions.items() if d.flagged]
    flagged_ids.sort(key=lambda idx: max(decisions[idx].per_kpi_scores.values()), reverse=True)

    if max_batch_size is not None:
        flagged_ids = flagged_ids[:max_batch_size]

    return candidate_pool.loc[flagged_ids], decisions


def _ingest_and_retrain(
    kpi_slugs: List[str],
    sim_results: pd.DataFrame,
    flagged_batch: pd.DataFrame,
    X_train: pd.DataFrame,
    Y_train: pd.DataFrame,
    registry: Dict[str, Any],
    estimator_factory: Optional[EstimatorFactory] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Shared by both backends: replication-level sim/real results ->
    averaged per candidate -> appended to training data -> every KPI
    estimator refit on the updated data.

    Persists EVERY KPI column present in sim_results, not just kpi_slugs:
    a real AnyLogic run produces all 20 KPI outputs at once regardless of
    which ones this round's loop was scoped to, so the export in this
    manual round throwing away 16 of them would waste real data the
    project explicitly wants to keep for future extension work (spec.md
    §7 item 12). Only the ESTIMATOR retraining below stays scoped to
    kpi_slugs -- the persisted dataset is as complete as what AnyLogic
    actually returned."""
    outputs = registry.get("outputs", {})
    meta_cols = {"run_id", "replication", "seed"}
    available_slugs = [c for c in sim_results.columns if c not in meta_cols]
    unknown = [s for s in available_slugs if s not in outputs]
    if unknown:
        raise KeyError(f"sim_results has columns not in the registry: {unknown}")

    agg = sim_results.groupby("run_id")[available_slugs].mean()

    X_train_new = pd.concat([X_train, flagged_batch.loc[agg.index]])
    new_rows = {outputs[slug]["raw_key"]: agg[slug] for slug in available_slugs}
    Y_train_new = pd.concat([Y_train, pd.DataFrame(new_rows)])

    estimators_new = fit_kpi_estimators(kpi_slugs, X_train_new, Y_train_new, registry, estimator_factory)
    return X_train_new, Y_train_new, estimators_new


def run_loop(
    kpi_slugs: List[str],
    candidate_pool: pd.DataFrame,
    des_backend: DESBackend,
    X_train: pd.DataFrame,
    Y_train: pd.DataFrame,
    registry: Optional[Dict[str, Any]] = None,
    quantile: float = 0.9,
    max_batch_size: int = 10,
    n_replications: int = 5,
    seed: Optional[int] = None,
    estimator_factory: Optional[EstimatorFactory] = None,
) -> Dict[str, Any]:
    """One full propose -> score -> batch -> simulate -> retrain ->
    recalibrate pass against a SYNCHRONOUS backend (SyntheticDESBackend, or
    anything else conforming to DESBackend.simulate()). ManualWorklistDESBackend
    is NOT synchronous -- use export_manual_round()/ingest_manual_round()
    instead (module docstring).

    estimator_factory: defaults to dispatch.get_uq_estimator (DEMO_4's
    mechanism); pass proven6.get_proven_uq_estimator to run this same loop
    against PROVEN_6's benchmarked winning methods instead (§7 item 13).

    Returns a summary: what was flagged, what was simulated, and how each
    flagged candidate's trust score moved after retraining -- the concrete
    evidence spec.md's DoD (§5.5) asks for ("the trust score changes
    sensibly afterward").
    """
    if not kpi_slugs:
        raise ValueError("kpi_slugs is empty")
    reg = registry if registry is not None else load_registry()

    estimators = fit_kpi_estimators(kpi_slugs, X_train, Y_train, reg, estimator_factory)
    novelty_scorer = NoveltyScorer().fit(X_train.to_numpy(dtype=float))
    scales = {
        slug: _kpi_scale(Y_train[reg["outputs"][slug]["raw_key"]].to_numpy(dtype=float))
        for slug in kpi_slugs
    }

    thresholds = calibrate(kpi_slugs, X_train, estimators, novelty_scorer, scales, quantile=quantile)
    flagged_batch, decisions = propose_and_flag(
        kpi_slugs, candidate_pool, estimators, novelty_scorer, thresholds, scales, max_batch_size
    )

    if flagged_batch.empty:
        return {
            "flagged_count": 0,
            "thresholds": thresholds,
            "message": "No candidates flagged at this threshold -- nothing to simulate/retrain.",
        }

    scores_before = compute_trust_scores(kpi_slugs, flagged_batch, estimators, novelty_scorer, scales)

    sim_results = des_backend.simulate(flagged_batch, n_replications=n_replications, seed=seed)
    X_train_new, Y_train_new, estimators_new = _ingest_and_retrain(
        kpi_slugs, sim_results, flagged_batch, X_train, Y_train, reg, estimator_factory
    )

    novelty_scorer_new = NoveltyScorer().fit(X_train_new.to_numpy(dtype=float))
    scales_new = {
        slug: _kpi_scale(Y_train_new[reg["outputs"][slug]["raw_key"]].to_numpy(dtype=float))
        for slug in kpi_slugs
    }
    scores_after = compute_trust_scores(kpi_slugs, flagged_batch, estimators_new, novelty_scorer_new, scales_new)

    return {
        "flagged_count": len(flagged_batch),
        "flagged_ids": list(flagged_batch.index),
        "thresholds": thresholds,
        "scores_before": scores_before,
        "scores_after": scores_after,
        "n_training_rows_before": len(X_train),
        "n_training_rows_after": len(X_train_new),
        "X_train": X_train_new,
        "Y_train": Y_train_new,
        "estimators": estimators_new,
    }


def export_manual_round(
    kpi_slugs: List[str],
    candidate_pool: pd.DataFrame,
    manual_backend: Any,
    out_path: Path,
    X_train: pd.DataFrame,
    Y_train: pd.DataFrame,
    registry: Optional[Dict[str, Any]] = None,
    quantile: float = 0.9,
    max_batch_size: int = 10,
    n_replications: int = 5,
    seed: Optional[int] = None,
    estimator_factory: Optional[EstimatorFactory] = None,
) -> Dict[str, Any]:
    """propose -> score -> batch -> export. Produces both artifacts
    (spec.md §7 item 11): the canonical flat CSV request record
    (out_path with a .csv suffix) and the human-followable Excel worksheet
    (out_path with a .xlsx suffix) -- same flagged batch, two views. Returns
    the flagged batch + everything ingest_manual_round() needs later, since
    the loop can't complete synchronously (§7 item 9 -- manual entry only).

    estimator_factory: see run_loop() -- defaults to DEMO_4's dispatch,
    pass proven6.get_proven_uq_estimator for PROVEN_6."""
    reg = registry if registry is not None else load_registry()
    estimators = fit_kpi_estimators(kpi_slugs, X_train, Y_train, reg, estimator_factory)
    novelty_scorer = NoveltyScorer().fit(X_train.to_numpy(dtype=float))
    scales = {
        slug: _kpi_scale(Y_train[reg["outputs"][slug]["raw_key"]].to_numpy(dtype=float))
        for slug in kpi_slugs
    }
    thresholds = calibrate(kpi_slugs, X_train, estimators, novelty_scorer, scales, quantile=quantile)
    flagged_batch, decisions = propose_and_flag(
        kpi_slugs, candidate_pool, estimators, novelty_scorer, thresholds, scales, max_batch_size
    )
    if flagged_batch.empty:
        return {"flagged_count": 0, "thresholds": thresholds, "csv_path": None, "worklist_path": None}

    out_path = Path(out_path)
    csv_path = manual_backend.export_run_requests_csv(
        flagged_batch, n_replications=n_replications, seed=seed, out_path=out_path.with_suffix(".csv")
    )
    worklist_path = manual_backend.export_worklist(flagged_batch, out_path.with_suffix(".xlsx"))
    return {
        "flagged_count": len(flagged_batch),
        "flagged_batch": flagged_batch,
        "thresholds": thresholds,
        "csv_path": csv_path,
        "worklist_path": worklist_path,
    }


def ingest_manual_round(
    kpi_slugs: List[str],
    results_path: Path,
    manual_backend: Any,
    flagged_batch: pd.DataFrame,
    X_train: pd.DataFrame,
    Y_train: pd.DataFrame,
    registry: Optional[Dict[str, Any]] = None,
    estimator_factory: Optional[EstimatorFactory] = None,
) -> Dict[str, Any]:
    """The other half of the manual round: real AnyLogic Cloud results ->
    retrain -> recalibrate. Call once the human running AnyLogic Cloud
    brings back their Excel export.

    estimator_factory: see run_loop() -- must match whatever export_manual_round()
    used for this round, or retraining will silently switch UQ mechanism."""
    reg = registry if registry is not None else load_registry()
    sim_results = manual_backend.ingest_results(results_path)
    X_train_new, Y_train_new, estimators_new = _ingest_and_retrain(
        kpi_slugs, sim_results, flagged_batch, X_train, Y_train, reg, estimator_factory
    )
    return {
        "n_training_rows_before": len(X_train),
        "n_training_rows_after": len(X_train_new),
        "X_train": X_train_new,
        "Y_train": Y_train_new,
        "estimators": estimators_new,
    }
