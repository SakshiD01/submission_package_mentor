"""
Adapter: T2.2's fitted GP ground-truth artifact (fit_ground_truth.py) ->
the ``ground_truth_fns``/``noise_std`` dependencies ``SyntheticDESBackend``
(synthetic.py, spec.md §5.2) expects. This is the seam T2.5 was built
against from the start -- ground truth is injected, not fit internally --
so wiring T2.2's real output in is a small adapter, not a redesign.

Key names: fit_ground_truth.py's KPI_MAP uses NOLHC's display names
("TT_OB_Agri"); SyntheticDESBackend / dispatch.py / kpi_scope.py use
registry slugs ("tt_ob_agri"). This module is the one place that
translates between them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import joblib

from .synthetic import GroundTruthFn

_HERE = Path(__file__).resolve().parent
DEFAULT_ARTIFACT_PATH = _HERE / "ground_truth_gps.joblib"


def load_ground_truth_artifact(path: Optional[Path] = None) -> Dict:
    art_path = Path(path) if path is not None else DEFAULT_ARTIFACT_PATH
    if not art_path.is_file():
        raise FileNotFoundError(
            f"Missing T2.2 ground-truth artifact: {art_path}. "
            "Run fit_ground_truth.py first, or pass an explicit path=... for tests."
        )
    return joblib.load(art_path)


def _make_gp_fn(gp, scaler) -> GroundTruthFn:
    """Closes over one fitted GP -- batch predict, matching GroundTruthFn's
    (n, 35) -> (n,) contract (T2.2's own SyntheticGroundTruth.run() was
    single-row; SyntheticDESBackend.simulate() calls ground truth per
    candidate row internally, so a batch-shaped fn works either way)."""

    def _fn(X: np.ndarray) -> np.ndarray:
        Xs = scaler.transform(np.asarray(X, dtype=float))
        return gp.predict(Xs)

    return _fn


def ground_truth_fns_and_noise(
    artifact: Optional[Dict] = None,
) -> Tuple[Dict[str, GroundTruthFn], Dict[str, float]]:
    """T2.2 artifact -> (ground_truth_fns, noise_std), both keyed by lowercase
    registry slug (e.g. "tt_ob_agri"), ready to pass straight into
    SyntheticDESBackend(kpi_slugs=..., ground_truth_fns=..., noise_std=...).

    Only covers the KPIs T2.2 actually fit -- currently {tt_ob_agri,
    tt_ib_lb, uti_dafm_r}. Note this is NOT all of DEMO_4: wt_ob_a_gb_ross
    and tt_ib_dr (the two conformal-fallback KPIs in DEMO_4, incl. the
    known-bad stress test) have no ground-truth GP yet -- a SyntheticDESBackend
    built from this function's output can only simulate the 3 KPIs listed
    above, not the full DEMO_4 set, until that gap is resolved (spec.md §7).
    """
    art = artifact if artifact is not None else load_ground_truth_artifact()
    scaler = art["scaler"]

    ground_truth_fns: Dict[str, GroundTruthFn] = {}
    noise_std: Dict[str, float] = {}
    for short_name, entry in art["kpis"].items():
        slug = short_name.lower()
        ground_truth_fns[slug] = _make_gp_fn(entry["gp"], scaler)
        noise_std[slug] = float(entry["noise_std"])

    return ground_truth_fns, noise_std
