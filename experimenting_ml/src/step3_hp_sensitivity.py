"""
Step 3d: hyperparameter sensitivity from cv_fold_details (requires Step 1 --save-fold-details).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from step3_selection import load_cv, top_k_models_by_cv_rmse


def plot_hp_sensitivity_for_model(
    details_df: pd.DataFrame,
    target: str,
    model: str,
    out_path: Path,
    *,
    max_hp_keys: int = 2,
) -> bool:
    """
    For aggregate rows only: plot mean CV RMSE vs first 1–2 varying numeric hyperparameters.
    Returns False if nothing to plot.
    """
    sub = details_df[
        (details_df["target"] == target)
        & (details_df["model"] == model)
        & (details_df["fold"] == "aggregate")
    ].copy()
    if sub.empty:
        return False

    params_list: List[Dict[str, Any]] = []
    rmses: List[float] = []
    for _, row in sub.iterrows():
        try:
            d = json.loads(row["params"]) if isinstance(row["params"], str) else row["params"]
        except (json.JSONDecodeError, TypeError):
            continue
        params_list.append(d)
        rmses.append(float(row["rmse"]))

    if len(params_list) < 2:
        return False

    keys_variation: Dict[str, List[Any]] = {}
    for k in params_list[0].keys():
        vals = [p.get(k) for p in params_list]
        if len(set(str(v) for v in vals)) > 1:
            keys_variation[k] = vals

    numeric_keys = [k for k in keys_variation if isinstance(params_list[0].get(k), (int, float))]
    if not numeric_keys:
        return False

    numeric_keys = numeric_keys[:max_hp_keys]
    k0 = numeric_keys[0]
    x0 = [float(p[k0]) for p in params_list]

    fig, ax = plt.subplots(figsize=(7, 4))
    if len(numeric_keys) >= 2:
        k1 = numeric_keys[1]
        x1 = [float(p[k1]) for p in params_list]
        sc = ax.scatter(x0, rmses, c=x1, cmap="viridis", s=40, edgecolors="k", linewidths=0.3)
        plt.colorbar(sc, ax=ax, label=k1)
        ax.set_xlabel(k0)
    else:
        order = np.argsort(x0)
        ax.plot(np.array(x0)[order], np.array(rmses)[order], "o-", markersize=6)
        ax.set_xlabel(k0)

    ax.set_ylabel("Mean CV RMSE (aggregate over folds)")
    ax.set_title(f"HP sensitivity — {target} / {model}")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return True


def run_hp_sensitivity_all(
    cv_path: Path,
    details_csv: Path,
    model_names: Sequence[str],
    targets: Sequence[str],
    out_dir: Path,
    *,
    top_k: int = 3,
) -> pd.DataFrame:
    cv = load_cv(cv_path)
    if not details_csv.is_file():
        return pd.DataFrame(
            [{"error": f"Missing {details_csv}; rerun Step 1 with --save-fold-details"}]
        )

    df = pd.read_csv(details_csv)
    need = {"target", "model", "fold", "params", "rmse"}
    if not need.issubset(df.columns):
        return pd.DataFrame([{"error": f"CSV missing columns {need}"}])

    rows = []
    for t in targets:
        tops = top_k_models_by_cv_rmse(cv, t, model_names, top_k)
        for m in tops:
            outp = out_dir / f"hp_sens__{t}__{m}.png"
            ok = plot_hp_sensitivity_for_model(df, t, m, outp)
            rows.append({"target": t, "model": m, "plotted": ok, "path": str(outp) if ok else ""})
    return pd.DataFrame(rows)
