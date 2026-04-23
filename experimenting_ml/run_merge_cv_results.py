#!/usr/bin/env python3
"""
Merge several per-target cv_results.json files into one combined JSON.

Each input file should look like cv_results.json: top-level keys are target names,
values are { "ModelName": { "best_params", "fold_rmses", ... }, ... }.

Typical workflow:
  python run_step1_cv.py --target TT_A --out outputs/cv_TT_A.json
  python run_step1_cv.py --target TT_B --out outputs/cv_TT_B.json
  python run_merge_cv_results.py outputs/cv_TT_A.json outputs/cv_TT_B.json

Or glob:
  python run_merge_cv_results.py --glob 'outputs/cv_target_*.json'

Writes outputs/cv_results.json (+ optional .summary.csv) by default.

Usage:
  python run_merge_cv_results.py file1.json file2.json ...
  python run_merge_cv_results.py --glob 'outputs/partial_cv_*.json' --out outputs/cv_results.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    if obj is None or isinstance(obj, (str, bool, int, float)):
        return obj
    if isinstance(obj, tuple):
        return list(obj)
    return str(obj)


def load_one(path: Path) -> Dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a JSON object")
    return data


def merge_files(paths: List[Path]) -> Dict:
    combined: Dict = {}
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError(p)
        part = load_one(p)
        for target, models in part.items():
            if target in combined:
                raise ValueError(
                    f"Duplicate target {target!r}: appears in more than one input "
                    f"(second file: {p}). Use one file per target or fix inputs."
                )
            if not isinstance(models, dict):
                raise ValueError(f"{p}: value for {target!r} must be an object (per-model results)")
            combined[target] = models
    return combined


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge per-target CV JSON into one cv_results.json")
    ap.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="Per-target cv_results JSON files",
    )
    ap.add_argument(
        "--glob",
        dest="glob_pattern",
        type=str,
        default=None,
        help="Glob under cwd (e.g. outputs/cv_*.json); combined with positional files",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "cv_results.json",
        help="Merged JSON path",
    )
    ap.add_argument(
        "--write-summary",
        action="store_true",
        help="Also write <out>.summary.csv like run_step1_cv.py",
    )
    args = ap.parse_args()

    paths: List[Path] = list(args.inputs)
    if args.glob_pattern:
        paths.extend(sorted(Path().glob(args.glob_pattern)))

    paths = [p.resolve() for p in paths]
    # stable unique order
    seen = set()
    uniq: List[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    paths = uniq

    if not paths:
        raise SystemExit("No input files: pass JSON paths or use --glob")

    merged = merge_files(paths)
    if not merged:
        raise SystemExit("Merged result is empty")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(_json_safe(merged), indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {args.out} ({len(merged)} target(s) from {len(paths)} file(s))")

    if args.write_summary:
        rows = []
        for t, per_m in merged.items():
            for m, r in per_m.items():
                rows.append(
                    {
                        "target": t,
                        "model": m,
                        "mean_rmse": r["mean_rmse"],
                        "std_rmse": r["std_rmse"],
                        "cv_n_splits": r.get("cv_n_splits"),
                        "cv_n_repeats": r.get("cv_n_repeats"),
                        "cv_n_scores": r.get(
                            "cv_n_scores", len(r.get("fold_rmses", []))
                        ),
                        "best_params": json.dumps(r["best_params"], sort_keys=True),
                    }
                )
        summary_path = args.out.with_suffix(".summary.csv")
        pd.DataFrame(rows).sort_values(["target", "mean_rmse"]).to_csv(
            summary_path, index=False
        )
        print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
