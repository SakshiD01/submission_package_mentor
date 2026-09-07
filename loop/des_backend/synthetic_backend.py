"""
T2.2 deliverable — reference implementation Nila's SyntheticDESBackend (T2.5)
can import directly. Loads the fitted GP ground-truth surfaces + noise model
from ground_truth_gps.joblib and exposes a "run DES" call for a candidate
input vector, scoped to the 3 KPIs in KPI_MAP (fit_ground_truth.py).

Usage:
    from synthetic_backend import SyntheticGroundTruth
    sgt = SyntheticGroundTruth("ground_truth_gps.joblib")
    result = sgt.run(x_candidate, kpi="TT_IB_LB", n_replications=1, seed=0)
    # result = {"mean": <GP posterior mean>, "gp_std": <epistemic std>,
    #           "replications": [<noisy samples>], "replication_mean": ...}
"""
import joblib
import numpy as np


class SyntheticGroundTruth:
    def __init__(self, artifact_path: str):
        art = joblib.load(artifact_path)
        self.scaler = art["scaler"]
        self.kpis = art["kpis"]  # short_name -> {"gp":..., "noise_std":..., "y_column":...}

    def run(self, x_row: np.ndarray, kpi: str, n_replications: int = 1, seed: int | None = None):
        """Emulate a DES call: GP posterior mean/std (metamodel uncertainty)
        plus `n_replications` independent noisy draws (stand-in for DES
        replication noise -- see spec doc, Noise model, for the caveat on
        what this noise represents)."""
        if kpi not in self.kpis:
            raise ValueError(f"kpi must be one of {list(self.kpis)}, got {kpi!r}")
        entry = self.kpis[kpi]
        gp, noise_std = entry["gp"], entry["noise_std"]

        x_row = np.asarray(x_row, dtype=float).reshape(1, -1)
        xs = self.scaler.transform(x_row)
        mean, gp_std = gp.predict(xs, return_std=True)
        mean, gp_std = float(mean[0]), float(gp_std[0])

        rng = np.random.default_rng(seed)
        reps = (mean + rng.normal(0.0, noise_std, size=n_replications)).tolist()
        return {
            "kpi": kpi,
            "mean": mean,               # GP posterior mean = "true" surface value
            "gp_std": gp_std,           # epistemic uncertainty (far from training data -> large)
            "replications": reps,       # simulated noisy DES-like outputs
            "replication_mean": float(np.mean(reps)),
        }


if __name__ == "__main__":
    import pandas as pd
    X = pd.read_csv("/tmp/build/X_129.csv").drop(columns=["factor name"])
    sgt = SyntheticGroundTruth("/tmp/build/loop/des_backend/ground_truth_gps.joblib")

    # demo: an in-sample point (should be close to the real recorded value)
    x0 = X.iloc[0].values
    print("In-sample candidate (row 0):", sgt.run(x0, kpi="TT_IB_LB", n_replications=5, seed=1))

    # demo: an out-of-hull candidate (push one input far outside its observed range)
    x_ood = X.iloc[0].values.copy()
    col_idx = 0
    x_ood[col_idx] = X.iloc[:, col_idx].max() * 3.0
    print("\nOut-of-hull candidate (input 0 pushed to 3x observed max):",
          sgt.run(x_ood, kpi="TT_IB_LB", n_replications=5, seed=1))
