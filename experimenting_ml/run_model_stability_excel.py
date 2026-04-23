#!/usr/bin/env python3
"""
Model stability validation workbook (mentor finalization Step 1).

Default shortlist: per target, top ``k`` models by **lowest mean CV RMSE** (contenders for that target).
Alternative: same global shortlist for all targets (median mean-rank rule, Step 2 style).

Outputs:
  outputs/model_stability_by_target.xlsx
  outputs/model_stability_by_target.meta.json

Usage:
  python run_model_stability_excel.py
  python run_model_stability_excel.py --shortlist-mode topk_mean_cv_rmse --shortlist-k 5
  python run_model_stability_excel.py --shortlist-mode global_median_rank --shortlist-k 5
  python run_model_stability_excel.py --all-models
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
NOLHC_SRC = ROOT.parent / "nolhc_ml" / "src"
for pth in (SRC, NOLHC_SRC):
    if str(pth) not in sys.path:
        sys.path.insert(0, str(pth))

from model_stability_excel import (  # noqa: E402
    build_model_stability_workbook,
    compute_global_median_shortlist,
    shortlist_topk_mean_cv_rmse,
)
from step2_ranking import load_cv_results  # noqa: E402
from training_columns import OUTPUT_COLUMN_ORDER  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="CV rank stability workbook (one sheet per target)")
    p.add_argument("--cv-json", type=Path, default=ROOT / "outputs" / "cv_results.json")
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "model_stability_by_target.xlsx",
    )
    p.add_argument(
        "--shortlist-k",
        type=int,
        default=5,
        help="k for top-CV-RMSE shortlist or global median-rank shortlist",
    )
    p.add_argument(
        "--shortlist-mode",
        choices=("topk_mean_cv_rmse", "global_median_rank"),
        default="topk_mean_cv_rmse",
        help="topk_mean_cv_rmse: per-target top-k by mean CV RMSE (default). "
        "global_median_rank: same k models on every sheet (Step 2 style).",
    )
    p.add_argument(
        "--all-models",
        action="store_true",
        help="Include all models (overrides --shortlist-mode)",
    )
    args = p.parse_args()

    if not args.cv_json.is_file():
        raise SystemExit(f"Missing {args.cv_json}")

    cv = load_cv_results(args.cv_json)
    targets = [t for t in OUTPUT_COLUMN_ORDER if t in cv]
    if not targets:
        targets = sorted(cv.keys())
    sample_t = targets[0]
    model_names = sorted(cv[sample_t].keys())
    k = max(1, int(args.shortlist_k))

    if args.all_models:
        mode = "all_models"
        shortlist = list(model_names)
    elif args.shortlist_mode == "global_median_rank":
        mode = "global_median_rank"
        shortlist = compute_global_median_shortlist(
            args.cv_json, model_names, targets, shortlist_k=k
        )
    else:
        mode = "topk_mean_cv_rmse"
        shortlist = []

    build_model_stability_workbook(
        args.out.resolve(),
        cv_path=args.cv_json.resolve(),
        targets=targets,
        model_names=model_names,
        shortlist=shortlist,
        shortlist_mode=mode,
        shortlist_k=k,
    )

    meta: dict = {
        "cv_json": str(args.cv_json),
        "shortlist_k": k,
        "shortlist_mode": mode,
        "all_models": args.all_models,
    }
    if mode == "global_median_rank":
        meta["shortlist_models"] = shortlist
    elif mode == "topk_mean_cv_rmse":
        meta["per_target_shortlist"] = {
            t: shortlist_topk_mean_cv_rmse(cv, t, model_names, k) for t in targets
        }
    else:
        meta["n_models"] = len(model_names)

    meta_path = args.out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"Wrote {meta_path}")
    if mode == "global_median_rank":
        print(f"Global shortlist ({len(shortlist)}): {', '.join(shortlist)}")
    elif mode == "topk_mean_cv_rmse":
        print(f"Per-target shortlist: top {k} by mean CV RMSE (see .meta.json)")


if __name__ == "__main__":
    main()
