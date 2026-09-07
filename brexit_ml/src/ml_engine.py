"""
Load trained artifacts and run inference (spec §7).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np

from schemas import PredictionResult
from training_columns import TRAINING_COLUMN_ORDER

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class MLEngine:
    """
    Loads ``scaler_X.pkl``, ``registry.json``, and per-output model/classifier pickles.

    Registry keys are **slugs** (e.g. ``transportation_time_agri_import_from_gb``). ``predict``
    returns the same keys for alignment with training.
    """

    def __init__(
        self,
        model_version: str = "v1",
        *,
        models_root: Optional[Path] = None,
    ) -> None:
        root = Path(models_root) if models_root is not None else PROJECT_ROOT
        self._models_dir = root / "models" / model_version
        self.model_version = model_version

        scaler_path = self._models_dir / "scaler_X.pkl"
        registry_path = self._models_dir / "registry.json"
        if not scaler_path.is_file() or not registry_path.is_file():
            raise FileNotFoundError(
                f"Missing scaler or registry under {self._models_dir}. Run: python src/train.py"
            )

        self.scaler = joblib.load(scaler_path)
        with open(registry_path, encoding="utf-8") as f:
            self.registry: Dict[str, Any] = json.load(f)

        self.models: Dict[str, Any] = {}
        self.classifiers: Dict[str, Any] = {}
        self._load_all_models()

    def _load_all_models(self) -> None:
        outputs = self.registry.get("outputs", {})
        for slug, info in outputs.items():
            if info.get("model_type") == "not_trained" or info.get("phase") == 2:
                continue
            mf = info.get("model_file")
            if mf:
                path = self._models_dir / mf
                if path.is_file():
                    self.models[slug] = joblib.load(path)
            cf = info.get("classifier_file")
            if cf:
                path = self._models_dir / cf
                if path.is_file():
                    self.classifiers[slug] = joblib.load(path)

    def _fill_defaults(self, input_vector: Dict[str, Any]) -> Dict[str, float]:
        medians: Dict[str, float] = self.registry["training_medians"]
        out: Dict[str, float] = dict(medians)
        for k, v in input_vector.items():
            if k in out and v is not None:
                out[k] = float(v)
        return out

    def _build_x_scaled(self, input_vector: Dict[str, Any]) -> np.ndarray:
        X = self._fill_defaults(input_vector)
        arr = np.array([[X[col] for col in TRAINING_COLUMN_ORDER]], dtype=np.float64)
        return self.scaler.transform(arr)

    def predict(self, input_vector: Dict[str, Any]) -> Dict[str, PredictionResult]:
        """
        ``input_vector``: AnyLogic column names → values; missing keys use training medians.

        Returns slug-keyed ``PredictionResult`` (same keys as ``registry['outputs']``).
        """
        x_scaled = self._build_x_scaled(input_vector)
        results: Dict[str, PredictionResult] = {}

        for slug, info in self.registry["outputs"].items():
            unit = str(info["unit"])
            phase = int(info["phase"])
            cov = int(info["coverage_pct"])
            r2 = info.get("r2_cv_mean")
            if r2 is not None:
                r2 = float(r2)

            if info.get("model_type") == "not_trained" or phase == 2:
                results[slug] = PredictionResult(
                    value=None,
                    unit=unit,
                    status="not_trained",
                    phase=phase,  # type: ignore[arg-type]
                    coverage_pct=cov,
                    r2=None,
                )
                continue

            # Zero-inflation: run classifier first when present
            if slug in self.classifiers:
                clf = self.classifiers[slug]
                cls_pred = clf.predict(x_scaled)[0]
                is_nonzero = bool(int(cls_pred)) if cls_pred is not None else False
                if not is_nonzero:
                    results[slug] = PredictionResult(
                        value=0.0,
                        unit=unit,
                        status="zero_predicted",
                        phase=phase,  # type: ignore[arg-type]
                        coverage_pct=cov,
                        r2=r2,
                    )
                    continue
                # Classifier says nonzero but no regressor (degenerate training)
                if slug not in self.models:
                    results[slug] = PredictionResult(
                        value=0.0,
                        unit=unit,
                        status="zero_predicted",
                        phase=phase,  # type: ignore[arg-type]
                        coverage_pct=cov,
                        r2=r2,
                    )
                    continue

            reg = self.models.get(slug)
            if reg is None:
                results[slug] = PredictionResult(
                    value=None,
                    unit=unit,
                    status="not_trained",
                    phase=phase,  # type: ignore[arg-type]
                    coverage_pct=cov,
                    r2=None,
                )
                continue

            value = float(reg.predict(x_scaled)[0])
            st = "ok" if cov >= 15 else "low_coverage"
            results[slug] = PredictionResult(
                value=value,
                unit=unit,
                status=st,
                phase=phase,  # type: ignore[arg-type]
                coverage_pct=cov,
                r2=r2,
            )

        return results

    def predict_values_only(self, input_vector: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Raw floats / None for API layers that do not need Pydantic models."""
        return {k: v.value for k, v in self.predict(input_vector).items()}
