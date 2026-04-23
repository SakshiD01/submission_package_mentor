#!/usr/bin/env python3
"""
Regenerate docs/CV_Best_Models_Per_Target.md from cv_results.json
(best CV mean RMSE model per target + hyperparameters).

Usage:
  python generate_cv_summary_md.py
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

from training_columns import OUTPUT_COLUMN_ORDER  # noqa: E402


def _fmt_params(d: dict) -> str:
    parts = []
    for k in sorted(d.keys()):
        v = d[k]
        if v is None:
            vs = "null"
        elif isinstance(v, float):
            vs = f"{v:.6g}" if abs(v) < 1e-3 or abs(v) >= 1e6 else str(v)
        else:
            vs = repr(v)
        parts.append(f"`{k}`={vs}")
    return ", ".join(parts)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--cv",
        type=Path,
        default=ROOT / "outputs" / "cv_results.json",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "CV_Best_Models_Per_Target.md",
    )
    args = p.parse_args()

    cv = json.loads(args.cv.read_text(encoding="utf-8"))

    target_order = [c for c in OUTPUT_COLUMN_ORDER if c in cv]
    extra = sorted(set(cv.keys()) - set(target_order))
    targets = target_order + extra

    lines = [
        "# CV summary — best model per target (5-fold RMSE)",
        "",
        "Generated from `outputs/cv_results.json`. Regenerate:",
        "",
        "```bash",
        "python generate_cv_summary_md.py",
        "```",
        "",
        "| # | Target | Best model (lowest mean CV RMSE) | Mean CV RMSE | Std CV RMSE | Selected hyperparameters |",
        "|---:|---|---|---|---:|---|",
    ]

    for i, t in enumerate(targets, start=1):
        per = cv[t]
        best_m = min(per.keys(), key=lambda m: per[m]["mean_rmse"])
        r = per[best_m]
        params = _fmt_params(r["best_params"])
        lines.append(
            f"| {i} | `{t}` | **{best_m}** | {r['mean_rmse']:.4f} | {r['std_rmse']:.4f} | {params} |"
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
