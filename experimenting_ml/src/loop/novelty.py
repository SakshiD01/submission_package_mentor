"""
Novelty/OOD scorer (spec.md §5.1, §4.1 item 5): how far a candidate point
sits from the 35-dim NOLHC training hull.

Uses sklearn.ensemble.IsolationForest rather than hand-rolled Mahalanobis
distance -- at n=129, d=35 a full covariance matrix needs careful shrinkage
to stay numerically stable, and IsolationForest (one of the methods spec.md
§4.1 item 5 already names) avoids that risk under deadline pressure. Mahalanobis
stays a documented future alternative, not a v0 requirement.

T2.4 (27-Aug-2026): implemented ahead of Sakshi's 27-28 Aug slot to de-risk
the 1-Sep freeze (T2.6/T2.7/T2.8 all sit downstream of this) -- flagged for
her review once she's free, same pattern as the T2.2 ground-truth decisions.

Scope note, not silently smoothed over: Sakshi's T2.2 write-up suggested
combining IsolationForest with the ground-truth GP's own `gp_std` as a
second, cross-checked novelty signal. That doesn't generalise cleanly
anymore -- the 26-Aug ground-truth decision (spec.md §7 item 4) means only
`uti_dafm_r` (1 of DEMO_4's 4 KPIs) actually has a fitted GP; the other 3
use production models directly and have no `gp_std` to offer. `novelty_term`
in trust.py is deliberately per-CANDIDATE, shared across every KPI for that
candidate (unlike the per-KPI UQ term) -- a signal available for only 1 of 4
KPIs can't be the mechanism without breaking that symmetry. IsolationForest,
fit once on the 35-dim input space, works uniformly regardless of which
ground truth backs each KPI, so it's the sole v0 mechanism here. Folding
gp_std back in as a *bonus* signal for uti_dafm_r specifically is a
reasonable stretch idea, not required for demo-4 sign-off.

Sign/scale convention (this is the one design choice, not free): trust.py's
trust_score() requires novelty_term >= 0 and adds it directly to the UQ
term. IsolationForest's own decision_function(X) is centred at ~0 by
construction (sklearn's contamination-based offset), positive for
"normal"/inlier points and negative for outliers. score() below returns
max(0, -decision_function(X)) -- so a typical in-hull candidate scores
exactly 0 (no novelty penalty), and the penalty grows the further a point
sits outside the training hull, unbounded above.

Measured limitation, not a hypothetical (found while testing this against
real data, 27-Aug): pushing a SINGLE one of the 35 inputs far outside its
observed range -- the exact perturbation Sakshi's T2.2 demo used to show
gp_std ballooning -- does NOT reliably move this score off 0, even at 20x
the observed max, with contamination='auto'|0.1|0.2 all checked. This isn't
a tuning bug: IsolationForest isolates points via random axis-aligned
splits, and at d=35 a single extreme dimension is diluted across the other
34 unremarkable ones, so path length (and therefore decision_function)
stays close to typical. It DOES respond to a multi-dimensional excursion
(all 35 inputs pushed to 3x their max together scores ~0.16, clearly > 0).
This is a genuine, reportable difference from the GP-std signal, not a
defect to quietly tune away -- see test_novelty.py's
RealDataSanityCheckTests for both behaviours, and spec.md §7 for the
write-up. It's also the concrete evidence for Sakshi's own T2.2
recommendation to cross-check IsolationForest against gp_std where
available (currently only uti_dafm_r) rather than lean on either alone.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest


class NoveltyScorer:
    def __init__(
        self,
        n_estimators: int = 200,
        contamination: str = "auto",
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self._model: Optional[IsolationForest] = None

    def fit(self, X_train: np.ndarray) -> "NoveltyScorer":
        X_train = np.asarray(X_train, dtype=float)
        if X_train.ndim != 2:
            raise ValueError(f"X_train must be 2D (n_samples, n_features), got shape {X_train.shape}")
        if len(X_train) < 2:
            raise ValueError(f"need >=2 rows to fit, got {len(X_train)}")

        model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        model.fit(X_train)
        self._model = model
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        """Higher = more novel / more out-of-distribution relative to the
        training hull. Always >= 0 (see module docstring for the sign
        convention) -- ready to feed straight into trust_score()'s
        novelty_term without further transformation."""
        if self._model is None:
            raise RuntimeError("NoveltyScorer not fitted -- call fit() first")
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D (n_samples, n_features), got shape {X.shape}")

        decision = self._model.decision_function(X)  # positive=inlier, negative=outlier
        return np.clip(-decision, a_min=0.0, a_max=None)
