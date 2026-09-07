"""Smoke test: Node loads `ui/app.js` (module graph + top-level evaluation).

Run from package dir (`brexit_ml/`):  pytest tests/test_ui_app_smoke.py
Run from repo root:                   pytest brexit_ml/tests/test_ui_app_smoke.py
"""

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_DIR = PROJECT_ROOT / "ui"
SMOKE_SCRIPT = UI_DIR / "scripts" / "smoke-load-app.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed or not on PATH")
def test_ui_app_js_loads_under_node():
    assert SMOKE_SCRIPT.is_file(), f"Missing {SMOKE_SCRIPT}"
    proc = subprocess.run(
        [shutil.which("node"), str(SMOKE_SCRIPT)],
        cwd=str(UI_DIR),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, (
        f"node smoke-load-app failed ({proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "app.js and imports loaded OK" in proc.stdout
