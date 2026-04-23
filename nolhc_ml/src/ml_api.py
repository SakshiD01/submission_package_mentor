"""
NOLHC ML FastAPI routes (nolhc_ml_engine_spec.md §13–14).
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ml_engine import MLEngine
from training_columns import (
    INPUT_DESCRIPTIONS,
    TRAINING_COLUMN_ORDER,
    input_unit,
)


def _serialize_predictions(preds: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v.model_dump() for k, v in preds.items()}


def _model_not_ready(version: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "model_not_ready",
            "detail": f"No model files in models/{version}/. Run: python src/train.py",
        },
    )


def _validate_prediction_inputs(body: Dict[str, Any]) -> Optional[str]:
    """Return error detail string or None if OK (§14 invalid_input)."""
    for k, v in body.items():
        if k == "outputs":
            continue
        if k not in TRAINING_COLUMN_ORDER:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return f"Invalid numeric value for {k}: {v!r}"
        if k.startswith("Pct_"):
            if not (0.0 <= fv <= 1.0):
                return f"{k} must be between 0.0 and 1.0, got {fv}"
        u = input_unit(k)
        if u in ("tonnes", "trailers", "minutes", "count") and fv < 0:
            return f"{k} must be non-negative, got {fv}"
    return None


def _inputs_catalog(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    med = registry.get("training_medians", {})
    out: List[Dict[str, Any]] = []
    for name in TRAINING_COLUMN_ORDER:
        out.append(
            {
                "name": name,
                "description": INPUT_DESCRIPTIONS.get(name, name),
                "unit": input_unit(name),
                "typical": med.get(name),
            }
        )
    return out


def create_app(
    *,
    model_version: str = "v1",
    models_root: Optional[Path] = None,
    engine: Optional[MLEngine] = None,
) -> FastAPI:
    app = FastAPI(
        title="NOLHC ML Engine",
        version="2.0.0",
        description="NOLHC raw ML API (spec §13).",
    )

    _engine: Optional[MLEngine] = engine
    if _engine is None:
        try:
            _engine = MLEngine(model_version, models_root=models_root)
        except FileNotFoundError:
            _engine = None

    def require_engine() -> Optional[MLEngine]:
        return _engine

    app.state.get_engine = require_engine  # type: ignore[attr-defined]
    app.state.model_version = model_version  # type: ignore[attr-defined]
    app.state.models_root = (models_root or (Path(__file__).resolve().parents[1] / "models"))  # type: ignore[attr-defined]

    @app.get("/health")
    def health() -> Any:
        eng = require_engine()
        if eng is None:
            return _model_not_ready(model_version)
        reg = eng.registry
        outputs = reg.get("outputs", {})
        r2_vals = [float(o.get("r2_cv_mean", 0.0)) for o in outputs.values()]
        avg_r2 = float(sum(r2_vals) / len(r2_vals)) if r2_vals else 0.0
        below = [slug for slug, o in outputs.items() if float(o.get("r2_cv_mean", 0.0)) < 0.75]
        return {
            "status": "ok",
            "model_version": eng.model_version,
            "training_runs": int(reg.get("training_runs", 0)),
            "output_models": len(outputs),
            "candidate_models_benchmarked": int(reg.get("candidate_models_benchmarked", 0)),
            "avg_r2": avg_r2,
            "stacking_won_count": int(reg.get("stacking_won_count", 0)),
            "outputs_below_threshold": below,
        }

    @app.post("/predict")
    def predict_raw(body: Dict[str, Any]) -> Any:
        eng = require_engine()
        if eng is None:
            return _model_not_ready(model_version)
        err = _validate_prediction_inputs(body)
        if err:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_input", "detail": err},
            )
        try:
            preds = eng.predict(body)
            return _serialize_predictions(preds)
        except Exception as e:  # noqa: BLE001
            return JSONResponse(
                status_code=500,
                content={
                    "error": "prediction_error",
                    "detail": str(e),
                    "trace": traceback.format_exc()[-2000:],
                },
            )

    @app.post("/predict/selective")
    def predict_selective(body: Dict[str, Any]) -> Any:
        eng = require_engine()
        if eng is None:
            return _model_not_ready(model_version)
        err = _validate_prediction_inputs(body)
        if err:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_input", "detail": err},
            )
        outputs_req = body.get("outputs")
        if not outputs_req or not isinstance(outputs_req, list):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_input",
                    "detail": 'Request must include a non-empty "outputs" list of output slugs.',
                },
            )
        registry_outputs = eng.registry.get("outputs", {})
        unknown = [k for k in outputs_req if k not in registry_outputs]
        if unknown:
            valid = ", ".join(sorted(registry_outputs.keys())[:25])
            return JSONResponse(
                status_code=404,
                content={
                    "error": "output_not_found",
                    "detail": f"Output {unknown[0]!r} not found. Valid slugs include: {valid}",
                },
            )
        inputs_only = {k: v for k, v in body.items() if k != "outputs"}
        try:
            preds = eng.predict_selective(inputs_only, list(outputs_req))
            return _serialize_predictions(preds)
        except KeyError as e:
            return JSONResponse(
                status_code=404,
                content={"error": "output_not_found", "detail": str(e)},
            )
        except Exception as e:  # noqa: BLE001
            return JSONResponse(
                status_code=500,
                content={"error": "prediction_error", "detail": str(e)},
            )

    @app.get("/outputs")
    def list_outputs() -> Any:
        eng = require_engine()
        if eng is None:
            return _model_not_ready(model_version)
        rows: List[Dict[str, Any]] = []
        for slug, info in eng.registry.get("outputs", {}).items():
            rows.append({"slug": slug, **info})
        return rows

    @app.get("/inputs")
    def list_inputs() -> Any:
        eng = require_engine()
        if eng is None:
            return _model_not_ready(model_version)
        return _inputs_catalog(eng.registry)

    @app.get("/benchmark/{output_slug}")
    def benchmark_one(output_slug: str) -> Any:
        eng = require_engine()
        if eng is None:
            return _model_not_ready(model_version)
        reg_out = eng.registry.get("outputs", {})
        if output_slug not in reg_out:
            valid = ", ".join(sorted(reg_out.keys())[:25])
            return JSONResponse(
                status_code=404,
                content={
                    "error": "output_not_found",
                    "detail": f"Unknown output slug {output_slug!r}. Valid: {valid}",
                },
            )
        info = reg_out[output_slug]
        bench_name = info.get("benchmark_file", f"benchmark_{output_slug}.json")
        bench_path = eng.model_dir / bench_name
        if not bench_path.is_file():
            return JSONResponse(
                status_code=404,
                content={
                    "error": "output_not_found",
                    "detail": f"Missing benchmark file: {bench_path.name}",
                },
            )
        with open(bench_path, encoding="utf-8") as f:
            return json.load(f)

    return app


app = create_app()
