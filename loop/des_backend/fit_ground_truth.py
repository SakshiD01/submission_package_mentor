"""
T2.2 — Ground-truth GP surface + noise model for the synthetic DES benchmark.
Scope: 3 representative KPIs (spec.md 5.2 / Final_Spec.docx 5.2), not all 20.

Fits one GP per chosen KPI on the full 129-run NOLHC sample (X: 35 inputs,
Y: 1 KPI), to stand in for "run the real AnyLogic DES" cheaply. A candidate
input vector is scored by the GP posterior mean, and a synthetic replicate
is produced by adding injected noise (see NOISE MODEL below).

Source data: nolhc_ml/data/raw/nolhc_runs.xlsx (ExpValues / SimResults),
the same raw file the original 129-run benchmark was built from.
"""
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
from sklearn.preprocessing import StandardScaler

X = pd.read_csv("/tmp/build/X_129.csv")
Y = pd.read_csv("/tmp/build/Y_129.csv")
X = X.drop(columns=["factor name"])
assert X.shape == (129, 35), X.shape
assert Y.shape == (129, 20), Y.shape

# --- KPI selection: 3 representative targets spanning the engine's actual
# model-family mix (see selection rationale in the accompanying spec doc) ---
KPI_MAP = {
    # short_name -> (full Y column, CV-selected model family, CV RMSE)
    # source: experimenting_ml/docs/CV_Best_Models_Per_Target.md
    "TT_OB_Agri": ("Agri Products | Outbound | TT_OB_Agri", "ExtraTrees", 7.3009),
    "TT_IB_LB":   ("Routes | Landbridge | TT_IB_LB", "GPR_Matern", 21.4914),
    "Uti_DAFM_R": ("Staff Utilisation | Rooslare | Uti_DAFM_R", "GPR_Matern", 0.0104),
}

NOISE_FRACTION = 0.15  # documented assumption, see spec doc section "Noise model"

scaler = StandardScaler().fit(X.values)
Xs = scaler.transform(X.values)

results = {}
artifacts = {"scaler": scaler, "kpis": {}}

for short, (col, family, cv_rmse) in KPI_MAP.items():
    y = Y[col].values.astype(float)
    kernel = ConstantKernel(1.0, (1e-2, 1e3)) * Matern(length_scale=1.0, length_scale_bounds=(1e-2, 1e2), nu=1.5) \
             + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-8, 1e2))
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=8, random_state=42)
    gp.fit(Xs, y)

    # in-sample fit quality (diagnostic only -- this GP is a ground-truth
    # stand-in, not a held-out-validated production model; see spec doc)
    y_hat, y_std = gp.predict(Xs, return_std=True)
    in_sample_rmse = float(np.sqrt(np.mean((y_hat - y) ** 2)))

    noise_std = NOISE_FRACTION * cv_rmse

    results[short] = {
        "y_column": col,
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
    artifacts["kpis"][short] = {"gp": gp, "noise_std": noise_std, "y_column": col}
    print(f"{short:12s} family={family:12s} kernel={gp.kernel_}  in-sample RMSE={in_sample_rmse:.4f}  noise_std={noise_std:.4f}")

joblib.dump(artifacts, "/tmp/build/loop/des_backend/ground_truth_gps.joblib")
with open("/tmp/build/loop/des_backend/ground_truth_summary.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nSaved: ground_truth_gps.joblib, ground_truth_summary.json")
