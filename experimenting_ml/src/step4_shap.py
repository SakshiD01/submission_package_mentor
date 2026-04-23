"""
Step 4: SHAP explanations for the selected model per target (post-selection only).

Uses raw feature space (same as training data before scaling). Tree models use
``TreeExplainer`` when possible; others use ``shap.Explainer`` with an independent masker.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd

from models import NEEDS_SCALING

try:
    import shap
except ImportError as e:
    shap = None  # type: ignore
    _SHAP_ERR = e
else:
    _SHAP_ERR = None


def _safe_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)


# Tree ensembles fit on raw X in this pipeline (not scaled)
TREE_MODELS = frozenset(
    {
        "RandomForest",
        "ExtraTrees",
        "GradientBoosting",
        "AdaBoost",
        "XGBoost",
        "LightGBM",
        "CatBoost",
    }
)


def _load_estimator(trained_dir: Path, target: str, model_name: str):
    tdir = trained_dir / _safe_filename(target)
    fp = tdir / f"{_safe_filename(model_name)}.joblib"
    if not fp.is_file():
        raise FileNotFoundError(fp)
    return joblib.load(fp)


def _make_predict_fn(
    est,
    scaler,
    model_name: str,
) -> Callable[[np.ndarray], np.ndarray]:
    def predict_fn(X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if model_name in NEEDS_SCALING:
            Xf = scaler.transform(X)
            return np.asarray(est.predict(Xf), dtype=float)
        return np.asarray(est.predict(X), dtype=float)

    return predict_fn


def _subsample_rows(X: np.ndarray, max_rows: int, seed: int) -> np.ndarray:
    n = len(X)
    if n <= max_rows:
        return X
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, size=max_rows, replace=False)
    return X[idx]


def run_shap_for_target(
    *,
    trained_dir: Path,
    target: str,
    model_name: str,
    X_background: np.ndarray,
    X_explain: np.ndarray,
    feature_names: List[str],
    out_dir: Path,
    seed: int = 42,
    n_local: int = 3,
) -> Dict[str, Any]:
    """
    Writes summary bar, beeswarm (if supported), mean |SHAP| CSV, and waterfall plots
    for the first ``n_local`` rows of ``X_explain``.
    """
    if shap is None:
        raise ImportError(
            "Install shap: pip install shap"
        ) from _SHAP_ERR

    scaler = joblib.load(trained_dir / "scaler.joblib")
    est = _load_estimator(trained_dir, target, model_name)
    predict_fn = _make_predict_fn(est, scaler, model_name)

    X_bg = _subsample_rows(X_background, min(len(X_background), 100), seed)
    X_ex = _subsample_rows(X_explain, min(len(X_explain), 200), seed + 1)
    n_feat = X_bg.shape[1]
    cols = list(feature_names[:n_feat])

    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"{_safe_filename(target)}__{_safe_filename(model_name)}"
    meta: Dict[str, Any] = {"target": target, "model": model_name, "outputs": []}

    sv = None
    use_tree = model_name in TREE_MODELS and model_name not in NEEDS_SCALING
    if use_tree:
        try:
            tree_exp = shap.TreeExplainer(est)
            sv = tree_exp(X_ex)
        except Exception as ex:
            meta["tree_explainer_fallback"] = str(ex)
            use_tree = False

    if sv is None:
        X_bg_df = pd.DataFrame(X_bg, columns=cols)
        X_ex_df = pd.DataFrame(X_ex, columns=cols)

        def _pred(X):
            if isinstance(X, pd.DataFrame):
                X = X.to_numpy(dtype=float)
            return predict_fn(X)

        masker = shap.maskers.Independent(X_bg_df)
        explainer = shap.Explainer(_pred, masker)
        sv = explainer(X_ex_df)

    # Global: mean |SHAP|
    vals = np.asarray(sv.values, dtype=float)
    if vals.ndim == 1:
        vals = vals.reshape(1, -1)
    mean_abs = np.abs(vals).mean(axis=0)
    fn_use = cols[: mean_abs.shape[0]]
    imp = pd.DataFrame({"feature": fn_use, "mean_abs_shap": mean_abs}).sort_values(
        "mean_abs_shap", ascending=False
    )
    csv_path = Path(str(base) + "__importance.csv")
    imp.to_csv(csv_path, index=False)
    meta["outputs"].append(str(csv_path))

    # Bar summary
    try:
        plt.figure(figsize=(10, 6))
        shap.plots.bar(sv, max_display=min(25, len(fn_use)), show=False)
        plt.tight_layout()
        p_bar = Path(str(base) + "__summary_bar.png")
        plt.savefig(p_bar, dpi=140, bbox_inches="tight")
        plt.close()
        meta["outputs"].append(str(p_bar))
    except Exception as e:
        meta["bar_error"] = str(e)
        plt.close()

    # Beeswarm (global distribution of SHAP values)
    try:
        plt.figure(figsize=(10, 7))
        shap.plots.beeswarm(sv, max_display=min(25, len(fn_use)), show=False)
        plt.tight_layout()
        p_bee = Path(str(base) + "__beeswarm.png")
        plt.savefig(p_bee, dpi=140, bbox_inches="tight")
        plt.close()
        meta["outputs"].append(str(p_bee))
    except Exception as e:
        meta["beeswarm_error"] = str(e)
        plt.close()

    # Local: waterfall for first n_local rows of X_explain (original order, subsampled X_ex)
    loc_cap = min(n_local, len(X_ex))
    try:
        for i in range(loc_cap):
            plt.figure(figsize=(8, 5))
            shap.plots.waterfall(sv[i], max_display=min(20, len(fn_use)), show=False)
            plt.tight_layout()
            p_w = Path(str(base) + f"__waterfall_row{i}.png")
            plt.savefig(p_w, dpi=140, bbox_inches="tight")
            plt.close()
            meta["outputs"].append(str(p_w))
    except Exception as e:
        meta["waterfall_error"] = str(e)
        plt.close()

    return meta
