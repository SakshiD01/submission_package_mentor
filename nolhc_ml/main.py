"""
Uvicorn entrypoint: NOLHC ML API + static UI (``ui/``).

Run from ``nolhc_ml/``:

    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Open http://127.0.0.1:8000/ — same origin as ``/predict`` (NOLHC_ML_UI_Spec.md §8).
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from ml_api import create_app  # noqa: E402

app = create_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_UI_DIR = Path(__file__).resolve().parent / "ui"
if _UI_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")
