"""
Full DEMO_4 ground truth for SyntheticDESBackend (spec.md §7 items 4 & 6,
decided 26-Aug-2026): per KPI, use whichever ground-truth surface is the
more faithful stand-in, not "always fit a GP" uniformly.

  - GPR-won KPI (uti_dafm_r): T2.2's fitted GP (fit_ground_truth.py,
    Sakshi) -- her own 5-fold CV validated this closely matches the
    production model's own CV RMSE (0.0109 vs 0.0104), unsurprising since
    the real winner is already a GP.
  - Non-GPR-won KPIs (tt_ob_agri, wt_ob_a_gb_ross, tt_ib_dr): the already-
    trained PRODUCTION model itself (nolhc_ml/models/v1/model_<slug>.pkl +
    scaler_X.pkl), not a forced GP. Sakshi's T2.2 validation showed a GP
    forced onto tt_ob_agri (ExtraTrees-won) is ~3x worse (GP-surface 5-fold
    CV RMSE 22.4 vs. the production model's own 7.3) than just using the
    real production model as ground truth. Team decision 26-Aug: generalise
    that finding to every non-GPR DEMO_4 winner (wt_ob_a_gb_ross is
    CatBoost-won, tt_ib_dr is Stacking-won -- both tree/ensemble families a
    smooth isotropic GP has no reason to fit well either) rather than force
    a GP onto response surfaces already known not to be GP-shaped. This
    also means wt_ob_a_gb_ross/tt_ib_dr need no new GP fit at all -- the
    trained production models already exist and load cleanly in this venv
    (verified 26-Aug: same numpy 1.24.4/sklearn 1.3.2 as nolhc_ml's own,
    unlike Sakshi's original .joblib -- see ground_truth_gp.py's docstring).

Snapshot caveat (same pattern Sakshi flagged for tt_ib_lb in her T2.2 note):
noise_std for wt_ob_a_gb_ross/tt_ib_dr uses the CV RMSE from
experimenting_ml/docs/CV_Best_Models_Per_Target.md, which names a different
winning family (GradientBoosting / SVR_RBF) than nolhc_ml/models/v1's own
registry.json (CatBoost / Stacking-with-knn-best-individual) -- different
pipeline snapshots, close-but-not-identical numbers, same unresolved
discrepancy pattern already noted elsewhere in this repo. Used anyway, for
the same reason Sakshi used it: it's the one file with a CV RMSE for all 20
KPIs from a single consistent run. Not blocking; worth reconciling at some
point (spec.md §7 item 1's sibling issue).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np

from .ground_truth_gp import ground_truth_fns_and_noise as _gp_fns_and_noise
from .synthetic import GroundTruthFn

_REPO_ROOT = Path(__file__).resolve().parents[4]
_NOLHC_MODELS = _REPO_ROOT / "nolhc_ml" / "models" / "v1"

# slug -> CV RMSE, source: experimenting_ml/docs/CV_Best_Models_Per_Target.md
# (verified 26-Aug against this repo's own copy of that file)
_PRODUCTION_KPI_CV_RMSE = {
    "tt_ob_agri": 7.3009,
    "wt_ob_a_gb_ross": 0.0241,
    "tt_ib_dr": 0.2056,
}
NOISE_FRACTION = 0.15  # same documented assumption as fit_ground_truth.py (spec.md §7 item 5)


def _make_production_fn(model, scaler) -> GroundTruthFn:
    def _fn(X: np.ndarray) -> np.ndarray:
        return model.predict(scaler.transform(np.asarray(X, dtype=float)))

    return _fn


def _load_production_ground_truth(slug: str, scaler) -> Tuple[GroundTruthFn, float]:
    model_path = _NOLHC_MODELS / f"model_{slug}.pkl"
    if not model_path.is_file():
        raise FileNotFoundError(f"No production model for {slug!r}: {model_path}")
    model = joblib.load(model_path)
    cv_rmse = _PRODUCTION_KPI_CV_RMSE[slug]
    return _make_production_fn(model, scaler), NOISE_FRACTION * cv_rmse


def ground_truth_fns_and_noise_for_demo4() -> Tuple[Dict[str, GroundTruthFn], Dict[str, float]]:
    """Full DEMO_4 ground truth (spec.md §7 item 6, resolved 26-Aug):
    {tt_ob_agri, uti_dafm_r, wt_ob_a_gb_ross, tt_ib_dr} -> (fn, noise_std),
    one KPI per dispatch path -- ready to pass straight into
    SyntheticDESBackend(kpi_slugs=DEMO_4, ground_truth_fns=..., noise_std=...).
    """
    gp_fns, gp_noise = _gp_fns_and_noise()  # currently {tt_ob_agri, tt_ib_lb, uti_dafm_r}
    scaler = joblib.load(_NOLHC_MODELS / "scaler_X.pkl")

    fns: Dict[str, GroundTruthFn] = {"uti_dafm_r": gp_fns["uti_dafm_r"]}
    noise: Dict[str, float] = {"uti_dafm_r": gp_noise["uti_dafm_r"]}

    for slug in ("tt_ob_agri", "wt_ob_a_gb_ross", "tt_ib_dr"):
        fn, n = _load_production_ground_truth(slug, scaler)
        fns[slug] = fn
        noise[slug] = n

    return fns, noise
