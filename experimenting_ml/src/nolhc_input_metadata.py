"""
Build slider metadata for the 35 NOLHC input features.

Bounds prefer ExpValues from ``NOLHC Designs - AL Students.xlsx`` (if present);
otherwise training-data min/max from the loaded X frame.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

def _nolhc_designs_candidates(root: Path) -> List[Path]:
    names = [
        "NOLHC Designs - AL Students.xlsx",
        "NOLHC_Designs_-_AL_Students.xlsx",
        "NOLHC Designs - AL Students (1).xlsx",
    ]
    out: List[Path] = []
    for base in (root / "docs", root / "UI", root.parent / "nolhc_ml" / "data" / "raw"):
        if not base.is_dir():
            continue
        for n in names:
            p = base / n
            if p.is_file() and p not in out:
                out.append(p)
    return out


def _bounds_from_expvalues(xlsx_path: Path, training_order: List[str]) -> Optional[Dict[str, Tuple[float, float]]]:
    try:
        exp = pd.read_excel(
            xlsx_path, sheet_name="ExpValues", header=None, skiprows=3, engine="openpyxl"
        )
    except (OSError, ValueError, KeyError):
        return None
    if exp.shape[1] < 2:
        return None
    # Lazy import to match data_loader column alignment
    from training_columns import EXP_VALUES_FEATURE_COL_INDICES  # noqa: WPS433

    max_col = max(EXP_VALUES_FEATURE_COL_INDICES)
    if exp.shape[1] <= max_col:
        return None
    sub = exp.iloc[:, EXP_VALUES_FEATURE_COL_INDICES].copy()
    sub.columns = training_order
    for col in sub.columns:
        sub[col] = pd.to_numeric(sub[col], errors="coerce")
    sub = sub.dropna(how="all")
    if len(sub) == 0:
        return None
    out: Dict[str, Tuple[float, float]] = {}
    for c in training_order:
        col = sub[c].dropna()
        if len(col) == 0:
            continue
        out[str(c)] = (float(col.min()), float(col.max()))
    return out if out else None


def _bounds_from_frame(x: pd.DataFrame, training_order: List[str]) -> Dict[str, Tuple[float, float]]:
    out: Dict[str, Tuple[float, float]] = {}
    for c in training_order:
        if c not in x.columns:
            continue
        col = pd.to_numeric(x[c], errors="coerce").dropna()
        if len(col) == 0:
            continue
        lo, hi = float(col.min()), float(col.max())
        if lo == hi:
            lo -= 1e-6
            hi += 1e-6
        out[str(c)] = (lo, hi)
    return out


def merge_bounds(
    a: Dict[str, Tuple[float, float]],
    b: Dict[str, Tuple[float, float]],
) -> Dict[str, Tuple[float, float]]:
    """Intersect sensible ranges: expand to cover both minima and maxima."""
    keys = set(a) | set(b)
    out: Dict[str, Tuple[float, float]] = {}
    for k in keys:
        if k in a and k in b:
            out[k] = (min(a[k][0], b[k][0]), max(a[k][1], b[k][1]))
        elif k in a:
            out[k] = a[k]
        else:
            out[k] = b[k]
    return out


def _step_for_feature(name: str, lo: float, hi: float) -> float:
    span = hi - lo
    if name.startswith("Pct_") or name in ("Pct_IB_PreBoard", "Pct_OB_PreBoard"):
        return 0.001 if span < 0.2 else 0.005
    if name.startswith("ChkTime_"):
        return 0.5 if span < 30 else 1.0
    if name.startswith("Num") or name.startswith("VCap_"):
        return 1.0
    if span > 5000:
        return 10.0
    if span > 500:
        return 5.0
    if span > 50:
        return 1.0
    return max(0.01, round(span / 200.0, 6))


# Corridor route volumes (tonnes). Same split as _scenario_vector in run_ui_inference_api.
ROUTE_VOLUME_FEATURE_IDS: Tuple[str, ...] = (
    "Shift_NA_Im_LB_to_Cher",
    "NA_Im_LB",
    "NA_Im_DR",
    "Shift_NA_Ex_LB_to_Cher",
    "NA_Ex_LB",
    "NA_Ex_DR",
    "Shift_A_Im_LB_to_Cher",
    "A_Im_LB",
    "A_Im_DR",
    "Shift_A_Ex_LB_to_Cher",
    "A_Ex_LB",
    "A_Ex_DR",
)


def build_input_sliders(
    training_order: List[str],
    bounds: Dict[str, Tuple[float, float]],
    descriptions: Dict[str, str],
    input_unit_fn: Any,
) -> List[Dict[str, Any]]:
    sliders: List[Dict[str, Any]] = []
    for name in training_order:
        lo, hi = bounds.get(name, (0.0, 1.0))
        step = _step_for_feature(name, lo, hi)
        unit = input_unit_fn(name)
        is_pct = name.startswith("Pct_") or name in ("Pct_IB_PreBoard", "Pct_OB_PreBoard")
        is_route_vol = name in ROUTE_VOLUME_FEATURE_IDS
        desc = descriptions.get(name, name)
        if is_route_vol and "tonnes" not in desc.lower():
            desc = f"{desc} (tonnes)"
        disp = "percent_0_100" if is_pct else ("tonnes" if is_route_vol else "raw")
        sliders.append(
            {
                "id": name,
                "label": desc.split(",")[0].strip() if desc else name,
                "description": desc,
                "min": lo,
                "max": hi,
                "step": step,
                "unit": "tonnes" if is_route_vol else unit,
                "display": disp,
            }
        )
    return sliders


def clip_feature(
    name: str,
    val: float,
    bounds: Dict[str, Tuple[float, float]],
    _base: Dict[str, float],
) -> float:
    lo, hi = bounds.get(name, (float("-inf"), float("inf")))
    if name.startswith("Pct_") or name in ("Pct_IB_PreBoard", "Pct_OB_PreBoard"):
        if val > 1.5:
            val = val / 100.0
        v = float(np.clip(val, 0.0, 1.0))
        return float(np.clip(v, lo, hi))
    v = float(val)
    return float(np.clip(v, lo, hi))
