"""Tests for LLM attribution layer (assembler + golden checks)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
SRC = ROOT / "src"
import sys

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from llm_attribution import (  # noqa: E402
    assemble_attribution_snapshot,
    build_messages,
    golden_numeric_fidelity,
)


def _expected_from_pipeline(target: str, model: str) -> tuple[float, float]:
    test = json.loads((OUTPUTS / "test_results.json").read_text(encoding="utf-8"))
    conf = json.loads((OUTPUTS / "conformal_results.json").read_text(encoding="utf-8"))
    return float(test[target][model]["rmse"]), float(conf[target][model]["interval_width"])


@unittest.skipUnless(
    (OUTPUTS / "test_results.json").is_file()
    and (OUTPUTS / "conformal_results.json").is_file()
    and (OUTPUTS / "step4_shap" / "shap_selected_models.csv").is_file(),
    "requires experimenting_ml/outputs pipeline artefacts",
)
class TestAssemblerIntegration(unittest.TestCase):
    def test_tt_ob_agri_matches_pipeline_json(self) -> None:
        s = assemble_attribution_snapshot("TT_OB_Agri", OUTPUTS)
        self.assertEqual(s.selected_model, "ExtraTrees")
        exp_rmse, exp_width = _expected_from_pipeline("TT_OB_Agri", "ExtraTrees")
        self.assertAlmostEqual(s.metrics.test_rmse, exp_rmse, places=5)
        self.assertAlmostEqual(s.interval_90.full_width, exp_width, places=5)
        self.assertEqual(s.residual_summary.n_test, 26)
        self.assertGreaterEqual(len(s.top_shap_features), 1)


class TestGoldenAndPrompts(unittest.TestCase):
    def test_golden_passes_when_json_echoed(self) -> None:
        if not (OUTPUTS / "test_results.json").is_file():
            self.skipTest("no outputs")
        snap = assemble_attribution_snapshot("TT_OB_Agri", OUTPUTS)
        text = snap.to_llm_json()
        v = golden_numeric_fidelity(text, snap)
        self.assertEqual(v, [])

    def test_messages_shape(self) -> None:
        if not (OUTPUTS / "test_results.json").is_file():
            self.skipTest("no outputs")
        snap = assemble_attribution_snapshot("TT_OB_Agri", OUTPUTS)
        msgs = build_messages("analyst_methods", snap, "What could go wrong?")
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[-1]["role"], "user")
        self.assertIn("ATTRIBUTION_FACTS", msgs[-1]["content"])
        self.assertIn(snap.target, msgs[-1]["content"])


class TestScriptedPersonaPrompts(unittest.TestCase):
    """Contract tests for scripted evaluation (per persona)."""

    def test_each_persona_builds(self) -> None:
        if not (OUTPUTS / "test_results.json").is_file():
            self.skipTest("no outputs")
        snap = assemble_attribution_snapshot("TT_OB_Agri", OUTPUTS)
        for pid in ("executive", "risk_compliance", "operations", "analyst_methods"):
            msgs = build_messages(pid, snap, "Explain this target.")
            blob = json.dumps(msgs)
            self.assertIn(snap.target, blob)
            self.assertIn(str(snap.metrics.test_rmse), blob)


if __name__ == "__main__":
    unittest.main()
