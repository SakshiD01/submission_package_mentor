"""
PROVEN_6 recalibration check (spec.md §9 follow-up, 5-Sep 2026).

Answers a real question raised mid-freeze: as the training dataset keeps
growing via the batch-sequential loop (129 -> 139 -> 169 rows so far), does
UQ_Method_Benchmark.xlsx's per-family method choice -- fixed 1-Sep on a
103/26 split, mentor-reviewed, hardcoded into proven6.PROVEN_METHOD -- stay
the winner, or could a bigger held-out set favour a different method?

This module answers that WITHOUT auto-changing anything. It re-runs the same
kind of held-out coverage comparison the original benchmark used against
whatever dataset_store.load_current_training_data() currently returns, for
every PROVEN_6 KPI, using the same UQEstimator classes already fitted and
tested elsewhere (BaggedTreeJackknife, GPRNative, ConformalFallback,
MapieCVPlus) -- no new UQ logic, just orchestration + comparison.

Split mechanism: sklearn's own `train_test_split(test_size=0.2,
random_state=42)` -- confirmed, not assumed, against UQ_Method_Benchmark.xlsx
itself. This repo's own splits.train_test_indices() (a permutation-based
80/20 split, different algorithm despite the same seed/fraction) was tried
first and does NOT reproduce the workbook's numbers -- on wt_ob_lb (still
exactly 129 rows, nothing has changed for this KPI, see below) it gave
84.6%/65.4% coverage for native/conformal GPR where the workbook's real
numbers are 96.2%/92.3%. Switching to sklearn's own split reproduces both
to 3+ decimal places (see check_kpi()'s inline note). This mismatch is
exactly why the recalibration check has to be validated against a KPI whose
data HASN'T changed before trusting what it says about the ones that have.

Policy this embodies (write into spec.md alongside it):
  - Re-benchmarking is a periodic CHECK, not something that runs on every
    single ingested round -- coverage on a small held-out set is noisy
    (spec.md §7 item 14's Wilson-CI point applies here too), so re-running
    reflexively would risk flip-flopping on noise, not real signal.
  - A check that finds a DIFFERENT winner than PROVEN_METHOD does NOT
    auto-apply it. It's surfaced as "REVIEW NEEDED" for the same kind of
    mentor sign-off the original decision went through -- proven6.py's
    routing table is a reviewed decision, not a cache to invalidate silently.
  - This is the mechanism a future fully-automated loop (no manual AnyLogic
    copy-paste) would run on a schedule (e.g. every N accepted rounds, or
    at defined dataset-size milestones) instead of a human remembering to
    ask "should we re-check?" -- same propose-then-human-decides pattern
    already used for individual candidate points, one level up, applied to
    method selection instead.

Also surfaces something the growth history itself created: PROVEN_6's 6
KPIs have NOT all grown equally. wt_ob_lb has zero real AnyLogic Cloud
support (WT_OB_LB has no known raw field, item 5's finding) -- its 129
training rows are unchanged by either real round. wt_ob_a_gb_dub picked up
30 real rows (item 17) but not the first round's 10 (item 15's exclusion).
Only tt_ob_lb, uti_cus_r, wt_ib_na_ross, tt_ib_lb are genuinely at 169. This
module reports each KPI's actual n, not an assumed shared 169, so that
distinction is visible rather than papered over.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

from . import dataset_store
from .proven6 import PROVEN_6, PROVEN_METHOD, PROVEN_REGISTERED_AS_OVERRIDE
from .uq.conformal_fallback import ConformalFallback
from .uq.dispatch import load_registry
from .uq.gpr_native import GPRNative
from .uq.mapie_cv_plus import MapieCVPlus
from .uq.tree_native import BaggedTreeJackknife

TARGET_COVERAGE = 0.90

METHOD_LABELS: Dict[str, str] = {
    "bagged_tree_native": "native ensemble-SD (bagging variance)",
    "gpr_native": "native GPR posterior SD",
    "conformal_fallback": "split conformal",
    "mapie_cv_plus": "CV+ / jackknife+ (mapie)",
}


def _candidate_methods_for(registered_as: str) -> Dict[str, Any]:
    """Every UQEstimator mechanism applicable to this family -- native path
    (if one exists for this family) plus both fallback mechanisms. The
    hand-rolled bootstrap-ensemble candidate from the original 1-Sep
    benchmark lost in every family and was never committed as a class
    (reports/README.md) -- not reproduced here for that reason, not an
    oversight."""
    methods: Dict[str, Any] = {}
    if registered_as in ("extra_trees", "random_forest"):
        methods["bagged_tree_native"] = BaggedTreeJackknife
    if registered_as in ("gpr_rbf", "gpr_matern"):
        methods["gpr_native"] = GPRNative
    methods["conformal_fallback"] = ConformalFallback
    methods["mapie_cv_plus"] = MapieCVPlus
    return methods


@dataclass
class MethodResult:
    method: str
    coverage: float
    mean_width: float
    rmse: float


@dataclass
class KPICheck:
    kpi_slug: str
    registered_as: str
    n_train: int
    n_test: int
    current_method: str
    results: List[MethodResult] = field(default_factory=list)
    recommended_method: str = ""
    changed: bool = False


def _coverage(y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    return float(np.mean((y_true >= lower) & (y_true <= upper)))


def check_kpi(kpi_slug: str, X: np.ndarray, y: np.ndarray, registry: Dict[str, Any]) -> KPICheck:
    """Re-run every applicable UQEstimator for this KPI's family on the
    CURRENT dataset's own 80/20 split, and report which one is closest to
    the 90% coverage target now -- without touching PROVEN_METHOD."""
    registered_as = PROVEN_REGISTERED_AS_OVERRIDE.get(
        kpi_slug, registry["outputs"][kpi_slug]["registered_as"]
    )
    # sklearn's train_test_split(test_size=0.2, random_state=42) -- confirmed,
    # not assumed, to be the original benchmark's exact split mechanism: on
    # wt_ob_lb's unchanged 129 rows this reproduces UQ_Method_Benchmark.xlsx's
    # native-GPR (96.2% coverage, width 0.7055) and conformalized-GPR (92.3%,
    # width 0.7061) numbers to 3+ decimal places. This repo's OWN
    # splits.train_test_indices() (a permutation-based split, different
    # algorithm despite the same seed/fraction) does NOT reproduce them --
    # tried first, gave 84.6%/65.4% on the same unchanged KPI, which is what
    # exposed that the two split mechanisms disagree. Matching the original
    # exactly here is what makes this check's "REVIEW NEEDED" flags mean
    # something, rather than just measuring a different, unvalidated method.
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results: List[MethodResult] = []
    for method_name, cls in _candidate_methods_for(registered_as).items():
        est = cls(kpi_slug=kpi_slug, registered_as=registered_as)
        est.fit(X_train, y_train)
        pred = est.predict_with_uncertainty(X_test)
        cov = _coverage(y_test, pred.lower, pred.upper)
        width = float(np.mean(pred.upper - pred.lower))
        rmse = float(np.sqrt(mean_squared_error(y_test, pred.mean)))
        results.append(MethodResult(method_name, cov, width, rmse))

    # Same tie-break the original benchmark used in prose (closest to the
    # 90% target, narrower interval breaks ties) -- not separately re-derived
    # per-family since it's a fixed, KPI-independent rule.
    best = min(results, key=lambda r: (abs(r.coverage - TARGET_COVERAGE), r.mean_width))
    current = PROVEN_METHOD[kpi_slug]
    return KPICheck(
        kpi_slug=kpi_slug,
        registered_as=registered_as,
        n_train=len(X_train),
        n_test=len(X_test),
        current_method=current,
        results=results,
        recommended_method=best.method,
        changed=(best.method != current),
    )


def run_recalibration_check(registry: Optional[Dict[str, Any]] = None) -> List[KPICheck]:
    """One check per PROVEN_6 KPI against dataset_store's CURRENT training
    data -- whatever that is at call time, no hardcoded row count."""
    reg = registry if registry is not None else load_registry()
    X_df, Y_df = dataset_store.load_current_training_data()
    checks: List[KPICheck] = []
    for kpi in PROVEN_6:
        raw_key = reg["outputs"][kpi]["raw_key"]
        y_full = Y_df[raw_key].to_numpy(dtype=float)
        mask = ~np.isnan(y_full)
        X = X_df.to_numpy(dtype=float)[mask]
        y = y_full[mask]
        checks.append(check_kpi(kpi, X, y, reg))
    return checks
