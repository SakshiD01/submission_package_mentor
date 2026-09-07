"""
Uvicorn entrypoint: **raw** ML routes + **semantic** ``/scenario/*`` + static **UI** (``ui/``).

Run from this directory (``brexit_ml/``):

    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Then open **http://127.0.0.1:8000/** in a browser: same origin as the API (no CORS setup needed
for the default flow). Fill the form and **Run Simulation** to call ``POST /scenario/predict``.

CORS is enabled with permissive local-dev settings so the UI still works if you serve ``ui/`` from
another port or open a copied build from ``file://`` (not recommended).

``src/`` is prepended to ``sys.path`` so imports match the spec (``ml_api``, ``ml_engine``, …).
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from ml_api import create_app  # noqa: E402
from semantic_api import register_semantic_routes  # noqa: E402

app = create_app()
register_semantic_routes(app)

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
