"""
Raw ML FastAPI routes (spec §21–22).
"""

from __future__ import annotations

import difflib
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ml_engine import MLEngine
from training_columns import TRAINING_COLUMN_ORDER


def _infer_input_unit(name: str) -> str:
    n = name.lower()
    if n.startswith("vol"):
        return "tonnes"
    if n.startswith("num"):
        return "count"
    if "cost" in n:
        return "EUR"
    if n.startswith("per") or "(%)" in name or "unacc" in n:
        return "fraction"
    if "time" in n or "chk" in n or "transit" in n:
        return "minutes"
    if "shelflife" in n:
        return "days"
    if "cap" in n:
        return "trailers"
    return "mixed"


def _inputs_catalog(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    med = registry.get("training_medians", {})
    out: List[Dict[str, Any]] = []
    for name in TRAINING_COLUMN_ORDER:
        out.append(
            {
                "name": name,
                "unit": _infer_input_unit(name),
                "typical": med.get(name),
                "min": None,
                "max": None,
            }
        )
    return out


def _serialize_predictions(preds: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v.model_dump() for k, v in preds.items()}


def _model_not_ready(version: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "error": "model_not_ready",
            "detail": f"No model files found in models/{version}/. Run: python src/train.py",
        },
    )


def create_app(
    *,
    model_version: str = "v1",
    models_root: Optional[Path] = None,
    engine: Optional[MLEngine] = None,
) -> FastAPI:
    app = FastAPI(
        title="Brexit ML Engine",
        version="1.0.0",
        description="Raw ML API (spec §21). Semantic routes are added separately.",
    )

    _engine: Optional[MLEngine] = engine
    if _engine is None:
        try:
            _engine = MLEngine(model_version, models_root=models_root)
        except FileNotFoundError:
            _engine = None

    def require_engine() -> Optional[MLEngine]:
        return _engine

    # Exposed for semantic routes (Task 12) and tests
    app.state.get_engine = require_engine  # type: ignore[attr-defined]
    app.state.model_version = model_version  # type: ignore[attr-defined]

    @app.get("/health")
    def health() -> Any:
        eng = require_engine()
        if eng is None:
            return _model_not_ready(model_version)
        reg = eng.registry
        outputs = reg.get("outputs", {})
        phase1 = sum(1 for o in outputs.values() if int(o.get("phase", 0)) == 1)
        phase2_trained = sum(
            1
            for o in outputs.values()
            if int(o.get("phase", 0)) == 2 and o.get("model_type") != "not_trained"
        )
        phase2_pending = sum(
            1
            for o in outputs.values()
            if int(o.get("phase", 0)) == 2 and o.get("model_type") == "not_trained"
        )
        return {
            "status": "ok",
            "model_version": eng.model_version,
            "training_runs": int(reg.get("training_runs", 0)),
            "phase1_models": phase1,
            "phase2_models_trained": phase2_trained,
            "phase2_models_pending": phase2_pending,
        }

    @app.post("/predict")
    def predict_raw(body: Dict[str, Any]) -> Any:
        eng = require_engine()
        if eng is None:
            return _model_not_ready(model_version)
        try:
            preds = eng.predict(body)
            return _serialize_predictions(preds)
        except Exception as e:
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
        outputs_req = body.get("outputs")
        if not outputs_req or not isinstance(outputs_req, list):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_input",
                    "detail": 'Request must include a non-empty "outputs" list of output slugs.',
                },
            )
        inputs = {k: v for k, v in body.items() if k != "outputs"}
        registry_outputs = eng.registry.get("outputs", {})
        unknown_parts: List[str] = []
        for key in outputs_req:
            if key not in registry_outputs:
                candidates = difflib.get_close_matches(
                    key, list(registry_outputs.keys()), n=1, cutoff=0.4
                )
                hint = f" Did you mean '{candidates[0]}'?" if candidates else ""
                unknown_parts.append(f"Output {key!r} not found.{hint}")
        if unknown_parts:
            return JSONResponse(
                status_code=422,
                content={
                    "error": "unknown_output",
                    "detail": " ".join(unknown_parts),
                },
            )
        try:
            full = eng.predict(inputs)
            sel = {k: full[k] for k in outputs_req if k in full}
            return _serialize_predictions(sel)
        except Exception as e:
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

    return app


app = create_app()
