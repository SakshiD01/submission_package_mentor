"""
HTTP integration tests for `run_ui_inference_api`: `/api/predict`, `/api/infer`, `/api/meta`.

Requires pipeline artefacts under `experimenting_ml/outputs/` (SHAP CSV, scaler, trained models).
"""

from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
NOLHC_SRC = ROOT.parent / "nolhc_ml" / "src"
SRC = ROOT / "src"
for _p in (SRC, NOLHC_SRC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _artifacts_ready() -> bool:
    o = ROOT / "outputs"
    return (
        (o / "step4_shap" / "shap_selected_models.csv").is_file()
        and (o / "trained_models" / "scaler.joblib").is_file()
    )


def _import_deps_ok() -> bool:
    """Skip integration tests when the venv does not include ML stack deps (e.g. joblib)."""
    try:
        import joblib  # noqa: F401
    except ImportError:
        return False
    return True


def _pick_target(selected: dict) -> str:
    for t in ("TT_OB_Agri",):
        if t in selected:
            return t
    return next(iter(selected))


@unittest.skipUnless(
    _artifacts_ready() and _import_deps_ok(),
    "requires joblib + experimenting_ml/outputs (shap_selected_models.csv, trained_models/scaler.joblib)",
)
class TestUiInferenceApiHttp(unittest.TestCase):
    """Boots ThreadingHTTPServer with the same Handler wiring as `main()`."""

    _httpd: Optional[ThreadingHTTPServer] = None
    _thread: Optional[threading.Thread] = None
    _port: int = 0

    @classmethod
    def setUpClass(cls) -> None:
        from run_ui_inference_api import Handler, InferenceEngine

        outputs = ROOT / "outputs"
        engine = InferenceEngine(outputs)
        level_inputs = {
            "routes": {
                "baseline": {
                    "directShare": 0.0,
                    "landbridgeShare": 100.0,
                    "ntbIrish": 0.0,
                    "ntbUK": 0.0,
                },
                "moderate": {
                    "directShare": 40.0,
                    "landbridgeShare": 60.0,
                    "ntbIrish": 40.0,
                    "ntbUK": 40.0,
                },
                "significant": {
                    "directShare": 85.0,
                    "landbridgeShare": 15.0,
                    "ntbIrish": 80.0,
                    "ntbUK": 80.0,
                },
            },
            "border": {
                "baseline": {
                    "inspectionEnhance": 0.0,
                    "landbridgeShare": 100.0,
                    "inspectionCoverage": 0.0,
                },
                "moderate": {
                    "inspectionEnhance": 40.0,
                    "landbridgeShare": 100.0,
                    "inspectionCoverage": 40.0,
                },
                "significant": {
                    "inspectionEnhance": 80.0,
                    "landbridgeShare": 100.0,
                    "inspectionCoverage": 80.0,
                },
            },
        }
        engine.feature_defaults_by_scenario = engine.compute_feature_defaults(level_inputs)
        Handler.engine = engine
        Handler.level_inputs = level_inputs
        cls._engine = engine

        cls._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls._port = cls._httpd.server_address[1]
        cls._thread = threading.Thread(target=cls._httpd.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._httpd is not None:
            cls._httpd.shutdown()
            cls._httpd.server_close()
        if cls._thread is not None:
            cls._thread.join(timeout=30)

    def _request_json(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        *,
        timeout: float = 180.0,
    ) -> Tuple[int, Dict[str, Any]]:
        url = f"http://127.0.0.1:{self._port}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                return e.code, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return e.code, {"_raw": raw}

    def test_get_api_meta_includes_selected_models(self) -> None:
        status, data = self._request_json("GET", "/api/meta")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertIn("selected_models", data)
        self.assertEqual(data["selected_models"], dict(self._engine.selected_models))

    def test_post_api_predict_stack_simulator_and_predictions(self) -> None:
        mf = {k: float(v) for k, v in self._engine.base.items()}
        focus = _pick_target(self._engine.selected_models)
        from training_columns import col_to_slug

        body = {
            "scenario_family": "routes",
            "scenario_level": "baseline",
            "inputs": {},
            "model_features": mf,
            "focus_target": focus,
            "light": True,
            "include_trend": False,
            "include_target_corr": False,
            "mc_samples": 24,
        }
        status, data = self._request_json("POST", "/api/predict", body)
        self.assertEqual(status, 200, data)
        self.assertTrue(data.get("ok"), data)
        stack = data.get("stack") or {}
        self.assertEqual(stack.get("pipeline"), "experimenting_ml")
        self.assertIn("outputs_dir", stack)
        self.assertEqual(stack.get("selected_models"), dict(self._engine.selected_models))
        preds = data.get("predictions") or {}
        self.assertIsInstance(preds, dict)
        self.assertGreaterEqual(len(preds), 1)
        self.assertIn(focus, preds)
        self.assertEqual(preds[focus].get("model"), self._engine.selected_models[focus])
        sim = data.get("simulator") or {}
        slug = col_to_slug(focus)
        self.assertIn(slug, sim)
        row = sim[slug]
        self.assertIn("value", row)
        self.assertIn("unit", row)
        self.assertEqual(row.get("registered_as"), preds[focus].get("model"))
        self.assertIn("monte_carlo", data)

    def test_post_api_predict_output_targets_filters_predictions(self) -> None:
        mf = {k: float(v) for k, v in self._engine.base.items()}
        focus = _pick_target(self._engine.selected_models)
        body = {
            "scenario_family": "routes",
            "scenario_level": "baseline",
            "inputs": {},
            "model_features": mf,
            "focus_target": focus,
            "light": True,
            "include_trend": False,
            "include_target_corr": False,
            "mc_samples": 16,
            "output_targets": [focus],
        }
        status, data = self._request_json("POST", "/api/predict", body)
        self.assertEqual(status, 200, data)
        self.assertTrue(data.get("ok"), data)
        preds = data.get("predictions") or {}
        self.assertEqual(set(preds.keys()), {focus})

    def test_post_api_infer_ok_and_predictions_shape(self) -> None:
        mf = {k: float(v) for k, v in self._engine.base.items()}
        focus = _pick_target(self._engine.selected_models)
        body = {
            "scenario_family": "routes",
            "scenario_level": "baseline",
            "inputs": {},
            "model_features": mf,
            "focus_target": focus,
            "light": True,
            "include_trend": False,
            "include_target_corr": False,
            "mc_samples": 16,
        }
        status, data = self._request_json("POST", "/api/infer", body)
        self.assertEqual(status, 200, data)
        self.assertTrue(data.get("ok"), data)
        preds = data.get("predictions") or {}
        self.assertGreaterEqual(len(preds), 1)
        self.assertIn(focus, preds)
        row = preds[focus]
        for key in ("model", "prediction", "baseline_prediction", "delta_vs_baseline", "interval"):
            self.assertIn(key, row)


if __name__ == "__main__":
    unittest.main()
