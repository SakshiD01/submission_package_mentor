"""Load scaler + 20 regressors; predict (nolhc_ml_engine_spec.md §10)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np

from schemas import PredictionResult
from training_columns import TRAINING_COLUMN_ORDER

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MLEngine:
    def __init__(self, model_version: str = "v1", models_root: Optional[Path] = None) -> None:
        root = models_root or (PROJECT_ROOT / "models")
        self.model_dir = root / model_version
        self.model_version = model_version
        reg_path = self.model_dir / "registry.json"
        if not reg_path.is_file():
            raise FileNotFoundError(f"Missing registry: {reg_path}")
        with open(reg_path, encoding="utf-8") as f:
            self.registry: Dict[str, Any] = json.load(f)
        self.scaler = joblib.load(self.model_dir / "scaler_X.pkl")
        self.models: Dict[str, Any] = {}
        for slug in self.registry.get("outputs", {}):
            p = self.model_dir / f"model_{slug}.pkl"
            if not p.is_file():
                raise FileNotFoundError(f"Missing model: {p}")
            self.models[slug] = joblib.load(p)

    def _fill_defaults(self, input_vector: Dict[str, Any]) -> Dict[str, float]:
        med = self.registry.get("training_medians", {})
        return {c: float(input_vector.get(c, med.get(c, 0.0))) for c in TRAINING_COLUMN_ORDER}

    def _vector_from_inputs(self, input_vector: Dict[str, Any]) -> np.ndarray:
        filled = self._fill_defaults(input_vector)
        row = [filled[c] for c in TRAINING_COLUMN_ORDER]
        return np.asarray(row, dtype=np.float64).reshape(1, -1)

    def predict(self, input_vector: Dict[str, Any]) -> Dict[str, PredictionResult]:
        x_raw = self._vector_from_inputs(input_vector)
        x_scaled = self.scaler.transform(x_raw)
        out: Dict[str, PredictionResult] = {}
        for slug, model in self.models.items():
            info = self.registry["outputs"][slug]
            val = float(model.predict(x_scaled)[0])
            r2 = float(info.get("r2_cv_mean", 0.0))
            st = "ok" if r2 >= 0.75 else "low_confidence"
            out[slug] = PredictionResult(
                value=val,
                unit=str(info.get("unit", "hours")),
                status=st,
                r2=r2,
                registered_as=str(info.get("registered_as", "")),
                mae=float(info.get("mae_cv_mean", 0.0)),
            )
        return out

    def predict_selective(
        self, input_vector: Dict[str, Any], output_slugs: list[str]
    ) -> Dict[str, PredictionResult]:
        full = self.predict(input_vector)
        unknown = [s for s in output_slugs if s not in full]
        if unknown:
            raise KeyError(unknown)
        return {s: full[s] for s in output_slugs}
