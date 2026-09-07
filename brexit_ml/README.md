# Brexit ML Engine (Phase 1)

Surrogate ML service for the IRE ↔ GB East/West corridor per `docs/ml/spec/brexit_ml_engine_spec.md`.

## Prerequisites

- Python 3.10+ (spec). If your default `python3` is older, create the venv with a newer interpreter, e.g. `python3.12 -m venv .venv`.
- Source workbook: place the AnyLogic export under `data/raw/`. The default path is `data/raw/completed_runs.xlsx`; if you keep the original filename (e.g. `Post-Brexit Sector Based Model - PostBrexit_latest model - Completed runs.xlsx`), pass it explicitly: `--xlsx "data/raw/Post-Brexit Sector Based Model - PostBrexit_latest model - Completed runs.xlsx"`.

## Setup

From this directory (`brexit_ml/`):

```bash
python3.10 -m venv .venv   # or python3.11 / python3.12
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional: `export PYTHONPATH=src` is not required when using `main.py` (it prepends `src/`) or when running pytest (see `pyproject.toml`).

## Data loading (Task 3)

With `data/raw/completed_runs.xlsx` in place:

```bash
python -c "from data_loader import load_xlsx, save_processed_parquet; from pathlib import Path; \
  X,Y = load_xlsx('data/raw/completed_runs.xlsx'); \
  save_processed_parquet(X, Y, Path('data/processed'))"
```

Or import `prepare_training_frames` for tests. Column names are defined in `src/training_columns.py` (generated from `docs/ml/spec/brexit_ml_engine_spec.md`).

## Train (Task 5)

Requires **XGBoost** with a working OpenMP runtime (on Apple Silicon / macOS: `brew install libomp` if import fails).

```bash
python src/train.py
# or reload from xlsx instead of cached parquet:
python src/train.py --reload-xlsx
```

Writes `models/v1/scaler_X.pkl`, per-output `model_*.pkl` / `classifier_*.pkl`, and `registry.json`. Phase 2 targets (35) are registered as `not_trained` without fitting.

## Run API (raw + semantic)

From `brexit_ml/`:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

`main.py` mounts the raw ML app and registers semantic routes. **CORS is off by default** (localhost-only); add middleware in `main.py` if a browser UI on another origin needs to call the API.

**Raw** (spec §21): `GET /health`, `POST /predict`, `POST /predict/selective`, `GET /outputs`, `GET /inputs`.

**Semantic** (spec §12): `POST /scenario/predict`, `POST /scenario/validate`, `GET /scenario/options`, `GET /scenario/schema`.

Without `models/v1/`, `/health` and raw predict return **503** `model_not_ready`; `/scenario/options` and `/scenario/schema` still work.

Check: `GET http://localhost:8000/health`

## Tests

From `brexit_ml/`:

```bash
pytest tests -v
```

## Layout

- `src/` — Python modules (`data_loader`, `train`, `ml_engine`, APIs, …)
- `data/raw/` — input xlsx (not committed)
- `data/processed/` — parquet features/targets
- `models/v1/` — scaler, per-output models, `registry.json` (not committed)
