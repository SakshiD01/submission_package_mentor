#!/usr/bin/env python3
"""
Step 4: SHAP explainability for the **selected** model per target only (post-selection).

Does not score or compare models — explains the one model you designate per target.

**Recommended pipeline order (before conformal / test eval):** Step 1 → … → Step 3 →
Step 6 (retrain) → **Step 4 SHAP** (default selection + explain split) → Step 7/9 →
conformal. After test results exist, re-run with ``--selection composite`` and/or
``--explain-split test`` if you want alignment with Step 10 or hold-out explanations.

Selection modes:
  --selection composite_pre_test (default): CV + paired t-test wins only (same 2:1
    weight ratio as the CV:wins parts of Step 10 composite); needs cv_results.json +
    paired_ttests_all_targets.csv
  --selection cv         : lowest mean CV RMSE per target
  --selection composite: full Step 10 rule (needs test + conformal JSON too)
  --selection json       : --selection-json path to {\"TargetName\": \"ModelName\", ...}

Background / explain sets:
  - Background: subsample of training rows (max 100)
  - Global plots + CSV: subsample of train or test (see --explain-split; default train)
  - Local waterfalls: first rows of that explain subsample (see --n-local)

Usage:
  python run_step4_shap.py
  python run_step4_shap.py --selection cv
  python run_step4_shap.py --selection composite
  python run_step4_shap.py --explain-split test
  python run_step4_shap.py --selection json --selection-json my_models.json

Requires: pip install shap

After a successful SHAP run, merge one sheet per target into a single workbook::

  python run_step4_shap_master_excel.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
NOLHC_SRC = ROOT.parent / "nolhc_ml" / "src"
for pth in (SRC, NOLHC_SRC):
    if str(pth) not in sys.path:
        sys.path.insert(0, str(pth))

from data import load_xy  # noqa: E402
from excel_report import (  # noqa: E402
    build_ttest_structures,
    compute_model_selection,
    compute_model_selection_pre_test,
    load_json,
)
from splits import train_test_indices  # noqa: E402
from step4_shap import run_shap_for_target  # noqa: E402
from test_eval import load_split_meta  # noqa: E402
from training_columns import OUTPUT_COLUMN_ORDER  # noqa: E402


def resolve_selection(
    policy: str,
    *,
    cv_path: Path,
    test_path: Path,
    conf_path: Path,
    pairs_path: Path,
    targets: List[str],
    selection_json: Optional[Path],
) -> Dict[str, str]:
    cv = load_json(cv_path)
    if policy == "cv":
        out: Dict[str, str] = {}
        for t in targets:
            if t not in cv:
                raise KeyError(t)
            out[t] = min(cv[t].keys(), key=lambda m: float(cv[t][m]["mean_rmse"]))
        return out

    if policy == "composite_pre_test":
        if not pairs_path.is_file():
            raise SystemExit(
                "composite_pre_test selection requires --pairs-csv (paired t-tests)"
            )
        model_names = sorted(cv[next(iter(cv))].keys())
        ttest_by_target = build_ttest_structures(pairs_path, model_names, targets)
        df = compute_model_selection_pre_test(
            cv, ttest_by_target, targets, model_names
        )
        return {str(r["Target"]): str(r["Best_Model"]) for _, r in df.iterrows()}

    if policy == "composite":
        if not test_path.is_file() or not conf_path.is_file() or not pairs_path.is_file():
            raise SystemExit(
                "composite selection requires --test-json, --conformal-json, --pairs-csv"
            )
        test_results = load_json(test_path)
        conformal_results = load_json(conf_path)
        model_names = sorted(cv[next(iter(cv))].keys())
        ttest_by_target = build_ttest_structures(pairs_path, model_names, targets)
        df = compute_model_selection(
            cv,
            test_results,
            conformal_results,
            ttest_by_target,
            targets,
            model_names,
        )
        return {str(r["Target"]): str(r["Best_Model"]) for _, r in df.iterrows()}

    if policy == "json":
        if selection_json is None or not selection_json.is_file():
            raise SystemExit("--selection-json required for --selection json")
        raw = json.loads(selection_json.read_text(encoding="utf-8"))
        out = {}
        for t in targets:
            if t not in raw:
                raise SystemExit(f"selection-json missing key {t!r}")
            out[t] = str(raw[t])
        return out

    raise SystemExit(f"Unknown --selection {policy!r}")


def main() -> None:
    p = argparse.ArgumentParser(description="Step 4 — SHAP for selected models per target")
    p.add_argument(
        "--selection",
        choices=("composite_pre_test", "cv", "composite", "json"),
        default="composite_pre_test",
        help="How to pick one model per target (default: CV+t-test wins, no hold-out)",
    )
    p.add_argument(
        "--selection-json",
        type=Path,
        default=None,
        help='Mapping target -> model name when --selection json',
    )
    p.add_argument(
        "--trained-dir",
        type=Path,
        default=ROOT / "outputs" / "trained_models",
    )
    p.add_argument("--cv-json", type=Path, default=ROOT / "outputs" / "cv_results.json")
    p.add_argument("--test-json", type=Path, default=ROOT / "outputs" / "test_results.json")
    p.add_argument(
        "--conformal-json", type=Path, default=ROOT / "outputs" / "conformal_results.json"
    )
    p.add_argument(
        "--pairs-csv",
        type=Path,
        default=ROOT / "outputs" / "paired_ttests_all_targets.csv",
    )
    p.add_argument("--parquet-dir", type=Path, default=None)
    p.add_argument("--xlsx", type=Path, default=None)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "outputs" / "step4_shap",
    )
    p.add_argument(
        "--explain-split",
        choices=("train", "test"),
        default="train",
        help="Subsample for global SHAP + waterfalls (default train: no peek at hold-out X)",
    )
    p.add_argument(
        "--n-local",
        type=int,
        default=3,
        help="Waterfall plots for first N rows of the explain subsample",
    )
    args = p.parse_args()

    meta_path = args.trained_dir / "split_meta.json"
    if not meta_path.is_file():
        raise SystemExit(f"Missing {meta_path}; run run_step6_retrain.py first")

    meta = load_split_meta(meta_path)
    train_idx = meta["train_idx"]
    test_idx = meta["test_idx"]

    X, Y = load_xy(parquet_dir=args.parquet_dir, xlsx_path=args.xlsx)
    if len(X) != meta["n_total"]:
        raise SystemExit("Data row count does not match split_meta.json")

    cv_results = load_json(args.cv_json)
    targets = [t for t in OUTPUT_COLUMN_ORDER if t in cv_results]
    if not targets:
        targets = sorted(cv_results.keys())

    sel = resolve_selection(
        args.selection,
        cv_path=args.cv_json,
        test_path=args.test_json,
        conf_path=args.conformal_json,
        pairs_path=args.pairs_csv,
        targets=targets,
        selection_json=args.selection_json,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "target": t,
                "model": sel[t],
                "selection_policy": args.selection,
                "explain_split": args.explain_split,
            }
            for t in targets
        ]
    ).to_csv(args.out_dir / "shap_selected_models.csv", index=False)

    X_train = X.iloc[train_idx].to_numpy(dtype=float)
    X_test = X.iloc[test_idx].to_numpy(dtype=float)
    X_explain = X_train if args.explain_split == "train" else X_test
    fnames = list(X.columns)

    manifest: List[Dict[str, Any]] = []
    for t in targets:
        m = sel[t]
        print(f"SHAP: {t} / {m} (explain={args.explain_split}) …", flush=True)
        try:
            meta_r = run_shap_for_target(
                trained_dir=args.trained_dir,
                target=t,
                model_name=m,
                X_background=X_train,
                X_explain=X_explain,
                feature_names=fnames,
                out_dir=args.out_dir,
                seed=args.seed,
                n_local=args.n_local,
            )
            meta_r["status"] = "ok"
            manifest.append(meta_r)
        except Exception as ex:
            manifest.append(
                {
                    "target": t,
                    "model": m,
                    "status": "error",
                    "error": str(ex),
                }
            )
            print(f"  failed: {ex}", flush=True)

    (args.out_dir / "shap_run_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {args.out_dir}/ (see shap_selected_models.csv + shap_run_manifest.json)")


if __name__ == "__main__":
    main()
