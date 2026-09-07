"""
T2.4 -- Novelty/OOD scorer: distance to the 35-dim NOLHC training hull.

Combines two independent signals per spec.md item 7's recommendation
("I'd lean toward both... since they can disagree in informative ways"):

  1. IsolationForest on the raw 35-dim input space (structural OOD test).
  2. GP epistemic std from T2.2's ground-truth surface, where available
     (a second, geometry-independent signal for the 3 T2.2 KPIs).

Verified finding (independently reproduced, not assumed): IsolationForest
misses single-dimension excursions at d=35 (a value pushed to 20x its
observed max barely moves the score) but correctly flags a genuinely
multi-dimensional excursion. GP-std does NOT share this blind spot -- it
inflates correctly even for a single pushed dimension (see demo below).
This is exactly the kind of disagreement worth combining rather than
picking one method.
"""
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest


class NoveltyScorer:
    def __init__(self, X_train: np.ndarray, gp_artifact_path: str | None = None,
                 contamination="auto", random_state=42):
        self.iso = IsolationForest(contamination=contamination, random_state=random_state,
                                    n_estimators=200).fit(X_train)
        self.gp_artifact = joblib.load(gp_artifact_path) if gp_artifact_path else None

    def score(self, x_row: np.ndarray, kpi: str | None = None) -> dict:
        x_row = np.asarray(x_row, dtype=float).reshape(1, -1)
        iso_decision = float(self.iso.decision_function(x_row)[0])  # <0 = anomaly
        iso_flag = bool(self.iso.predict(x_row)[0] == -1)

        gp_std = None
        if self.gp_artifact is not None and kpi is not None and kpi in self.gp_artifact["kpis"]:
            scaler = self.gp_artifact["scaler"]
            gp = self.gp_artifact["kpis"][kpi]["gp"]
            _, std = gp.predict(scaler.transform(x_row), return_std=True)
            gp_std = float(std[0])

        return {
            "isolation_forest_decision": iso_decision,
            "isolation_forest_flag": iso_flag,
            "gp_epistemic_std": gp_std,
            # simple combined flag: either signal firing counts as "novel"
            "novel_by_either_signal": iso_flag or (gp_std is not None and gp_std > 30.0),
        }


if __name__ == "__main__":
    X = pd.read_csv("/tmp/build/X_129.csv").drop(columns=["factor name"]).values
    scorer = NoveltyScorer(X, gp_artifact_path="/tmp/build/loop/des_backend/ground_truth_gps.joblib")

    x0 = X[0].copy()
    x_single_20x = x0.copy(); x_single_20x[0] = X[:, 0].max() * 20.0
    x_all_3x = X.max(axis=0) * 3.0

    for label, x in [("in-sample point", x0),
                      ("single dim -> 20x max", x_single_20x),
                      ("ALL 35 dims -> 3x max", x_all_3x)]:
        r = scorer.score(x, kpi="TT_IB_LB")
        print(f"{label:25s}  iso_decision={r['isolation_forest_decision']:+.4f}  "
              f"iso_flag={r['isolation_forest_flag']!s:5s}  "
              f"gp_std={r['gp_epistemic_std']:.2f}  "
              f"novel_by_either={r['novel_by_either_signal']}")
