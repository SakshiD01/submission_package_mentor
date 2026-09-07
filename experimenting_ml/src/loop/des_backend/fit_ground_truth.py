"""
T2.2 (Sakshi, 25-Aug-2026) — ground-truth GP surface + noise model for the
synthetic DES benchmark, spec.md §5.2.

This is a re-hosted, repo-runnable copy of Sakshi's original delivery
(``docs/T2.2_synthetic_des_backend_code.zip``, same file name). The recipe --
kernel, KPI_MAP, NOISE_FRACTION, random_state -- is unchanged from her
version; only the data-loading and output paths differ, for two reasons:

1. Her ``ground_truth_gps.joblib`` was pickled under numpy >=2.0 (references
   ``numpy._core``, which only exists there), but this repo's committed
   ``experimenting_ml/.venv`` runs numpy 1.24.4 / Python 3.8 -- numpy 2.x
   dropped Python 3.8 support, so the artifact can't load here. Forcing a
   cross-major-version numpy unpickle is fragile even when it "works", so
   this script re-fits from the same recipe instead of patching the pickle.
2. Her script read from ``/tmp/build/X_129.csv`` / ``/tmp/build/Y_129.csv``
   (her own local export); this one uses ``data.load_xy()``, the same
   129x35x20 NOLHC loader every other module in this repo uses. Verified
   before wiring this in: value ranges/means for all 3 KPIs match her
   ``ground_truth_summary.json`` exactly (same underlying xlsx, just a
   different column-naming convention on load) -- see spec.md §7.

Scope note (flagged, not silently resolved): DEMO_4 (kpi_scope.py) is
{tt_ob_agri, uti_dafm_r, wt_ob_a_gb_ross, tt_ib_dr} -- one KPI per dispatch
path. Sakshi's KPI_MAP below only overlaps on 2 of those 4 (tt_ob_agri,
uti_dafm_r) and adds tt_ib_lb, which is not in DEMO_4. wt_ob_a_gb_ross and
tt_ib_dr -- specifically chosen to exercise the conformal-fallback path,
including the known-bad stress test -- have no ground-truth GP yet. Team
decision needed (spec.md §7): extend KPI_MAP to cover the missing two, or
adjust DEMO_4. Not decided in this file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.preprocessing import StandardScaler

_HERE = Path(__file__).resolve().parent
_EXPERIMENTING_SRC = _HERE.parents[1]
if str(_EXPERIMENTING_SRC) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTING_SRC))

from data import load_xy  # noqa: E402

# short_name -> (raw_key in load_xy()'s Y columns, CV-selected model family, CV RMSE)
# CV RMSE source: experimenting_ml/docs/CV_Best_Models_Per_Target.md (verified
# against this repo's own copy, 26-Aug-2026 -- matches Sakshi's quoted values exactly).
KPI_MAP = {
    "TT_OB_Agri": ("TT_OB_Agri", "ExtraTrees", 7.3009),
    "TT_IB_LB": ("TT_IB_LB", "GPR_Matern", 21.4914),
    "Uti_DAFM_R": ("Uti_DAFM_R", "GPR_Matern", 0.0104),
}

NOISE_FRACTION = 0.15  # documented assumption (spec.md §7) -- not a measured replication variance


def fit_all(output_dir: Path | None = None) -> dict:
    out_dir = output_dir or _HERE
    X_df, Y_df = load_xy()
    assert X_df.shape == (129, 35), X_df.shape
    assert Y_df.shape == (129, 20), Y_df.shape

    scaler = StandardScaler().fit(X_df.to_numpy(dtype=float))
    Xs = scaler.transform(X_df.to_numpy(dtype=float))

    results = {}
    artifacts = {"scaler": scaler, "kpis": {}}

    for short, (raw_key, family, cv_rmse) in KPI_MAP.items():
        y = Y_df[raw_key].to_numpy(dtype=float)
        kernel = ConstantKernel(1.0, (1e-2, 1e3)) * Matern(
            length_scale=1.0, length_scale_bounds=(1e-2, 1e2), nu=1.5
        ) + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-8, 1e2))
        gp = GaussianProcessRegressor(
            kernel=kernel, normalize_y=True, n_restarts_optimizer=8, random_state=42
        )
        gp.fit(Xs, y)

        y_hat, _ = gp.predict(Xs, return_std=True)
        in_sample_rmse = float(np.sqrt(np.mean((y_hat - y) ** 2)))
        noise_std = NOISE_FRACTION * cv_rmse

        results[short] = {
            "raw_key": raw_key,
            "cv_selected_family": family,
            "cv_rmse_source": cv_rmse,
            "gp_kernel_fitted": str(gp.kernel_),
            "gp_log_marginal_likelihood": float(gp.log_marginal_likelihood_value_),
            "in_sample_rmse": in_sample_rmse,
            "y_range": [float(y.min()), float(y.max())],
            "y_mean": float(y.mean()),
            "injected_noise_std": noise_std,
            "injected_noise_pct_of_range": float(noise_std / (y.max() - y.min())),
        }
        artifacts["kpis"][short] = {"gp": gp, "noise_std": noise_std, "raw_key": raw_key}
        print(
            f"{short:12s} family={family:12s} kernel={gp.kernel_}  "
            f"in-sample RMSE={in_sample_rmse:.4f}  noise_std={noise_std:.4f}"
        )

    joblib.dump(artifacts, out_dir / "ground_truth_gps.joblib")
    with open(out_dir / "ground_truth_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out_dir / 'ground_truth_gps.joblib'}, {out_dir / 'ground_truth_summary.json'}")
    return results


if __name__ == "__main__":
    fit_all()
