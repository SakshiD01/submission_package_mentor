# Brexit Simulation ML Engine — Technical Design Specification

**Version:** 1.0  
**Scope:** Phase 1 — IRE ↔ GB East/West Corridor  
**Purpose:** Self-contained implementation reference for Cursor + Superpower plugin. No external document required.  
**Source data:** `Post-Brexit_Sector_Based_Model_-_PostBrexit_latest_model_-_Completed_runs__2_.xlsx` — 228 AnyLogic simulation runs  

---

## Table of Contents

1. [System Purpose](#1-system-purpose)
2. [Architecture Overview](#2-architecture-overview)
3. [Repository & Module Structure](#3-repository--module-structure)
4. [Dataset Facts](#4-dataset-facts)
5. [ML Core Design](#5-ml-core-design)
6. [Training Pipeline](#6-training-pipeline)
7. [Inference Pipeline](#7-inference-pipeline)
8. [Incremental Retraining](#8-incremental-retraining)
9. [Model Registry Schema](#9-model-registry-schema)
10. [Raw Input Parameters — Complete Reference](#10-raw-input-parameters--complete-reference)
11. [Raw Output Parameters — Complete Reference](#11-raw-output-parameters--complete-reference)
12. [Semantic API Layer](#12-semantic-api-layer)
13. [Semantic Input Fields — Complete Reference](#13-semantic-input-fields--complete-reference)
14. [Semantic Output Response Schema](#14-semantic-output-response-schema)
15. [Param Translator — Complete Mapping Logic](#15-param-translator--complete-mapping-logic)
16. [Check Regime Presets](#16-check-regime-presets)
17. [Port Routing Resolution](#17-port-routing-resolution)
18. [Output Filter Map](#18-output-filter-map)
19. [Phase 1 Scenario Definition](#19-phase-1-scenario-definition)
20. [Phase 2 Gap Analysis & Roadmap](#20-phase-2-gap-analysis--roadmap)
21. [FastAPI Endpoint Contract](#21-fastapi-endpoint-contract)
22. [Error Handling Contract](#22-error-handling-contract)
23. [Coverage & Confidence Flags](#23-coverage--confidence-flags)
24. [Technology Stack & Dependencies](#24-technology-stack--dependencies)
25. [Implementation Checklist for Cursor](#25-implementation-checklist-for-cursor)

---

## 1. System Purpose

The system replaces the need to run a full AnyLogic discrete-event simulation for every scenario. A trained ML model ensemble predicts simulation KPIs from input parameters in milliseconds rather than the minutes a full AnyLogic run takes.

**The core user problem being solved:** A user currently must provide all 158 AnyLogic parameter names with precise values to run a scenario. They do not know these parameter names, do not understand the units, and do not know which inputs affect which outputs. The system reduces this to 7 human-readable choices (supplier region, port, commodity, destination, route, check regime, resources) and returns only the KPIs relevant to their specific scenario.

**Two API layers serve two different consumers:**

| Layer | Endpoint | Consumer | Input format |
|---|---|---|---|
| Raw ML API | `POST /predict` | Technical integrations, chatbot | 153 AnyLogic column names |
| Semantic API | `POST /scenario/predict` | End-user UI, wizard, dropdowns | 7 semantic dimensions |

The Semantic API translates human selections into the Raw ML API format internally. The user never sees an AnyLogic column name.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  USER LAYER                                                  │
│  Wizard UI / Chatbot                                        │
│  7 guided fields: region → port → commodity →               │
│  destination → route → check_regime → resources             │
└──────────────────────────┬──────────────────────────────────┘
                           │ POST /scenario/predict
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  SEMANTIC API LAYER  (semantic_api.py)                      │
│                                                              │
│  1. ScenarioRequest validation (Pydantic)                   │
│  2. Corridor router → detects active corridor               │
│  3. param_translator.py → builds 153-col ML vector          │
│     - fills unused params with training medians             │
│  4. Calls Raw ML API internally                             │
│  5. output_filter.py → selects relevant KPIs                │
│  6. Labels results in plain English                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ internal call
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  RAW ML API LAYER  (ml_api.py)                              │
│  POST /predict                                               │
│  POST /predict/selective                                     │
│  GET  /outputs                                               │
│  GET  /inputs                                                │
│  GET  /health                                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  ML ENGINE  (ml_engine.py)                                  │
│  - Loads 136 XGBoost models from model registry             │
│  - StandardScaler applied to input vector                   │
│  - Zero-inflation classifier for sparse outputs             │
│  - Returns {output_name: value} dict                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                  │
│  data/processed/X_train.parquet   (153 features, 228 rows) │
│  data/processed/Y_train.parquet   (136 targets, 228 rows)  │
│  models/v{N}/model_{output}.pkl   (one per output)         │
│  models/v{N}/scaler_X.pkl                                   │
│  models/v{N}/registry.json                                  │
│  data/raw/completed_runs.xlsx                               │
└─────────────────────────────────────────────────────────────┘
```

**Request flow (Semantic):**
1. UI sends `POST /scenario/predict` with 7 semantic fields
2. `ScenarioRequest` validated by Pydantic
3. Corridor router determines `active_corridor` from Vol* fields
4. `param_translator.py` builds a 153-element dict, filling all unused params with training medians
5. ML engine runs all 136 models on the vector
6. `output_filter.py` selects the output keys relevant to `(commodity, direction, route_type)`
7. Results labelled, grouped, confidence-flagged, returned

---

## 3. Repository & Module Structure

```
brexit_ml/
│
├── data/
│   ├── raw/
│   │   └── completed_runs.xlsx           # Source AnyLogic export (never modified)
│   └── processed/
│       ├── X_train.parquet               # 228 rows × 153 input features
│       └── Y_train.parquet               # 228 rows × 136 output targets
│
├── models/
│   └── v1/
│       ├── scaler_X.pkl                  # sklearn StandardScaler fitted on X_train
│       ├── model_{output_key}.pkl        # one XGBoost model per output (136 files)
│       ├── classifier_{output_key}.pkl   # zero-inflation classifier (sparse outputs only)
│       └── registry.json                 # metadata: R², MAE, coverage, training date
│
├── src/
│   ├── data_loader.py                    # reads xlsx, extracts X/Y, saves parquet
│   ├── train.py                          # full training pipeline
│   ├── ml_engine.py                      # loads models, runs prediction
│   ├── ml_api.py                         # FastAPI: /predict, /health, /outputs, /inputs
│   ├── semantic_api.py                   # FastAPI: /scenario/predict, /scenario/options
│   ├── param_translator.py               # semantic → raw param mapping
│   ├── output_filter.py                  # selects relevant outputs per scenario
│   ├── corridor_router.py                # detects active corridor from Vol* inputs
│   └── schemas.py                        # all Pydantic request/response models
│
├── tests/
│   ├── test_translator.py
│   ├── test_output_filter.py
│   └── test_api.py
│
├── requirements.txt
├── main.py                               # entrypoint: uvicorn app
└── README.md
```

---

## 4. Dataset Facts

All numbers in this section are computed from the actual xlsx file. These are ground truth — use them directly in code.

### 4.1 Dimensions

| Property | Value |
|---|---|
| Source file | `Post-Brexit_Sector_Based_Model_-_PostBrexit_latest_model_-_Completed_runs__2_.xlsx` |
| Sheet name | `Completed runs` |
| Header row | **Row index 1** (row 0 is blank — critical for parsing) |
| Data start row | Row index 2 |
| Total completed runs | **228** |
| Raw input columns | **158** |
| Input columns after dropping constants | **153** |
| Output target columns | **136** |
| Phase 1 output targets | **101** |
| Phase 2 output targets (placeholder) | **35** |
| Simulation period (all runs) | 30 days: 2020-02-22 to 2020-03-23 |
| All run statuses | Successful |

### 4.2 Corridor Activation

| Corridor | Active runs | % of total | Phase | Trainability |
|---|---|---|---|---|
| IRE ↔ GB East/West | 165 / 228 | 72% | **1** | ✅ Trainable |
| IRE ↔ EU Landbridge | 11 / 228 | 5% | 2 | ❌ Insufficient — always bundled with IRE-GB |
| IRE ↔ EU Cherbourg | 11 / 228 | 5% | 2 | ❌ Insufficient — no standalone runs |
| IRE ↔ EU Rotterdam | 11 / 228 | 5% | 2 | ❌ Insufficient — no standalone runs |
| IRE ↔ EU Zeebrugge | 11 / 228 | 5% | 2 | ❌ Insufficient — no standalone runs |
| IRE ↔ EU Bilbao | 3 / 228 | 1% | 2 | ❌ Not trainable — only 3 runs |
| GB ↔ EU Dover/Calais | 11 / 228 | 5% | 2 | ❌ Insufficient — only bundled |

> **Phase 1 training uses all 228 runs** for IRE-GB corridor outputs. EU corridor outputs remain untrained (`status: "not_trained"`, `value: null`) until Phase 2 AnyLogic runs are generated (50–60 standalone runs per corridor recommended).

### 4.3 Border Check Regime Distribution in Training Data

| Regime label | Run count | `PerGreenTrucksAPImIR` | `PerPhyChkAPImIR` |
|---|---|---|---|
| `none` (pre-Brexit baseline) | 9 | 1.0 | 0.0 |
| `light` (customs export only) | 114 | 1.0 | 0.0–0.05 |
| `standard` (10% physical checks) | 3 | 0.9 | 0.10 |
| `hard` (30%+ physical checks) | 102 | 0.7 | 0.30+ |

### 4.4 Columns to Drop (Zero Variance — No Predictive Signal)

These 5 columns are constant across all 228 runs. Drop before training.

```python
CONSTANT_COLS_TO_DROP = [
    "VolAllPExViaBil",    # all values = 0
    "VolAgriImViaBil",    # all values = 0
    "VolAgriExViaBil",    # all values = 0
    "VolCatImViaBil",     # all values = 0
    "CusIntTimeExGB-E",   # all values = 0
]
```

---

## 5. ML Core Design

### 5.1 Algorithm Selection

**Algorithm: XGBoost Regressor (one model per output target)**

Rationale:
- 228 training rows × 153 features → firmly in the regime where gradient boosted trees outperform neural networks (neural nets need thousands of rows to regularise)
- Handles mixed-scale inputs natively (percentages alongside tonnage in millions) without manual feature engineering
- Naturally handles sparse outputs (many zeros) via the zero-inflation approach below
- Produces feature importances for free — used by the chatbot explanation layer
- Full retrain takes < 30 seconds at this data size — simpler and safer than incremental learning

**Alternative rejected: Multi-output XGBoost** — not used because outputs have different active-corridor conditions. A single multi-output model trained on 136 sparse targets would be biased toward zero. Separate per-output models each learn from the subset of runs where that output is meaningful.

**Alternative rejected: Local LLM (Llama etc.)** — wrong modality. LLMs are generative text models; this is a structured numerical regression problem on tabular simulation data.

**Alternative rejected: RapidMiner** — GUI-only workflow, no Python API, licensing cost, cannot be embedded in a FastAPI service.

### 5.2 Zero-Inflation Strategy

Many output targets are non-zero in fewer than 30% of runs (e.g., most per-port waiting times). If you train a plain regressor on these, it is biased toward zero and produces inaccurate predictions for the non-zero cases.

**For outputs with < 30% non-zero coverage:** train a two-stage model:
1. **Classifier** (`XGBClassifier`): predicts `is_nonzero` (binary). Trained on all 228 rows.
2. **Regressor** (`XGBRegressor`): predicts the actual value. Trained only on the non-zero rows.

At inference, run the classifier first. If `is_nonzero = False`, return `0.0` with `status: "zero_predicted"`. If `True`, run the regressor.

**For outputs with ≥ 30% non-zero coverage:** train a plain `XGBRegressor` on all rows.

```python
# Threshold in train.py
ZERO_INFLATION_THRESHOLD = 0.30  # use two-stage model if coverage < 30%
```

### 5.3 Preprocessing

```python
# 1. Drop constant columns (5 columns listed in Section 4.4)
# 2. Replace NaN with 0 (AnyLogic exports 0 for unused corridors)
# 3. Fit StandardScaler on X_train, save as scaler_X.pkl
# 4. Apply scaler to X before training and inference

from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_train)
```

### 5.4 XGBoost Hyperparameters (Starting Point)

```python
XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "objective": "reg:squarederror",
    "random_state": 42,
    "n_jobs": -1,
}
```

Tune with 5-fold cross-validation. Given 228 rows, do not use test/train split alone — CV is essential.

### 5.5 Validation Strategy

- **5-fold cross-validation** on all 228 rows (stratified by corridor activation)
- Metrics recorded per output: **R²** (coefficient of determination) and **MAE** (mean absolute error)
- Validation run at end of every `train.py` execution
- Results stored in `registry.json` (see Section 9)
- **Corridor holdout test**: for Phase 1, hold out 10% of IRE-GB-only runs as a final test set

```python
from sklearn.model_selection import cross_val_score
cv_r2  = cross_val_score(model, X_scaled, y, cv=5, scoring="r2")
cv_mae = cross_val_score(model, X_scaled, y, cv=5, scoring="neg_mean_absolute_error")
```

---

## 6. Training Pipeline

File: `src/train.py`

### Step-by-step execution order

```
1.  data_loader.load_xlsx()
    - reads completed_runs.xlsx
    - header row index = 1 (NOT 0)
    - drops rows where Run# is null
    - drops rows where Status != "Successful"
    - drops the 5 CONSTANT_COLS_TO_DROP
    - replaces '<Data>' sentinel values with NaN, then fills NaN with 0
    - splits into X (153 cols) and Y (136 cols)
    - saves X_train.parquet and Y_train.parquet

2.  scaler = StandardScaler().fit(X)
    - saves to models/v{N}/scaler_X.pkl

3.  For each output column in Y (136 total):
    a.  compute coverage = (Y[col] != 0).mean()
    b.  if coverage < ZERO_INFLATION_THRESHOLD (0.30):
            train XGBClassifier on (X_scaled, (Y[col] != 0).astype(int))
            save classifier_{col_slug}.pkl
            train XGBRegressor on rows where Y[col] != 0
            save model_{col_slug}.pkl
        else:
            train XGBRegressor on all rows
            save model_{col_slug}.pkl
    c.  run 5-fold CV, record R² and MAE

4.  build registry.json (see Section 9)

5.  print summary: models trained, avg R², any output with R² < 0.5 flagged as warning
```

### Column slug generation

Output column names contain spaces and special characters. Convert to filesystem-safe slugs:

```python
import re
def col_to_slug(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug[:80]  # max 80 chars

# Examples:
# "Transportation time agri exportto GB" → "transportation_time_agri_exportto_gb"
# "DDAFM insp bay utilisation"           → "ddafm_insp_bay_utilisation"
# "AP avg WT on im at D"                 → "ap_avg_wt_on_im_at_d"
```

---

## 7. Inference Pipeline

File: `src/ml_engine.py`

```python
class MLEngine:
    def __init__(self, model_version: str = "v1"):
        # on startup: load scaler, all model files, registry
        self.scaler = joblib.load(f"models/{model_version}/scaler_X.pkl")
        self.models = {}         # {output_key: XGBRegressor}
        self.classifiers = {}    # {output_key: XGBClassifier}  (sparse outputs only)
        self.registry = json.load(open(f"models/{model_version}/registry.json"))
        self._load_all_models(model_version)

    def predict(self, input_vector: dict) -> dict:
        """
        input_vector: dict with up to 153 keys (AnyLogic column names).
        Missing keys are filled with training medians from registry.
        Returns: dict of {output_key: PredictionResult}
        """
        # 1. Fill missing inputs with training medians
        X = self._fill_defaults(input_vector)

        # 2. Build ordered numpy array matching training column order
        x_arr = np.array([X[col] for col in TRAINING_COLUMN_ORDER]).reshape(1, -1)

        # 3. Apply scaler
        x_scaled = self.scaler.transform(x_arr)

        # 4. Run each model
        results = {}
        for output_key, model in self.models.items():
            info = self.registry["outputs"][output_key]

            # Zero-inflation check
            if output_key in self.classifiers:
                is_nonzero = self.classifiers[output_key].predict(x_scaled)[0]
                if not is_nonzero:
                    results[output_key] = PredictionResult(
                        value=0.0, status="zero_predicted",
                        phase=info["phase"], unit=info["unit"]
                    )
                    continue

            value = float(model.predict(x_scaled)[0])
            coverage = info["coverage_pct"]
            status = "ok" if coverage >= 15 else "low_coverage"

            # Phase 2 outputs: model not trained, return null
            if info["phase"] == 2:
                status = "not_trained"
                value = None

            results[output_key] = PredictionResult(
                value=value, status=status,
                phase=info["phase"], unit=info["unit"],
                r2=info["r2"], coverage_pct=coverage
            )

        return results
```

### `TRAINING_COLUMN_ORDER`

This list must be hardcoded in `ml_engine.py`. It is the exact order of the 153 input columns after dropping constants, as they appear in the xlsx header row. The complete ordered list is:

```python
TRAINING_COLUMN_ORDER = [
    "VolAllPImGB", "VolAllPExGB", "VolAgriImGB", "VolAgriExGB",
    "VolCatImGB", "VolCatExGB", "VolAllPImEULB", "VolAllPExEULB",
    "VolAgriImEULB", "VolAgriExEULB", "VolCatImEULB", "VolCatExEULB",
    "VolAllPImViaChe", "VolAllPExViaChe", "VolAgriImViaChe", "VolAgriExViaChe",
    "VolCatImViaChe", "VolCatExViaChe", "VolAllPImViaRott", "VolAllPExViaRott",
    "VolAgriImViaRott", "VolAgriExViaRott", "VolCatImViaRott", "VolCatExViaRott",
    "VolAllPImViaZee", "VolAllPExViaZee", "VolAgriImViaZee", "VolAgriExViaZee",
    "VolCatImViaZee", "VolCatExViaZee", "VolAllPImViaBil",
    # NOTE: VolAllPExViaBil, VolAgriImViaBil, VolAgriExViaBil, VolCatImViaBil DROPPED (constant)
    "VolCatExViaBil", "VolAllPImGBEU", "VolAllPExGBEU",
    "PerCusIntTrucksAPExIR", "CusIntTimeAPExIR",
    "PerCusIntTrucksAgriExIR", "CusIntTimeAgriExIR",
    "PerCusIntTrucksCatExIR", "CusIntTimeCatExIR",
    "PerGreenTrucksAPImIR", "DocChkTimeAPImIR", "PerPhyChkAPImIR",
    "PhyChkTimeAPImIR", "PerSecurityChkAPIR", "SecChkTimeAPImIR",
    "DocChkTimeAgriImIR", "PerPhyChkAgriImIR", "PhyChkTimeAgriImIR",
    "PerSecurityChkAgriIR", "SecChkTimeAgriImIR",
    "DocChkTimeCatImIR", "PerPhyChkCatImIR", "PhyChkTimeCatImIR",
    "PerSecurityChkCatIR", "SecChkTimeCatImIR",
    "PerCusIntTrucksAPExGB-W", "CusIntTimeAPExGB-W",
    "PerCusIntTrucksAgriExGB-W", "CusIntTimeAgriExGB-W",
    "PerCusIntTrucksCatExGB-W", "CusIntTimeCatExGB-W",
    "PerGreenTrucksAPImGB-W", "DocChkTimeAPImGB-W", "PerPhyChkAPImGB-W",
    "PhyChkTimeAPImGB-W", "PerSecChkAPImGB-W", "SecChkTimeAPImGB-W",
    "DocChkTimeAgriImGB-W", "PerPhyChkAgriImGB-W", "PhyChkTimeAgriImGB-W",
    "PerSecChkAgriImGB-W", "SecChkTimeAgriImGB-W",
    "DocChkTimeCatImGB-W", "PerPhyChkCatImGB-W", "PhyChkTimeCatImGB-W",
    "PerSecChkCatImGB-W", "SecChkTimeCatImGB-W",
    "PerCusIntTrucksExGB-E",
    # NOTE: CusIntTimeExGB-E DROPPED (constant)
    "PerGreenTrucksImGB-E", "DocChkTimeImGB-E", "PerPhyChkImGB-E",
    "PhyChkTimeImGB-E", "PerSecChkImGB-E", "SecChkTimeImGB-E",
    "PerCusIntTrucksExEU", "CusIntTimeExEU", "PerGreenTrucksImEU",
    "DocCheckTimeImEU", "PerPhyChkImEU", "PhyCheckTimeImEU",
    "PerSecurityChkEU", "SecCheckTimeEU",
    "TransitCheckTimeLB", "PerPhyChkLB", "PhyCheckTimeLB",
    "PerSecurityChkLB", "SecCheckTimeLB",
    "NumCustomShedD", "NumDAFMInspBayD", "NumSecurityPostD", "NumTractorD",
    "NumCustomShedR", "NumDAFMInspBayR", "NumSecurityPostR", "NumTractorR",
    "NumCustomShedGB-W", "NumDAFMInspBayGB-W", "NumSecurityPostGB-W", "NumTractorGB-W",
    "NumCustomShedHoly", "NumDAFMInspBayHoly", "NumSecurityPostHoly", "NumTractorHoly",
    "NumCustomShedLiv", "NumDAFMInspBayLiv", "NumSecurityPostLiv", "NumTractorLiv",
    "NumCustomShedDov", "NumDAFMInspBayDov", "NumSecurityPostDov", "NumTractorDov",
    "NumCustomShedEU", "NumDAFMInspBayEU", "NumSecurityPostEU", "NumTractorEU",
    "PerUKTrucksMoveD", "PerLBTrucksMoveD",
    "DToHeyVesselCap", "DToLivVesselCap", "DToHolyVesselCap",
    "RToFishVesselCap", "RToPemVesselCap",
    "PerProductMoveHey", "PerProductMoveLiv", "PerProductMoveHoly",
    "PerProductMoveFish", "PerProductMovePem",
    "PerLBTrucksMoveToHey", "PerLBTrucksMoveToLiv", "PerLBTrucksMoveToHoly",
    "PerLBTrucksMoveToFish", "PerLBTrucksMoveToPem",
    "DToCheVesselCap", "DToRottVesselCap", "DToZeeVesselCap",
    "RToCheVesselCap", "RToBilVesselCap",
    "AvgShelflife(ProdCat)", "UnAccTrucks(%)",
    "DocCheckCost", "PhyCheckCost", "SecurityCheckCost",
]
# Total: 153 columns
```

---

## 8. Incremental Retraining

File: `src/train.py` — called with `--append` flag

```bash
# Add new runs and retrain
python src/train.py --new-runs path/to/new_runs.xlsx --append

# Full retrain from scratch (same command without --append)
python src/train.py
```

**Append logic:**
1. Load existing `X_train.parquet` and `Y_train.parquet`
2. Load new xlsx, apply same parsing/cleaning as initial load
3. Deduplicate on `Run #` column
4. Concatenate and save updated parquet files
5. Bump version: `v1 → v2`, create new `models/v2/` directory
6. Run full training pipeline on combined dataset
7. Print R² delta per output (new R² − old R²) to show improvement

**Why full retrain vs. incremental:** XGBoost does not support true online learning safely. At 228–500 rows, full retrain takes < 30 seconds. This is the correct approach for this data size.

---

## 9. Model Registry Schema

File: `models/v{N}/registry.json`

```json
{
  "version": "v1",
  "trained_at": "2024-03-22T14:32:01Z",
  "training_runs": 228,
  "input_features": 153,
  "output_targets": 136,
  "scaler": "scaler_X.pkl",
  "training_medians": {
    "VolAllPImGB": 6303240.0,
    "VolAllPExGB": 6639344.0,
    "VolAgriImGB": 4836066.0,
    "VolAgriExGB": 3524590.0,
    "VolCatImGB": 4180328.0,
    "VolCatExGB": 5000000.0,
    "NumCustomShedD": 30.0,
    "NumDAFMInspBayD": 27.0,
    "NumSecurityPostD": 19.0,
    "NumTractorD": 49.0,
    "PerProductMoveLiv": 0.4,
    "PerProductMoveHoly": 0.47,
    "PerProductMoveHey": 0.03,
    "DToHolyVesselCap": 209.0,
    "DToLivVesselCap": 123.0,
    "DToHeyVesselCap": 122.0,
    "AvgShelflife(ProdCat)": 14.0,
    "UnAccTrucks(%)": 0.5,
    "DocCheckCost": 50.0,
    "PhyCheckCost": 500.0,
    "SecurityCheckCost": 500.0
    // ... all 153 training medians
  },
  "outputs": {
    "transportation_time_agri_import_from_gb": {
      "raw_key": "Transportation time agri import from GB",
      "model_file": "model_transportation_time_agri_import_from_gb.pkl",
      "classifier_file": null,
      "phase": 1,
      "unit": "hours",
      "coverage_pct": 23,
      "model_type": "xgb_regressor",
      "r2_cv_mean": 0.87,
      "r2_cv_std": 0.04,
      "mae_cv_mean": 0.42,
      "zero_inflated": false
    },
    "agri_avg_wt_on_im_at_d": {
      "raw_key": "Agri avg WT on im at D",
      "model_file": "model_agri_avg_wt_on_im_at_d.pkl",
      "classifier_file": "classifier_agri_avg_wt_on_im_at_d.pkl",
      "phase": 1,
      "unit": "hours",
      "coverage_pct": 15,
      "model_type": "zero_inflated_xgb",
      "r2_cv_mean": 0.79,
      "r2_cv_std": 0.07,
      "mae_cv_mean": 0.08,
      "zero_inflated": true
    },
    "transportation_time_exportto_eulb": {
      "raw_key": "Transportation time exportto EULB",
      "model_file": null,
      "classifier_file": null,
      "phase": 2,
      "unit": "hours",
      "coverage_pct": 5,
      "model_type": "not_trained",
      "r2_cv_mean": null,
      "mae_cv_mean": null,
      "zero_inflated": false
    }
  }
}
```

---

## 10. Raw Input Parameters — Complete Reference

These are the **exact AnyLogic column names** used as ML input features. All units listed. Used directly in `POST /predict`. The Param Translator maps Semantic API fields to these names.

> **Conventions:** percentages are 0.0–1.0 fractions, times in minutes, volumes in tonnes, counts are integers.

### Section 1 — Trade Volumes

| Parameter | Min | Max | Typical (non-zero median) | Non-zero runs | Description |
|---|---|---|---|---|---|
| `VolAllPImGB` | 0 | 13,050,000 | 6,303,240 | 116/228 | All products imported GB→IRE (tonnes) |
| `VolAllPExGB` | 0 | 13,593,750 | 6,639,344 | 65/228 | All products exported IRE→GB (tonnes) |
| `VolAgriImGB` | 0 | 8,606,557 | 4,836,066 | 97/228 | Agri-food imported GB→IRE (tonnes) |
| `VolAgriExGB` | 0 | 9,262,295 | 3,524,590 | 66/228 | Agri-food exported IRE→GB (tonnes) |
| `VolCatImGB` | 0 | 7,734,375 | 4,180,328 | 77/228 | Product category imported GB→IRE (tonnes) |
| `VolCatExGB` | 0 | 9,754,098 | 5,000,000 | 55/228 | Product category exported IRE→GB (tonnes) |
| `VolAllPImEULB` | 0 | 5,141,622 | 1,205,760 | 11/228 | All products EU→IRE via Landbridge (Ph2) |
| `VolAllPExEULB` | 0 | 8,200,000 | 1,057,920 | 11/228 | All products IRE→EU via Landbridge (Ph2) |
| `VolAgriImEULB` | 0 | 555,114 | 313,123 | 11/228 | Agri EU→IRE via Landbridge (Ph2) |
| `VolAgriExEULB` | 0 | 414,629 | 255,354 | 11/228 | Agri IRE→EU via Landbridge (Ph2) |
| `VolCatImEULB` | 0 | 6,898 | 6,898 | 3/228 | Category EU→IRE via Landbridge (Ph2) |
| `VolCatExEULB` | 0 | 6,316,339 | 43,146 | 4/228 | Category IRE→EU via Landbridge (Ph2) |
| `VolAllPImViaChe` | 0 | 7,700,000 | 347,000 | 11/228 | All products Cherbourg→IRE (Ph2) |
| `VolAllPExViaChe` | 0 | 258,000 | 254,000 | 11/228 | All products IRE→Cherbourg (Ph2) |
| `VolAgriImViaChe` | 0 | 173,605 | 129,149 | 11/228 | Agri Cherbourg→IRE (Ph2) |
| `VolAgriExViaChe` | 0 | 48,975 | 35,282 | 11/228 | Agri IRE→Cherbourg (Ph2) |
| `VolCatImViaChe` | 0 | 8,688,525 | 8,239 | 5/228 | Category Cherbourg→IRE (Ph2) |
| `VolCatExViaChe` | 0 | 5,300,000 | 64,876 | 4/228 | Category IRE→Cherbourg (Ph2) |
| `VolAllPImViaRott` | 0 | 417,000 | 417,000 | 11/228 | All products Rotterdam→IRE (Ph2) |
| `VolAllPExViaRott` | 0 | 256,000 | 256,000 | 11/228 | All products IRE→Rotterdam (Ph2) |
| `VolAgriImViaRott` | 0 | 3,800,000 | 153,985 | 11/228 | Agri Rotterdam→IRE (Ph2) |
| `VolAgriExViaRott` | 0 | 6,301,804 | 35,282 | 11/228 | Agri IRE→Rotterdam (Ph2) |
| `VolCatImViaRott` | 0 | 3,936 | 3,936 | 3/228 | Category Rotterdam→IRE (Ph2) |
| `VolCatExViaRott` | 0 | 55,480 | 25,077 | 3/228 | Category IRE→Rotterdam (Ph2) |
| `VolAllPImViaZee` | 0 | 900,000 | 593,000 | 11/228 | All products Zeebrugge→IRE (Ph2) |
| `VolAllPExViaZee` | 0 | 290,000 | 290,000 | 11/228 | All products IRE→Zeebrugge (Ph2) |
| `VolAgriImViaZee` | 0 | 293,793 | 218,560 | 11/228 | Agri Zeebrugge→IRE (Ph2) |
| `VolAgriExViaZee` | 0 | 55,097 | 39,692 | 11/228 | Agri IRE→Zeebrugge (Ph2) |
| `VolCatImViaZee` | 0 | 2,697 | 2,697 | 3/228 | Category Zeebrugge→IRE (Ph2) |
| `VolCatExViaZee` | 0 | 21,086 | 7,418 | 3/228 | Category IRE→Zeebrugge (Ph2) |
| `VolAllPImViaBil` | 0 | 18,000 | 18,000 | 3/228 | All products Bilbao→IRE (Ph2, 3 runs only) |
| ~~`VolAllPExViaBil`~~ | — | — | — | 0/228 | **CONSTANT — DROPPED** |
| ~~`VolAgriImViaBil`~~ | — | — | — | 0/228 | **CONSTANT — DROPPED** |
| ~~`VolAgriExViaBil`~~ | — | — | — | 0/228 | **CONSTANT — DROPPED** |
| ~~`VolCatImViaBil`~~ | — | — | — | 0/228 | **CONSTANT — DROPPED** |
| `VolCatExViaBil` | 0 | 6,065,574 | 6,065,574 | 1/228 | Category IRE→Bilbao (1 run, Ph2) |
| `VolAllPImGBEU` | 0 | 7,551,000 | 7,551,000 | 11/228 | All products EU→GB Dover/Calais (Ph2) |
| `VolAllPExGBEU` | 0 | 10,853,000 | 10,853,000 | 11/228 | All products GB→EU Dover/Calais (Ph2) |

### Section 2 — Border Checks at Irish Ports (Export — IRE Outbound)

| Parameter | Min | Max | Typical | Non-zero | Description |
|---|---|---|---|---|---|
| `PerCusIntTrucksAPExIR` | 0 | 1.0 | 1.0 | 65/228 | Fraction all-product trucks with customs check on export from IRE |
| `CusIntTimeAPExIR` | 0 | 475 min | 266 min | 64/228 | Customs intervention time per truck, all products export |
| `PerCusIntTrucksAgriExIR` | 0 | 1.0 | 1.0 | 99/228 | Fraction agri trucks with customs check on export from IRE |
| `CusIntTimeAgriExIR` | 0 | 475 min | 201 min | 89/228 | Customs time per agri truck on export |
| `PerCusIntTrucksCatExIR` | 0 | 1.0 | 1.0 | 71/228 | Fraction category trucks with customs on export |
| `CusIntTimeCatExIR` | 0 | 453 min | 242 min | 61/228 | Customs time per category truck on export |

### Section 2 — Border Checks at Irish Ports (Import — GB Inbound to IRE)

| Parameter | Min | Max | Typical | Non-zero | Description |
|---|---|---|---|---|---|
| `PerGreenTrucksAPImIR` | 0 | 1.0 | 1.0 | 114/228 | Fraction all-product trucks → green route (no check). Set 1.0 for pre-Brexit |
| `DocChkTimeAPImIR` | 0 | 465 min | 242 min | 109/228 | Documentary + identity check time per truck (orange route) |
| `PerPhyChkAPImIR` | 0 | 1.0 | 1.0 | 105/228 | Fraction all-product trucks → physical check (red route) |
| `PhyChkTimeAPImIR` | 0 | 943 min | 385 min | 109/228 | Physical check time per truck |
| `PerSecurityChkAPIR` | 0 | 1.0 | 1.0 | 105/228 | Fraction all-product trucks → security/licence/immigration check |
| `SecChkTimeAPImIR` | 0 | 803 min | 377 min | 106/228 | Security check time per truck |
| `DocChkTimeAgriImIR` | 0 | 414 min | 172 min | 87/228 | Documentary check time per agri truck |
| `PerPhyChkAgriImIR` | 0 | 1.0 | 1.0 | 85/228 | Fraction agri trucks → SPS physical inspection |
| `PhyChkTimeAgriImIR` | 0 | 803 min | 385 min | 87/228 | SPS physical inspection time per agri truck |
| `PerSecurityChkAgriIR` | 0 | 1.0 | 1.0 | 85/228 | Fraction agri trucks → security check |
| `SecChkTimeAgriImIR` | 0 | 787 min | 426 min | 91/228 | Security check time per agri truck |
| `DocChkTimeCatImIR` | 0 | 369 min | 168 min | 72/228 | Documentary check time per category truck |
| `PerPhyChkCatImIR` | 0 | 1.0 | 1.0 | 72/228 | Fraction category trucks → physical check |
| `PhyChkTimeCatImIR` | 0 | 781 min | 398 min | 72/228 | Physical check time per category truck |
| `PerSecurityChkCatIR` | 0 | 1.0 | 1.0 | 72/228 | Fraction category trucks → security check |
| `SecChkTimeCatImIR` | 0 | 811 min | 367 min | 72/228 | Security check time per category truck |

### Section 2 — Border Checks at GB-West Ports

| Parameter | Min | Max | Typical | Non-zero | Description |
|---|---|---|---|---|---|
| `PerCusIntTrucksAPExGB-W` | 0 | 1.0 | 1.0 | 107/228 | Fraction all-product trucks with customs on export at GB-West |
| `CusIntTimeAPExGB-W` | 0 | 369 min | 262 min | 101/228 | Customs time at GB-West, all products |
| `PerCusIntTrucksAgriExGB-W` | 0 | 1.0 | 1.0 | 92/228 | Fraction agri trucks with customs at GB-West |
| `CusIntTimeAgriExGB-W` | 0 | 375 min | 246 min | 82/228 | Customs time agri trucks at GB-West |
| `PerCusIntTrucksCatExGB-W` | 0 | 1.0 | 1.0 | 69/228 | Fraction category trucks with customs at GB-West |
| `CusIntTimeCatExGB-W` | 0 | 363 min | 201 min | 62/228 | Customs time category trucks at GB-West |
| `PerGreenTrucksAPImGB-W` | 0 | 1.0 | 1.0 | 56/228 | Fraction trucks → green route at GB-West import |
| `DocChkTimeAPImGB-W` | 0 | 418 min | 172 min | 61/228 | Documentary check time at GB-West |
| `PerPhyChkAPImGB-W` | 0 | 1.0 | 1.0 | 49/228 | Fraction trucks → physical check at GB-West |
| `PhyChkTimeAPImGB-W` | 0 | 898 min | 475 min | 61/228 | Physical check time at GB-West |
| `PerSecChkAPImGB-W` | 0 | 1.0 | 1.0 | 47/228 | Fraction trucks → security check at GB-West |
| `SecChkTimeAPImGB-W` | 0 | 281 min | 136 min | 61/228 | Security check time at GB-West |
| `DocChkTimeAgriImGB-W` | 0 | 443 min | 197 min | 60/228 | Agri documentary check at GB-West |
| `PerPhyChkAgriImGB-W` | 0 | 1.0 | 1.0 | 53/228 | Agri physical check fraction at GB-West |
| `PhyChkTimeAgriImGB-W` | 0 | 891 min | 582 min | 60/228 | Agri physical check time at GB-West |
| `PerSecChkAgriImGB-W` | 0 | 1.0 | 1.0 | 56/228 | Agri security check fraction at GB-West |
| `SecChkTimeAgriImGB-W` | 0 | 891 min | 598 min | 60/228 | Agri security check time at GB-West |
| `DocChkTimeCatImGB-W` | 0 | 441 min | 223 min | 59/228 | Category documentary check at GB-West |
| `PerPhyChkCatImGB-W` | 0 | 1.0 | 1.0 | 55/228 | Category physical check fraction at GB-West |
| `PhyChkTimeCatImGB-W` | 0 | 959 min | 410 min | 58/228 | Category physical check time at GB-West |
| `PerSecChkCatImGB-W` | 0 | 1.0 | 1.0 | 47/228 | Category security check fraction at GB-West |
| `SecChkTimeCatImGB-W` | 0 | 859 min | 549 min | 58/228 | Category security check time at GB-West |

### Section 2 — GB-East (Dover) and EU (Calais) — Phase 2

| Parameter | Min | Max | Typical | Non-zero | Description |
|---|---|---|---|---|---|
| `PerCusIntTrucksExGB-E` | 0 | 1.0 | 1.0 | 14/228 | Phase 2 — Landbridge Dover export customs |
| ~~`CusIntTimeExGB-E`~~ | — | — | — | 0/228 | **CONSTANT — DROPPED** |
| `PerGreenTrucksImGB-E` | 0 | 1.0 | 1.0 | 15/228 | Phase 2 |
| `DocChkTimeImGB-E` | 0 | 20 min | 20 min | 3/228 | Phase 2 |
| `PerPhyChkImGB-E` | 0 | 0.1 | 0.1 | 3/228 | Phase 2 |
| `PhyChkTimeImGB-E` | 0 | 60 min | 60 min | 3/228 | Phase 2 |
| `PerSecChkImGB-E` | 0 | 0.1 | 0.1 | 3/228 | Phase 2 |
| `SecChkTimeImGB-E` | 0 | 20 min | 20 min | 3/228 | Phase 2 |
| `PerCusIntTrucksExEU` | 0 | 1.0 | 1.0 | 14/228 | Phase 2 — EU Calais export customs |
| `CusIntTimeExEU` | 0 | 254 min | 254 min | 1/228 | Phase 2 |
| `PerGreenTrucksImEU` | 0 | 1.0 | 1.0 | 14/228 | Phase 2 |
| `DocCheckTimeImEU` | 0 | 20 min | 20 min | 3/228 | Phase 2 |
| `PerPhyChkImEU` | 0 | 0.1 | 0.1 | 3/228 | Phase 2 |
| `PhyCheckTimeImEU` | 0 | 730 min | 60 min | 4/228 | Phase 2 |
| `PerSecurityChkEU` | 0 | 0.1 | 0.1 | 3/228 | Phase 2 |
| `SecCheckTimeEU` | 0 | 20 min | 20 min | 3/228 | Phase 2 |

### Section 3 — Landbridge Transit Checks

| Parameter | Min | Max | Typical | Non-zero | Description |
|---|---|---|---|---|---|
| `TransitCheckTimeLB` | 0 | 387 min | 188 min | 203/228 | Transit check time for Landbridge trucks at GB ports |
| `PerPhyChkLB` | 0 | 1.0 | 1.0 | 195/228 | Fraction of Landbridge trucks selected for physical check at GB |
| `PhyCheckTimeLB` | 0 | 844 min | 508 min | 201/228 | Physical check time for Landbridge trucks |
| `PerSecurityChkLB` | 0 | 1.0 | 1.0 | 188/228 | Fraction of Landbridge trucks selected for security check |
| `SecCheckTimeLB` | 0 | 926 min | 508 min | 201/228 | Security check time for Landbridge trucks |

### Section 4 — Resource Capacity

| Parameter | Min | Max | Typical | Non-zero | Description |
|---|---|---|---|---|---|
| `NumCustomShedD` | 0 | 81 | 30 | 150/228 | Customs officers/sheds at Dublin |
| `NumDAFMInspBayD` | 0 | 45 | 27 | 150/228 | DAFM (food safety) inspection bays at Dublin |
| `NumSecurityPostD` | 0 | 50 | 19 | 150/228 | Security posts at Dublin |
| `NumTractorD` | 0 | 87 | 49 | 150/228 | Tractors for unaccompanied trailers at Dublin |
| `NumCustomShedR` | 0 | 84 | 35 | 151/228 | Customs officers at Rosslare |
| `NumDAFMInspBayR` | 0 | 48 | 27 | 151/228 | DAFM bays at Rosslare |
| `NumSecurityPostR` | 0 | 39 | 17 | 152/228 | Security posts at Rosslare |
| `NumTractorR` | 0 | 91 | 52 | 151/228 | Tractors at Rosslare |
| `NumCustomShedGB-W` | 0 | 43 | 14 | 143/228 | Shared customs at GB-West ports |
| `NumDAFMInspBayGB-W` | 0 | 42 | 27 | 142/228 | Shared DAFM at GB-West |
| `NumSecurityPostGB-W` | 0 | 43 | 16 | 142/228 | Shared security at GB-West |
| `NumTractorGB-W` | 0 | 90 | 44 | 149/228 | Shared tractors at GB-West |
| `NumCustomShedHoly` | 0 | 43 | 16 | 141/228 | Customs at Holyhead specifically |
| `NumDAFMInspBayHoly` | 0 | 43 | 24 | 137/228 | DAFM at Holyhead |
| `NumSecurityPostHoly` | 0 | 41 | 15 | 137/228 | Security at Holyhead |
| `NumTractorHoly` | 0 | 88 | 50 | 137/228 | Tractors at Holyhead |
| `NumCustomShedLiv` | 0 | 44 | 14 | 122/228 | Customs at Liverpool |
| `NumDAFMInspBayLiv` | 0 | 40 | 28 | 122/228 | DAFM at Liverpool |
| `NumSecurityPostLiv` | 0 | 46 | 16 | 122/228 | Security at Liverpool |
| `NumTractorLiv` | 0 | 88 | 48 | 122/228 | Tractors at Liverpool |
| `NumCustomShedDov` | 0 | 43 | 15 | 135/228 | Customs at Dover (used for Landbridge) |
| `NumDAFMInspBayDov` | 0 | 39 | 27 | 135/228 | DAFM at Dover |
| `NumSecurityPostDov` | 0 | 45 | 16 | 135/228 | Security at Dover |
| `NumTractorDov` | 0 | 82 | 48 | 128/228 | Tractors at Dover |
| `NumCustomShedEU` | 0 | 60 | 10 | 13/228 | Customs at EU port (Phase 2) |
| `NumDAFMInspBayEU` | 0 | 33 | 10 | 13/228 | DAFM at EU port (Phase 2) |
| `NumSecurityPostEU` | 0 | 30 | 10 | 13/228 | Security at EU port (Phase 2) |
| `NumTractorEU` | 0 | 30 | 30 | 13/228 | Tractors at EU port (Phase 2) |

### Section 5 — Vessel Capacities & Port Routing Splits

| Parameter | Min | Max | Typical | Non-zero | Description |
|---|---|---|---|---|---|
| `PerUKTrucksMoveD` | 0 | 1.0 | 1.0 | 87/228 | Fraction of IRE→GB trucks departing from Dublin (vs Rosslare). Default: 0.85 |
| `PerLBTrucksMoveD` | 0 | 1.0 | 1.0 | 86/228 | Fraction of Landbridge trucks from Dublin |
| `DToHeyVesselCap` | 0 | 500 | 195 | 90/228 | Avg vessel capacity Dublin→Heysham (trailers). AnyLogic default: 122 |
| `DToLivVesselCap` | 0 | 406 | 293 | 90/228 | Avg vessel capacity Dublin→Liverpool. AnyLogic default: 123 |
| `DToHolyVesselCap` | 0 | 445 | 219 | 90/228 | Avg vessel capacity Dublin→Holyhead. AnyLogic default: 209 |
| `RToFishVesselCap` | 0 | 430 | 250 | 90/228 | Avg vessel capacity Rosslare→Fishguard. AnyLogic default: 75 |
| `RToPemVesselCap` | 0 | 449 | 168 | 89/228 | Avg vessel capacity Rosslare→Pembroke. AnyLogic default: 122 |
| `PerProductMoveHey` | 0 | 1.0 | 0.03 | 183/228 | Fraction inbound trucks arriving via Heysham. Default: 0.03 |
| `PerProductMoveLiv` | 0 | 1.0 | 1.0 | 179/228 | Fraction inbound trucks via Liverpool. Default: 0.40 |
| `PerProductMoveHoly` | 0 | 1.0 | 1.0 | 181/228 | Fraction inbound trucks via Holyhead. Default: 0.47 |
| `PerProductMoveFish` | 0 | 1.0 | 1.0 | 183/228 | Fraction inbound trucks via Fishguard. Default: 0.04 |
| `PerProductMovePem` | 0 | 1.0 | 1.0 | 183/228 | Fraction inbound trucks via Pembroke. Default: 0.06 |
| `PerLBTrucksMoveToHey` | 0 | 1.0 | 1.0 | 105/228 | Fraction LB trucks routed via Heysham |
| `PerLBTrucksMoveToLiv` | 0 | 1.0 | 1.0 | 179/228 | Fraction LB trucks routed via Liverpool |
| `PerLBTrucksMoveToHoly` | 0 | 1.0 | 1.0 | 116/228 | Fraction LB trucks routed via Holyhead |
| `PerLBTrucksMoveToFish` | 0 | 1.0 | 1.0 | 184/228 | Fraction LB trucks routed via Fishguard |
| `PerLBTrucksMoveToPem` | 0 | 1.0 | 1.0 | 184/228 | Fraction LB trucks routed via Pembroke |
| `DToCheVesselCap` | 0 | 170 | 170 | 11/228 | Vessel capacity Dublin→Cherbourg (Phase 2). Default: 170 |
| `DToRottVesselCap` | 0 | 530 | 530 | 11/228 | Vessel capacity Dublin→Rotterdam (Phase 2). Default: 530 |
| `DToZeeVesselCap` | 0 | 530 | 530 | 12/228 | Vessel capacity Dublin→Zeebrugge (Phase 2). Default: 530 |
| `RToCheVesselCap` | 0 | 150 | 150 | 11/228 | Vessel capacity Rosslare→Cherbourg (Phase 2). Default: 150 |
| `RToBilVesselCap` | 0 | 80 | 80 | 11/228 | Vessel capacity Rosslare→Bilbao (Phase 2). Default: 80 |

### Sections 6–8 — Shelf Life, Truck Type, Check Costs

| Parameter | Min | Max | Typical | Non-zero | Description |
|---|---|---|---|---|---|
| `AvgShelflife(ProdCat)` | 0 | 48 days | 14 days | 227/228 | Average shelf life of modelled product category in days |
| `UnAccTrucks(%)` | 0 | 1.0 | 1.0 | 227/228 | Fraction of unaccompanied trucks (trailer only, no cab). Default: 0.5 |
| `DocCheckCost` | 50 | 4,344 EUR | 2,227 EUR | 228/228 | Official cost per truck, documentary check |
| `PhyCheckCost` | 500 | 9,754 EUR | 4,297 EUR | 228/228 | Official cost per truck, physical inspection |
| `SecurityCheckCost` | 500 | 10,000 EUR | 5,234 EUR | 228/228 | Official cost per truck, security check |

---

## 11. Raw Output Parameters — Complete Reference

### Phase 1 Outputs (101 targets — trainable now)

> `cov` = percentage of 228 runs where this output was non-zero.

#### Transportation Time (hours)

| Output key (exact string) | cov | Description |
|---|---|---|
| `Transportation time all P exportto GB` | 20% | Avg transit hours, all products, IRE→GB |
| `Transportation time all P import from GB` | 29% | Avg transit hours, all products, GB→IRE |
| `Transportation time agri exportto GB` | 14% | Avg transit hours, agri, IRE→GB |
| `Transportation time agri import from GB` | 23% | Avg transit hours, agri, GB→IRE |
| `Transportation time cat exportto GB` | 21% | Avg transit hours, product category, IRE→GB |
| `Transportation time cat import from GB` | 22% | Avg transit hours, product category, GB→IRE |

#### Remaining Shelf Life (fraction 0.0–1.0)

| Output key | cov | Description |
|---|---|---|
| `Remaining shelflife cat exportto GB` | 100% | Shelf life fraction remaining on export to GB |
| `Remaining shelflife cat import from GB` | 100% | Shelf life fraction remaining on import from GB |

#### Waiting Time at Dublin Port (hours)

| Output key | cov | Description |
|---|---|---|
| `AP cus int WT on ex at D` | 2% | All-products customs wait on export at Dublin |
| `AP avg WT on im at D` | 17% | All-products avg wait on import at Dublin |
| `AP doc chk WT on im at D` | 1% | All-products documentary check wait at Dublin |
| `AP phy chk WT on im at D` | 1% | All-products physical check wait at Dublin |
| `AP sec chk WT on im at D` | 17% | All-products security check wait at Dublin |
| `Agri cus int WT on ex at D` | 0% | Agri customs wait on export at Dublin |
| `Agri avg WT on im at D` | 15% | Agri avg wait on import at Dublin |
| `Agri doc chk WT on im at D` | 15% | Agri documentary check wait at Dublin |
| `Agri phy chk WT on im at D` | 15% | Agri physical (SPS) check wait at Dublin |
| `Agri sec chk WT on im at D` | 11% | Agri security check wait at Dublin |
| `Cat cus int WT on ex at D` | 0% | Category customs wait on export at Dublin |
| `Cat avg WT on im at D` | 14% | Category avg wait on import at Dublin |
| `Cat doc chk WT on im at D` | 14% | Category documentary check wait at Dublin |
| `Cat phy chk WT on im at D` | 14% | Category physical check wait at Dublin |
| `Cat sec chk WT on im at D` | 11% | Category security check wait at Dublin |

#### Waiting Time at Rosslare Port (hours)

| Output key | cov | Description |
|---|---|---|
| `AP avg WT on ex at R` | 1% | All-products wait on export at Rosslare |
| `AP avg WT on im at R` | 11% | All-products avg wait on import at Rosslare |
| `AP doc chk WT on im at R` | 1% | All-products documentary check wait at Rosslare |
| `AP phy chk WT on im at R` | 1% | All-products physical check wait at Rosslare |
| `AP sec chk WT on im at R` | 11% | All-products security check wait at Rosslare |
| `Agri avg WT on ex at R` | 0% | Agri wait on export at Rosslare |
| `Agri avg WT on im at R` | 6% | Agri avg wait on import at Rosslare |
| `Agri doc chk WT on im at R` | 6% | Agri documentary check wait at Rosslare |
| `Agri phy chk WT on im at R` | 5% | Agri physical check wait at Rosslare |
| `Agri sec chk WT on im at R` | 6% | Agri security check wait at Rosslare |
| `Cat avg WT on ex at R` | 0% | Category wait on export at Rosslare |
| `Cat avg WT on im at R` | 10% | Category avg wait on import at Rosslare |
| `Cat doc chk WT on im at R` | 10% | Category documentary check wait at Rosslare |
| `Cat phy chk WT on im at R` | 9% | Category physical check wait at Rosslare |
| `Cat sec chk WT on im at R` | 9% | Category security check wait at Rosslare |

#### Waiting Time at GB-West Ports (hours)

| Output key | cov | Description |
|---|---|---|
| `AP avg waiting time on ex at fish` | 2% | All-products wait on export at Fishguard |
| `AP avg waiting time on im at fish` | 4% | All-products wait on import at Fishguard |
| `Agri avg waiting time on ex at fish` | 0% | Agri wait on export at Fishguard |
| `Agri avg waiting time on im at fish` | 2% | Agri wait on import at Fishguard |
| `Cat avg waiting time on ex at fish` | 2% | Category wait on export at Fishguard |
| `Cat avg waiting time on im at fish` | 3% | Category wait on import at Fishguard |
| `AP avg waiting time on ex at hey` | 2% | All-products wait on export at Heysham |
| `AP avg waiting time on im at hey` | 12% | All-products wait on import at Heysham |
| `Agri avg waiting time on ex at hey` | 0% | Agri wait on export at Heysham |
| `Agri avg waiting time on im at hey` | 8% | Agri wait on import at Heysham |
| `Cat avg waiting time on ex at hey` | 1% | Category wait on export at Heysham |
| `Cat avg waiting time on im at hey` | 18% | Category wait on import at Heysham |
| `AP avg waiting time on ex at holy` | 1% | All-products wait on export at Holyhead |
| `AP avg waiting time on im at holy` | 13% | All-products wait on import at Holyhead |
| `Agri avg waiting time on ex at holy` | 0% | Agri wait on export at Holyhead |
| `Agri avg waiting time on im at holy` | 8% | Agri wait on import at Holyhead |
| `Cat avg waiting time on ex at holy` | 1% | Category wait on export at Holyhead |
| `Cat avg waiting time on im at holy` | 19% | Category wait on import at Holyhead |
| `AP avg waiting time on ex at liv` | 1% | All-products wait on export at Liverpool |
| `AP avg waiting time on im at liv` | 13% | All-products wait on import at Liverpool |
| `Agri avg waiting time on ex at liv` | 0% | Agri wait on export at Liverpool |
| `Agri avg waiting time on im at liv` | 8% | Agri wait on import at Liverpool |
| `Cat avg waiting time on ex at liv` | 1% | Category wait on export at Liverpool |
| `Cat avg waiting time on im at liv` | 18% | Category wait on import at Liverpool |
| `AP avg waiting time on ex at pem` | 2% | All-products wait on export at Pembroke |
| `AP avg waiting time on im at pem` | 2% | All-products wait on import at Pembroke |
| `Agri avg waiting time on ex at pem` | 1% | Agri wait on export at Pembroke |
| `Agri avg waiting time on im at pem` | 1% | Agri wait on import at Pembroke |
| `Cat avg waiting time on ex at pem` | 2% | Category wait on export at Pembroke |
| `Cat avg waiting time on im at pem` | 1% | Category wait on import at Pembroke |

#### Resource Utilisation (fraction 0.0–1.0, values > 0.8 indicate bottleneck)

| Output key | cov | Description |
|---|---|---|
| `D custom shed utilisation` | 4% | Customs shed utilisation at Dublin |
| `DDAFM insp bay utilisation` | 25% | DAFM inspection bay utilisation at Dublin |
| `D security post utilisation` | 32% | Security post utilisation at Dublin |
| `D tractor utilisation` | 58% | Tractor utilisation at Dublin (unaccompanied trailer handling) |
| `R custom shed utilisation` | 4% | Customs utilisation at Rosslare |
| `RDAFM insp bay utilisation` | 12% | DAFM utilisation at Rosslare |
| `R security post utilisation` | 17% | Security utilisation at Rosslare |
| `R tractor utilisation` | 25% | Tractor utilisation at Rosslare |
| `Fish custom shed utilisation` | 6% | Customs utilisation at Fishguard |
| `Fish DAFM insp bay utilisation` | 3% | DAFM utilisation at Fishguard |
| `Fish security post utilisation` | 4% | Security utilisation at Fishguard |
| `Hey custom shed utilisation` | 9% | Customs utilisation at Heysham |
| `Hey DAFM insp bay utilisation` | 18% | DAFM utilisation at Heysham |
| `Hey security post utilisation` | 19% | Security utilisation at Heysham |
| `Holy custom shed utilisation` | 7% | Customs utilisation at Holyhead |
| `Holy DAFM insp bay utilisation` | 19% | DAFM utilisation at Holyhead |
| `Holy security post utilisation` | 20% | Security utilisation at Holyhead |
| `Liv custom shed utilisation` | 7% | Customs utilisation at Liverpool |
| `Liv DAFM insp bay utilisation` | 18% | DAFM utilisation at Liverpool |
| `Liv security post utilisation` | 19% | Security utilisation at Liverpool |
| `Pem custom shed utilisation` | 6% | Customs utilisation at Pembroke |
| `Pem DAFM insp bay utilisation` | 3% | DAFM utilisation at Pembroke |
| `Pem security post utilisation` | 3% | Security utilisation at Pembroke |

#### Queue Lengths (trucks)

| Output key | cov | Description |
|---|---|---|
| `Trucks vessel queue length D to UK` | 28% | Queue at Dublin for GB-bound vessels |
| `Trucks vessel queue length R to UK` | 11% | Queue at Rosslare for GB-bound vessels |
| `Trucks vessel queue length hey to D` | 43% | Queue at Heysham for Dublin-bound vessels |
| `Trucks vessel queue length liv to D` | 34% | Queue at Liverpool for Dublin-bound vessels |
| `Trucks vessel queue length holy to D` | 39% | Queue at Holyhead for Dublin-bound vessels |
| `Trucks vessel queue length fish to R` | 43% | Queue at Fishguard for Rosslare-bound vessels |
| `Trucks vessel queue length pem to R` | 45% | Queue at Pembroke for Rosslare-bound vessels |

#### Border Checking Costs (EUR total across simulation period)

| Output key | cov | Description |
|---|---|---|
| `Total doc check cost ex trucks from IR to GBW` | 27% | Documentary check costs for IRE export trucks at GB-West |
| `Total phy check cost ex trucks from IR to GBW` | 27% | Physical check costs for IRE export trucks at GB-West |
| `Total sec check cost ex trucks from IR to GBW` | 27% | Security check costs for IRE export trucks at GB-West |

### Phase 2 Outputs (35 targets — not_trained until Phase 2 data generated)

| Output key | cov | Description |
|---|---|---|
| `Transportation time exportto EULB` | 5% | IRE→EU via Landbridge (hours) |
| `Transportation time import from EULB` | 5% | EU→IRE via Landbridge (hours) |
| `Remaining shelflife cat exportto EULB` | 100% | Shelf life on LB export |
| `Remaining shelflife cat import from EULB` | 100% | Shelf life on LB import |
| `Transportation time exportto EU che` | 5% | IRE→EU via Cherbourg |
| `Transportation time import from EU che` | 5% | EU→IRE via Cherbourg |
| `Remaining shelflife cat exportto EU che` | 100% | Shelf life on Cherbourg export |
| `Remaining shelflife cat import from EU che` | 100% | Shelf life on Cherbourg import |
| `Transportation time exportto EU ro ze` | 5% | IRE→EU via Rotterdam/Zeebrugge |
| `Transportation time import from EU ro ze` | 5% | EU→IRE via Rotterdam/Zeebrugge |
| `Remaining shelflife cat exportto EU ro ze` | 100% | Shelf life on Rotterdam/Zeebrugge export |
| `Remaining shelflife cat import from EU ro ze` | 100% | Shelf life on Rotterdam/Zeebrugge import |
| `Transportation time exportto EU bil` | 0% | IRE→EU via Bilbao |
| `Transportation time import from EU bil` | 1% | EU→IRE via Bilbao |
| `Remaining shelflife cat exportto EU bil` | 100% | Shelf life on Bilbao export |
| `Remaining shelflife cat import from EU bil` | 100% | Shelf life on Bilbao import |
| `Avg waiting time on ex at dov` | 0% | Wait on export at Dover |
| `Avg waiting time on im at dov` | 1% | Wait on import at Dover |
| `Avg waiting time on ex at cal` | 0% | Wait on export at Calais |
| `Avg waiting time on im at cal` | 1% | Wait on import at Calais |
| `Trucks vessel queue length D to che` | 5% | Queue Dublin→Cherbourg |
| `Trucks vessel queue length D to rott` | 5% | Queue Dublin→Rotterdam |
| `Trucks vessel queue length D to zee` | 5% | Queue Dublin→Zeebrugge |
| `Trucks vessel queue length R to che` | 5% | Queue Rosslare→Cherbourg |
| `Trucks vessel queue length R to bil` | 0% | Queue Rosslare→Bilbao |
| `Trucks vessel queue length che to IR` | 5% | Queue Cherbourg→IRE |
| `Trucks vessel queue length rott to D` | 5% | Queue Rotterdam→Dublin |
| `Trucks vessel queue length zee to D` | 0% | Queue Zeebrugge→Dublin |
| `Trucks vessel queue length bil to R` | 1% | Queue Bilbao→Rosslare |
| `Total doc check cost im trucks to D` | 30% | Documentary check costs, inbound to Dublin |
| `Total phy check cost im trucks to D` | 25% | Physical check costs, inbound to Dublin |
| `Total sec check cost im trucks to D` | 32% | Security check costs, inbound to Dublin |
| `Total doc check cost im trucks to R` | 18% | Documentary check costs, inbound to Rosslare |
| `Total phy check cost im trucks to R` | 12% | Physical check costs, inbound to Rosslare |
| `Total sec check cost im trucks to R` | 17% | Security check costs, inbound to Rosslare |

---

## 12. Semantic API Layer

### 12.1 Design Pattern

The Semantic API is a **Facade** over the Raw ML API. It presents a domain-friendly interface where the user thinks in logistics terms (supplier region, port, commodity) rather than AnyLogic parameter names.

The key architectural rule: **the user must never see an AnyLogic column name**. The Param Translator (Section 15) is the only code that knows both representations simultaneously.

### 12.2 Endpoints

```
POST /scenario/predict      → runs full prediction for a semantic scenario
POST /scenario/validate     → validates selections without running prediction
GET  /scenario/options      → returns all valid dropdown values
GET  /scenario/schema       → returns step-by-step field definitions for wizard UI
```

### 12.3 The 7 Semantic Dimensions

A complete scenario is described by exactly 7 dimensions. Each maps to 1–20 raw parameters.

| Dimension | Semantic field(s) | Raw params affected |
|---|---|---|
| 1. Journey | `supplier_region`, `origin_port`, `destination_region`, `destination_port`, `direction` | Vol* fields, routing splits |
| 2. Commodity | `commodity_type` | Which Vol* and output filter used |
| 3. Volume | `product_volume_tonnes` | Populates the appropriate Vol* field |
| 4. Route | `route_type`, `destination_port` | Port routing split params, vessel cap |
| 5. Check regime | `check_regime` (+ optional overrides) | All Per*/Time* check params |
| 6. Resources | `customs_officers`, `dafm_officers`, `security_officers`, `tractors` | Num* params at relevant port |
| 7. Product | `shelf_life_days`, `unaccompanied_pct`, `doc_check_cost_eur`, `phy_check_cost_eur`, `sec_check_cost_eur` | AvgShelflife, UnAccTrucks, costs |

---

## 13. Semantic Input Fields — Complete Reference

### Full request schema

```python
class ScenarioRequest(BaseModel):

    # ── DIMENSION 1 & 2: Journey + Commodity ──────────────────────────────
    supplier_region: Literal["ireland", "great_britain", "eu"]
    origin_port: Literal["dublin", "rosslare"]
    destination_region: Literal["great_britain", "eu"]
    destination_port: Literal[
        "liverpool", "holyhead", "heysham",  # GB-West (Phase 1)
        "fishguard", "pembroke",              # GB-West via Rosslare (Phase 1)
        "cherbourg", "rotterdam",             # EU direct (Phase 2)
        "zeebrugge", "bilbao"                 # EU direct (Phase 2)
    ]
    commodity_type: Literal["all_products", "agri", "category"]
    direction: Literal["export", "import"]
    # direction = export means: origin_port → destination_port (IRE sending goods)
    # direction = import means: destination_port → origin_port (IRE receiving goods)

    # ── DIMENSION 3: Volume ───────────────────────────────────────────────
    product_volume_tonnes: float
    # This is the ONLY volume the user provides.
    # Translator maps it to the correct Vol* field based on
    # (commodity_type, direction, route_type).

    # ── DIMENSION 4: Route ────────────────────────────────────────────────
    route_type: Literal[
        "direct_gb",         # East/West corridor: Dublin/Rosslare → GB ports (Phase 1)
        "landbridge",        # IRE → GB → EU via Dover/Calais (Phase 2)
        "direct_cherbourg",  # IRE → Cherbourg direct (Phase 2)
        "direct_rotterdam",  # IRE → Rotterdam direct (Phase 2)
        "direct_zeebrugge",  # IRE → Zeebrugge direct (Phase 2)
        "direct_bilbao",     # IRE → Bilbao direct (Phase 2)
    ]
    vessel_capacity_trailers: Optional[int] = None
    # If None, filled from PORT_DEFAULTS[destination_port]["vessel_cap"]

    # ── DIMENSION 5: Check Regime ─────────────────────────────────────────
    check_regime: Literal["none", "light", "standard", "hard"]
    # See Section 16 for exact param mappings per regime.
    # Optional overrides — if provided, replace regime defaults:
    physical_check_pct: Optional[float] = None      # 0.0–1.0
    physical_check_time_mins: Optional[int] = None  # minutes
    doc_check_time_mins: Optional[int] = None        # minutes
    security_check_pct: Optional[float] = None       # 0.0–1.0
    security_check_time_mins: Optional[int] = None   # minutes

    # ── DIMENSION 6: Resources ────────────────────────────────────────────
    # Applied to the ORIGIN port (for export) or DESTINATION port (for import)
    customs_officers: Optional[int] = None   # default: 10
    dafm_officers: Optional[int] = None      # default: 10
    security_officers: Optional[int] = None  # default: 10
    tractors: Optional[int] = None           # default: 20

    # ── DIMENSION 7: Product & Costs ─────────────────────────────────────
    shelf_life_days: Optional[float] = None          # default: 14
    unaccompanied_pct: Optional[float] = None        # 0.0–1.0, default: 0.5
    doc_check_cost_eur: Optional[float] = None       # default: 50.0
    phy_check_cost_eur: Optional[float] = None       # default: 500.0
    sec_check_cost_eur: Optional[float] = None       # default: 500.0
```

### Valid enum values for UI dropdowns

```python
VALID_OPTIONS = {
    "supplier_region": ["ireland", "great_britain", "eu"],
    "origin_port": {
        "ireland": ["dublin", "rosslare"],
        "great_britain": ["liverpool", "holyhead", "heysham", "fishguard", "pembroke"],
        "eu": ["cherbourg", "rotterdam", "zeebrugge", "bilbao"],
    },
    "destination_region": ["great_britain", "eu"],
    "destination_port": {
        "great_britain": ["liverpool", "holyhead", "heysham", "fishguard", "pembroke"],
        "eu": ["cherbourg", "rotterdam", "zeebrugge", "bilbao"],
    },
    "commodity_type": ["all_products", "agri", "category"],
    "direction": ["export", "import"],
    "route_type": {
        "great_britain": ["direct_gb"],                                        # Phase 1
        "eu": ["landbridge", "direct_cherbourg", "direct_rotterdam",           # Phase 2
               "direct_zeebrugge", "direct_bilbao"],
    },
    "check_regime": ["none", "light", "standard", "hard"],
}
```

---

## 14. Semantic Output Response Schema

```python
class PredictionResult(BaseModel):
    value: Optional[float]      # null if not_trained
    unit: str
    status: Literal["ok", "low_coverage", "zero_predicted", "not_trained"]
    phase: Literal[1, 2]
    coverage_pct: int           # % of training runs with non-zero value
    r2: Optional[float]         # CV R² score, null if not_trained

class ScenarioResponse(BaseModel):
    scenario_id: str            # deterministic hash of inputs, e.g. "ire_dub_agri_export_liverpool_standard"
    corridor: str               # "Ireland → Great Britain (Dublin → Liverpool)"
    commodity: str              # "agri"
    direction: str              # "export" | "import"
    check_regime: str           # "standard"
    model_version: str          # "v1"

    results: dict[str, dict]    # grouped by category, see below

    warnings: list[str]         # e.g. ["shelf_life margin < 5%", "DAFM utilisation > 80%"]
    overall_confidence: Literal["high", "medium", "low"]
    # high   = all returned outputs have status "ok" (coverage >= 15%)
    # medium = some outputs have status "low_coverage"
    # low    = majority have low_coverage or zero_predicted

# Example results structure:
{
  "transit": {
    "Transportation time agri import from GB": {
      "value": 16.9, "unit": "hours",
      "status": "ok", "phase": 1, "coverage_pct": 23, "r2": 0.87
    }
  },
  "border_delay": {
    "Agri avg WT on im at D": {
      "value": 0.31, "unit": "hours",
      "status": "ok", "phase": 1, "coverage_pct": 15, "r2": 0.79
    },
    "Agri phy chk WT on im at D": {
      "value": 0.12, "unit": "hours",
      "status": "low_coverage", "phase": 1, "coverage_pct": 15, "r2": 0.72
    }
  },
  "shelf_life": {
    "Remaining shelflife cat import from GB": {
      "value": 0.967, "unit": "fraction",
      "status": "ok", "phase": 1, "coverage_pct": 100, "r2": 0.96
    }
  },
  "resource_utilisation": {
    "DDAFM insp bay utilisation": {
      "value": 0.61, "unit": "fraction",
      "status": "ok", "phase": 1, "coverage_pct": 25, "r2": 0.83
    }
  },
  "vessel_queues": {
    "Trucks vessel queue length liv to D": {
      "value": 25.3, "unit": "trucks",
      "status": "ok", "phase": 1, "coverage_pct": 34, "r2": 0.88
    }
  },
  "costs": {
    "Total doc check cost ex trucks from IR to GBW": {
      "value": 1067150.0, "unit": "EUR",
      "status": "ok", "phase": 1, "coverage_pct": 27, "r2": 0.91
    }
  }
}
```

---

## 15. Param Translator — Complete Mapping Logic

File: `src/param_translator.py`

The translator converts a `ScenarioRequest` into a complete 153-element dict of raw parameters. All unlisted params are filled with training medians from `registry.json`.

```python
def translate(req: ScenarioRequest, medians: dict) -> dict:
    """
    Returns a dict with ALL 153 raw parameter names as keys.
    Starts from medians dict (all params at training median).
    Overrides specific params based on scenario selections.
    """
    params = dict(medians)  # start with all medians

    # ── STEP 1: Set all Vol* to 0 (clean slate for volume routing) ────────
    for k in params:
        if k.startswith("Vol"):
            params[k] = 0.0

    # ── STEP 2: Populate Vol* based on journey + commodity + volume ───────
    vol_key = VOLUME_MAP[(req.commodity_type, req.direction, req.route_type)]
    params[vol_key] = req.product_volume_tonnes

    # ── STEP 3: Apply port routing splits ────────────────────────────────
    port_defaults = PORT_ROUTING[req.destination_port]
    for k, v in port_defaults.items():
        params[k] = v
    # Zero out all other port splits (only one destination port active)
    for port_param in ALL_PORT_SPLIT_PARAMS:
        if port_param not in port_defaults:
            params[port_param] = 0.0

    # ── STEP 4: Apply vessel capacity ─────────────────────────────────────
    vessel_cap_key = VESSEL_CAP_MAP[req.origin_port][req.destination_port]
    params[vessel_cap_key] = req.vessel_capacity_trailers or PORT_ROUTING[req.destination_port]["vessel_cap"]

    # ── STEP 5: Apply check regime ────────────────────────────────────────
    regime_params = CHECK_REGIME_PRESETS[req.check_regime][req.commodity_type]
    params.update(regime_params)
    # Apply optional overrides
    if req.physical_check_pct is not None:
        params[PHYCHK_PCT_MAP[req.commodity_type]] = req.physical_check_pct
    if req.physical_check_time_mins is not None:
        params[PHYCHK_TIME_MAP[req.commodity_type]] = req.physical_check_time_mins
    if req.doc_check_time_mins is not None:
        params[DOCCHK_TIME_MAP[req.commodity_type]] = req.doc_check_time_mins

    # ── STEP 6: Apply resource capacity ───────────────────────────────────
    port_for_resources = req.origin_port if req.direction == "export" else _infer_ire_port(req)
    resource_map = RESOURCE_PARAM_MAP[port_for_resources]
    if req.customs_officers: params[resource_map["customs"]] = req.customs_officers
    if req.dafm_officers:    params[resource_map["dafm"]]    = req.dafm_officers
    if req.security_officers:params[resource_map["security"]]= req.security_officers
    if req.tractors:         params[resource_map["tractors"]] = req.tractors

    # ── STEP 7: Shelf life and truck type ─────────────────────────────────
    params["AvgShelflife(ProdCat)"] = req.shelf_life_days or 14.0
    params["UnAccTrucks(%)"]        = req.unaccompanied_pct or 0.5

    # ── STEP 8: Check costs ───────────────────────────────────────────────
    params["DocCheckCost"]      = req.doc_check_cost_eur or 50.0
    params["PhyCheckCost"]      = req.phy_check_cost_eur or 500.0
    params["SecurityCheckCost"] = req.sec_check_cost_eur or 500.0

    return params


# ── VOLUME MAP ───────────────────────────────────────────────────────────────
# (commodity_type, direction, route_type) → raw Vol* column name

VOLUME_MAP = {
    ("all_products", "import", "direct_gb"):        "VolAllPImGB",
    ("all_products", "export", "direct_gb"):        "VolAllPExGB",
    ("agri",         "import", "direct_gb"):        "VolAgriImGB",
    ("agri",         "export", "direct_gb"):        "VolAgriExGB",
    ("category",     "import", "direct_gb"):        "VolCatImGB",
    ("category",     "export", "direct_gb"):        "VolCatExGB",
    ("all_products", "import", "landbridge"):       "VolAllPImEULB",
    ("all_products", "export", "landbridge"):       "VolAllPExEULB",
    ("agri",         "import", "landbridge"):       "VolAgriImEULB",
    ("agri",         "export", "landbridge"):       "VolAgriExEULB",
    ("all_products", "import", "direct_cherbourg"): "VolAllPImViaChe",
    ("all_products", "export", "direct_cherbourg"): "VolAllPExViaChe",
    ("agri",         "import", "direct_cherbourg"): "VolAgriImViaChe",
    ("agri",         "export", "direct_cherbourg"): "VolAgriExViaChe",
    ("all_products", "import", "direct_rotterdam"): "VolAllPImViaRott",
    ("all_products", "export", "direct_rotterdam"): "VolAllPExViaRott",
    ("agri",         "import", "direct_rotterdam"): "VolAgriImViaRott",
    ("agri",         "export", "direct_rotterdam"): "VolAgriExViaRott",
    ("all_products", "import", "direct_zeebrugge"): "VolAllPImViaZee",
    ("all_products", "export", "direct_zeebrugge"): "VolAllPExViaZee",
    ("agri",         "import", "direct_zeebrugge"): "VolAgriImViaZee",
    ("agri",         "export", "direct_zeebrugge"): "VolAgriExViaZee",
}


# ── RESOURCE PARAM MAP ───────────────────────────────────────────────────────
RESOURCE_PARAM_MAP = {
    "dublin": {
        "customs":  "NumCustomShedD",
        "dafm":     "NumDAFMInspBayD",
        "security": "NumSecurityPostD",
        "tractors": "NumTractorD",
    },
    "rosslare": {
        "customs":  "NumCustomShedR",
        "dafm":     "NumDAFMInspBayR",
        "security": "NumSecurityPostR",
        "tractors": "NumTractorR",
    },
    "liverpool": {
        "customs":  "NumCustomShedLiv",
        "dafm":     "NumDAFMInspBayLiv",
        "security": "NumSecurityPostLiv",
        "tractors": "NumTractorLiv",
    },
    "holyhead": {
        "customs":  "NumCustomShedHoly",
        "dafm":     "NumDAFMInspBayHoly",
        "security": "NumSecurityPostHoly",
        "tractors": "NumTractorHoly",
    },
    "heysham": {
        "customs":  "NumCustomShedGB-W",
        "dafm":     "NumDAFMInspBayGB-W",
        "security": "NumSecurityPostGB-W",
        "tractors": "NumTractorGB-W",
    },
    "fishguard": {
        "customs":  "NumCustomShedGB-W",
        "dafm":     "NumDAFMInspBayGB-W",
        "security": "NumSecurityPostGB-W",
        "tractors": "NumTractorGB-W",
    },
    "pembroke": {
        "customs":  "NumCustomShedGB-W",
        "dafm":     "NumDAFMInspBayGB-W",
        "security": "NumSecurityPostGB-W",
        "tractors": "NumTractorGB-W",
    },
}


# ── VESSEL CAP MAP ───────────────────────────────────────────────────────────
# (origin_port, destination_port) → raw vessel cap param name

VESSEL_CAP_MAP = {
    "dublin": {
        "heysham":    "DToHeyVesselCap",
        "liverpool":  "DToLivVesselCap",
        "holyhead":   "DToHolyVesselCap",
        "cherbourg":  "DToCheVesselCap",
        "rotterdam":  "DToRottVesselCap",
        "zeebrugge":  "DToZeeVesselCap",
    },
    "rosslare": {
        "fishguard":  "RToFishVesselCap",
        "pembroke":   "RToPemVesselCap",
        "cherbourg":  "RToCheVesselCap",
        "bilbao":     "RToBilVesselCap",
    },
}
```

---

## 16. Check Regime Presets

These presets encode the Brexit scenario logic. When a user selects `check_regime: "hard"`, all 12+ check-related raw parameters are set appropriately without the user knowing any of them exist.

Presets are defined per commodity type because SPS checks apply specifically to agri products.

```python
CHECK_REGIME_PRESETS = {

    "none": {
        # Pre-Brexit: all trucks green route, no checks
        "all_products": {
            "PerGreenTrucksAPImIR": 1.0,
            "DocChkTimeAPImIR": 0,
            "PerPhyChkAPImIR": 0.0,
            "PhyChkTimeAPImIR": 0,
            "PerSecurityChkAPIR": 0.0,
            "SecChkTimeAPImIR": 0,
            "PerCusIntTrucksAPExIR": 0.0,
            "CusIntTimeAPExIR": 0,
            "PerGreenTrucksAPImGB-W": 1.0,
            "DocChkTimeAPImGB-W": 0,
            "PerPhyChkAPImGB-W": 0.0,
            "PhyChkTimeAPImGB-W": 0,
        },
        "agri": {
            "PerGreenTrucksAPImIR": 1.0,
            "DocChkTimeAgriImIR": 0,
            "PerPhyChkAgriImIR": 0.0,
            "PhyChkTimeAgriImIR": 0,
            "PerSecurityChkAgriIR": 0.0,
            "SecChkTimeAgriImIR": 0,
            "PerCusIntTrucksAgriExIR": 0.0,
            "CusIntTimeAgriExIR": 0,
        },
        "category": {
            "PerGreenTrucksAPImIR": 1.0,
            "DocChkTimeCatImIR": 0,
            "PerPhyChkCatImIR": 0.0,
            "PhyChkTimeCatImIR": 0,
            "PerSecurityChkCatIR": 0.0,
            "SecChkTimeCatImIR": 0,
            "PerCusIntTrucksCatExIR": 0.0,
            "CusIntTimeCatExIR": 0,
        },
    },

    "light": {
        # Light Brexit: customs export checks only, no import physical checks
        "all_products": {
            "PerCusIntTrucksAPExIR": 1.0,
            "CusIntTimeAPExIR": 266,
            "PerGreenTrucksAPImIR": 1.0,
            "PerPhyChkAPImIR": 0.0,
            "DocChkTimeAPImIR": 0,
            "PerSecurityChkAPIR": 0.0,
            "PerCusIntTrucksAPExGB-W": 1.0,
            "CusIntTimeAPExGB-W": 262,
            "PerGreenTrucksAPImGB-W": 1.0,
            "PerPhyChkAPImGB-W": 0.0,
        },
        "agri": {
            "PerCusIntTrucksAgriExIR": 1.0,
            "CusIntTimeAgriExIR": 201,
            "PerGreenTrucksAPImIR": 1.0,
            "PerPhyChkAgriImIR": 0.0,
            "DocChkTimeAgriImIR": 0,
            "PerSecurityChkAgriIR": 0.0,
            "PerCusIntTrucksAgriExGB-W": 1.0,
            "CusIntTimeAgriExGB-W": 246,
        },
        "category": {
            "PerCusIntTrucksCatExIR": 1.0,
            "CusIntTimeCatExIR": 242,
            "PerGreenTrucksAPImIR": 1.0,
            "PerPhyChkCatImIR": 0.0,
            "DocChkTimeCatImIR": 0,
            "PerSecurityChkCatIR": 0.0,
            "PerCusIntTrucksCatExGB-W": 1.0,
            "CusIntTimeCatExGB-W": 201,
        },
    },

    "standard": {
        # Standard Brexit: 10% physical checks, 20-min documentary
        "all_products": {
            "PerCusIntTrucksAPExIR": 1.0,
            "CusIntTimeAPExIR": 266,
            "PerGreenTrucksAPImIR": 0.9,
            "DocChkTimeAPImIR": 20,
            "PerPhyChkAPImIR": 0.1,
            "PhyChkTimeAPImIR": 60,
            "PerSecurityChkAPIR": 0.05,
            "SecChkTimeAPImIR": 20,
            "PerGreenTrucksAPImGB-W": 0.9,
            "PerPhyChkAPImGB-W": 0.1,
            "PhyChkTimeAPImGB-W": 60,
        },
        "agri": {
            "PerCusIntTrucksAgriExIR": 1.0,
            "CusIntTimeAgriExIR": 201,
            "DocChkTimeAgriImIR": 20,
            "PerPhyChkAgriImIR": 0.1,
            "PhyChkTimeAgriImIR": 60,
            "PerSecurityChkAgriIR": 0.05,
            "SecChkTimeAgriImIR": 20,
        },
        "category": {
            "PerCusIntTrucksCatExIR": 1.0,
            "CusIntTimeCatExIR": 242,
            "DocChkTimeCatImIR": 20,
            "PerPhyChkCatImIR": 0.1,
            "PhyChkTimeCatImIR": 60,
            "PerSecurityChkCatIR": 0.05,
            "SecChkTimeCatImIR": 20,
        },
    },

    "hard": {
        # Hard Brexit: 30% physical SPS checks, long times — based on actual run 7 values
        "all_products": {
            "PerCusIntTrucksAPExIR": 1.0,
            "CusIntTimeAPExIR": 266,
            "PerGreenTrucksAPImIR": 0.7,
            "DocChkTimeAPImIR": 242,
            "PerPhyChkAPImIR": 0.3,
            "PhyChkTimeAPImIR": 385,
            "PerSecurityChkAPIR": 0.1,
            "SecChkTimeAPImIR": 377,
            "PerGreenTrucksAPImGB-W": 0.7,
            "PerPhyChkAPImGB-W": 0.3,
            "PhyChkTimeAPImGB-W": 475,
        },
        "agri": {
            "PerCusIntTrucksAgriExIR": 1.0,
            "CusIntTimeAgriExIR": 201,
            "DocChkTimeAgriImIR": 172,
            "PerPhyChkAgriImIR": 0.3,
            "PhyChkTimeAgriImIR": 385,
            "PerSecurityChkAgriIR": 0.1,
            "SecChkTimeAgriImIR": 426,
        },
        "category": {
            "PerCusIntTrucksCatExIR": 1.0,
            "CusIntTimeCatExIR": 242,
            "DocChkTimeCatImIR": 168,
            "PerPhyChkCatImIR": 0.3,
            "PhyChkTimeCatImIR": 398,
            "PerSecurityChkCatIR": 0.1,
            "SecChkTimeCatImIR": 367,
        },
    },
}
```

---

## 17. Port Routing Resolution

When a user selects `destination_port: "liverpool"`, the translator must:
1. Set `PerProductMoveLiv = 1.0` (100% of trucks use Liverpool)
2. Set all other `PerProductMove*` to 0.0
3. Set `DToLivVesselCap` to the user's vessel capacity (or default)

```python
PORT_ROUTING = {
    # Each entry: {routing_param: fraction, vessel_cap_param: name, vessel_cap_default: int}
    # Also includes routing split params to zero out

    "liverpool": {
        "PerProductMoveLiv":  1.0,
        "PerProductMoveHoly": 0.0,
        "PerProductMoveHey":  0.0,
        "PerProductMoveFish": 0.0,
        "PerProductMovePem":  0.0,
        "vessel_cap_param":   "DToLivVesselCap",
        "vessel_cap":         123,
    },
    "holyhead": {
        "PerProductMoveHoly": 1.0,
        "PerProductMoveLiv":  0.0,
        "PerProductMoveHey":  0.0,
        "PerProductMoveFish": 0.0,
        "PerProductMovePem":  0.0,
        "vessel_cap_param":   "DToHolyVesselCap",
        "vessel_cap":         209,
    },
    "heysham": {
        "PerProductMoveHey":  1.0,
        "PerProductMoveLiv":  0.0,
        "PerProductMoveHoly": 0.0,
        "PerProductMoveFish": 0.0,
        "PerProductMovePem":  0.0,
        "vessel_cap_param":   "DToHeyVesselCap",
        "vessel_cap":         122,
    },
    "fishguard": {
        "PerProductMoveFish": 1.0,
        "PerProductMoveLiv":  0.0,
        "PerProductMoveHoly": 0.0,
        "PerProductMoveHey":  0.0,
        "PerProductMovePem":  0.0,
        "vessel_cap_param":   "RToFishVesselCap",
        "vessel_cap":         75,
    },
    "pembroke": {
        "PerProductMovePem":  1.0,
        "PerProductMoveLiv":  0.0,
        "PerProductMoveHoly": 0.0,
        "PerProductMoveHey":  0.0,
        "PerProductMoveFish": 0.0,
        "vessel_cap_param":   "RToPemVesselCap",
        "vessel_cap":         122,
    },
    "cherbourg": {
        "vessel_cap_param":   "DToCheVesselCap",
        "vessel_cap":         170,
    },
    "rotterdam": {
        "vessel_cap_param":   "DToRottVesselCap",
        "vessel_cap":         530,
    },
    "zeebrugge": {
        "vessel_cap_param":   "DToZeeVesselCap",
        "vessel_cap":         530,
    },
    "bilbao": {
        "vessel_cap_param":   "RToBilVesselCap",
        "vessel_cap":         80,
    },
}
```

---

## 18. Output Filter Map

File: `src/output_filter.py`

The output filter determines which of the 136 raw output keys to include in the semantic response, based on `(commodity_type, direction, route_type, destination_port)`. This prevents returning 136 undifferentiated predictions when only 8–15 are relevant to a scenario.

```python
OUTPUT_FILTER_MAP = {

    ("agri", "import", "direct_gb", "dublin", "liverpool"): [
        "Transportation time agri import from GB",
        "Agri avg WT on im at D",
        "Agri doc chk WT on im at D",
        "Agri phy chk WT on im at D",
        "Agri sec chk WT on im at D",
        "Agri avg waiting time on im at liv",
        "Remaining shelflife cat import from GB",
        "DDAFM insp bay utilisation",
        "D tractor utilisation",
        "D security post utilisation",
        "Trucks vessel queue length liv to D",
        "Liv DAFM insp bay utilisation",
        "Liv security post utilisation",
        "Total doc check cost im trucks to D",
        "Total phy check cost im trucks to D",
        "Total sec check cost im trucks to D",
    ],

    ("agri", "import", "direct_gb", "dublin", "holyhead"): [
        "Transportation time agri import from GB",
        "Agri avg WT on im at D",
        "Agri doc chk WT on im at D",
        "Agri phy chk WT on im at D",
        "Agri sec chk WT on im at D",
        "Agri avg waiting time on im at holy",
        "Remaining shelflife cat import from GB",
        "DDAFM insp bay utilisation",
        "D tractor utilisation",
        "Trucks vessel queue length holy to D",
        "Holy DAFM insp bay utilisation",
        "Holy security post utilisation",
        "Total doc check cost im trucks to D",
        "Total phy check cost im trucks to D",
    ],

    ("agri", "export", "direct_gb", "dublin", "liverpool"): [
        "Transportation time agri exportto GB",
        "Agri cus int WT on ex at D",
        "Remaining shelflife cat exportto GB",
        "D custom shed utilisation",
        "Trucks vessel queue length D to UK",
        "Total doc check cost ex trucks from IR to GBW",
        "Total phy check cost ex trucks from IR to GBW",
        "Total sec check cost ex trucks from IR to GBW",
    ],

    ("all_products", "import", "direct_gb", "dublin", "liverpool"): [
        "Transportation time all P import from GB",
        "AP avg WT on im at D",
        "AP doc chk WT on im at D",
        "AP phy chk WT on im at D",
        "AP sec chk WT on im at D",
        "AP avg waiting time on im at liv",
        "DDAFM insp bay utilisation",
        "D tractor utilisation",
        "D security post utilisation",
        "Trucks vessel queue length liv to D",
        "Liv DAFM insp bay utilisation",
        "Total doc check cost im trucks to D",
        "Total phy check cost im trucks to D",
    ],

    # ... similar entries for all (commodity, direction, port) combinations
}

# Fallback: if exact combination not in map, use commodity-only defaults
OUTPUT_FILTER_FALLBACK = {
    "agri": [
        "Transportation time agri import from GB",
        "Transportation time agri exportto GB",
        "Agri avg WT on im at D",
        "Agri phy chk WT on im at D",
        "Remaining shelflife cat import from GB",
        "DDAFM insp bay utilisation",
        "D tractor utilisation",
        "Trucks vessel queue length D to UK",
    ],
    "all_products": [
        "Transportation time all P import from GB",
        "Transportation time all P exportto GB",
        "AP avg WT on im at D",
        "DDAFM insp bay utilisation",
        "Trucks vessel queue length D to UK",
    ],
    "category": [
        "Transportation time cat import from GB",
        "Transportation time cat exportto GB",
        "Cat avg WT on im at D",
        "Remaining shelflife cat import from GB",
        "DDAFM insp bay utilisation",
    ],
}
```

---

## 19. Phase 1 Scenario Definition

Phase 1 is the complete, shippable system for the **IRE ↔ GB East/West Corridor**. It covers:

### Supported journeys (Phase 1)

| Origin | Origin port | Destination | Destination port | Commodities | Directions |
|---|---|---|---|---|---|
| Ireland | Dublin | Great Britain | Liverpool | all_products, agri, category | export, import |
| Ireland | Dublin | Great Britain | Holyhead | all_products, agri, category | export, import |
| Ireland | Dublin | Great Britain | Heysham | all_products, agri, category | export, import |
| Ireland | Rosslare | Great Britain | Fishguard | all_products, agri, category | export, import |
| Ireland | Rosslare | Great Britain | Pembroke | all_products, agri, category | export, import |

### Supported check regimes (Phase 1)

All four presets are trained: `none`, `light`, `standard`, `hard`

### Phase 1 output coverage

Phase 1 returns predictions for **101 output targets**:
- 6 transportation time outputs (IRE↔GB)
- 2 shelf life outputs (GB corridor)
- 30 Dublin waiting time outputs (all products / agri / category × import/export × check type)
- 15 Rosslare waiting time outputs
- 30 GB-West port waiting time outputs (Fishguard, Heysham, Holyhead, Liverpool, Pembroke)
- 8 Dublin resource utilisation outputs
- 7 GB-West port resource utilisation outputs (Hey, Holy, Liv, Fish, Pem)
- 7 vessel queue length outputs (D to UK, R to UK, hey/holy/liv/fish/pem to D/R)
- 3 border cost outputs (export trucks from IRE to GB-West)

### Phase 1 API example: Ireland → Dublin → Agri → GB → Liverpool → Import → Hard Brexit

```bash
curl -X POST http://localhost:8000/scenario/predict \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_region": "great_britain",
    "origin_port": "liverpool",
    "destination_region": "ireland",
    "destination_port": "dublin",
    "commodity_type": "agri",
    "direction": "import",
    "product_volume_tonnes": 1643898,
    "route_type": "direct_gb",
    "check_regime": "hard",
    "customs_officers": 10,
    "dafm_officers": 33,
    "security_officers": 10,
    "tractors": 20,
    "shelf_life_days": 21,
    "unaccompanied_pct": 0.5,
    "doc_check_cost_eur": 50,
    "phy_check_cost_eur": 500,
    "sec_check_cost_eur": 500
  }'
```

---

## 20. Phase 2 Gap Analysis & Roadmap

### What is missing

| Gap | Impact | Recommended fix |
|---|---|---|
| No standalone Landbridge runs | Cannot predict transit time, waiting time, or queue lengths for IRE↔EU via Landbridge | Generate 60 AnyLogic runs with only LB corridor active, varying check regimes and resource levels |
| No standalone Cherbourg runs | Same, Cherbourg route unpredictable | Generate 50 AnyLogic runs |
| No standalone Rotterdam/Zeebrugge runs | Same | Generate 50 runs combined (both similar) |
| Bilbao: only 3 runs, always bundled | Completely untrained | Generate 40 runs |
| Dover/Calais: only in 11 bundled runs | Cannot predict GB-East waiting time or utilisation alone | Generate 40 runs with Dover/Calais checks active |
| Import check costs at Dublin/Rosslare | Listed as Phase 2 but actually relevant to Phase 1 — costs appear in 25–32% of runs | Re-classify to Phase 1, will train adequately |

### Minimum runs needed to activate Phase 2

| Corridor | Minimum runs needed | Suggested parameter variation |
|---|---|---|
| Landbridge | 50 | 5 check regime levels × 2 volume levels × 5 resource levels |
| Cherbourg | 50 | Same |
| Rotterdam + Zeebrugge | 50 combined | Split 25/25 |
| Bilbao | 40 | 4 check levels × 2 volumes × 5 resource levels |
| Dover/Calais standalone | 40 | Focus on transit check time variation |

### Once Phase 2 data exists

Run `python src/train.py --append --new-runs phase2_runs.xlsx`. The system automatically detects increased coverage for Phase 2 outputs, trains models for them, and updates `registry.json`. The API immediately starts returning real predictions for those outputs instead of `null`.

---

## 21. FastAPI Endpoint Contract

File: `src/ml_api.py` + `src/semantic_api.py` — combined into single FastAPI app

```
Server:     localhost:8000
Framework:  FastAPI + Uvicorn
Launch:     uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### GET /health

```json
Response 200:
{
  "status": "ok",
  "model_version": "v1",
  "training_runs": 228,
  "phase1_models": 101,
  "phase2_models_trained": 0,
  "phase2_models_pending": 35
}
```

### POST /predict (Raw ML API)

```
Request body: dict of up to 153 AnyLogic parameter names (strings)
              Missing keys filled with training medians
Response 200: dict of 136 output predictions
```

### POST /predict/selective (Raw ML API)

```
Request body: {
  ...same as /predict...,
  "outputs": ["output key 1", "output key 2", ...]
}
Response 200: same as /predict but filtered to requested outputs only
```

### GET /outputs

```
Response 200: list of all 136 output parameter objects from registry.json
```

### GET /inputs

```
Response 200: list of all 153 input parameter names with min/max/typical/unit
```

### POST /scenario/predict (Semantic API)

```
Request body:  ScenarioRequest (see Section 13)
Response 200:  ScenarioResponse (see Section 14)
Response 400:  validation error
Response 422:  unknown output key requested
Response 503:  models not loaded (run train.py first)
```

### GET /scenario/options

```
Response 200: VALID_OPTIONS dict (see Section 13)
              Used by UI to populate dropdowns
```

### POST /scenario/validate

```
Request body:  ScenarioRequest (partial, any fields)
Response 200:  {"valid": true, "warnings": [], "active_corridor": "IRE_GB"}
Response 400:  {"valid": false, "errors": ["destination_port 'paris' not valid for eu"]}
```

---

## 22. Error Handling Contract

All errors return JSON with `error` and `detail` fields.

| HTTP code | `error` value | Trigger |
|---|---|---|
| 400 | `invalid_input` | Parameter out of range, invalid enum, negative volume |
| 422 | `unknown_output` | Output key in `/predict/selective` not found in registry |
| 422 | `phase2_not_available` | Route type is Phase 2 and no models trained yet |
| 503 | `model_not_ready` | Model files not found — `train.py` has not been run |
| 500 | `prediction_error` | Unexpected error during model inference |

```python
# Example error responses

# 400
{"error": "invalid_input", "detail": "physical_check_pct must be between 0.0 and 1.0, got 1.5"}

# 422
{"error": "unknown_output", "detail": "Output 'AP avg WT at D' not found. Did you mean 'AP avg WT on im at D'?"}

# 503
{"error": "model_not_ready", "detail": "No model files found in models/v1/. Run: python src/train.py"}
```

---

## 23. Coverage & Confidence Flags

Every prediction in every response carries a `status` field. These are the four valid values and their exact meanings:

| Status | Meaning | When set |
|---|---|---|
| `ok` | Model trained and reliable | Phase 1 output, coverage ≥ 15% of training runs |
| `low_coverage` | Model trained but sparse training data | Phase 1 output, coverage < 15% of training runs |
| `zero_predicted` | Zero-inflation classifier predicts this output is inactive for current inputs | Output has zero-inflation model AND classifier predicts is_nonzero = False |
| `not_trained` | No model exists for this output | Phase 2 output — returns `value: null` |

`overall_confidence` in `ScenarioResponse`:

| Value | Condition |
|---|---|
| `high` | All returned outputs have `status: "ok"` |
| `medium` | At least one output has `status: "low_coverage"` |
| `low` | Majority of outputs are `low_coverage` or `zero_predicted` |

---

## 24. Technology Stack & Dependencies

### requirements.txt

```
xgboost>=1.7.0
scikit-learn>=1.3.0
pandas>=2.0.0
numpy>=1.24.0
pyarrow>=12.0.0       # parquet support
openpyxl>=3.1.0       # xlsx reading
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
joblib>=1.3.0
python-dotenv>=1.0.0
```

### Python version

Python 3.10 or higher required.

### Local only

No cloud services, no external APIs, no database server required. Everything runs on localhost with filesystem-based model storage.

---

## 25. Implementation Checklist for Cursor

Use this checklist with the Superpower plugin. Each item is a discrete, testable task.

### Phase 0 — Environment setup

- [ ] Create `brexit_ml/` directory with structure from Section 3
- [ ] Create `requirements.txt` from Section 24
- [ ] Copy source xlsx to `data/raw/completed_runs.xlsx`
- [ ] Run `pip install -r requirements.txt`

### Phase 1a — Data layer

- [ ] Implement `src/data_loader.py`
  - [ ] Read xlsx, header at row index 1 (not 0)
  - [ ] Drop rows where Run# is null or Status != "Successful"
  - [ ] Drop 5 constant columns listed in Section 4.4
  - [ ] Replace `<Data>` with NaN, fill NaN with 0
  - [ ] Split into X (153 cols in TRAINING_COLUMN_ORDER) and Y (136 cols)
  - [ ] Assert X has exactly 228 rows and 153 columns
  - [ ] Assert Y has exactly 228 rows and 136 columns
  - [ ] Save to parquet

### Phase 1b — Training pipeline

- [ ] Implement `src/train.py`
  - [ ] Fit and save StandardScaler
  - [ ] Implement `col_to_slug()` function
  - [ ] For each of 136 output columns: compute coverage
  - [ ] Train XGBClassifier for outputs with coverage < 0.30
  - [ ] Train XGBRegressor for all outputs
  - [ ] Run 5-fold CV, record R² and MAE
  - [ ] Save all models as .pkl
  - [ ] Write `registry.json` with schema from Section 9
  - [ ] Print summary: any output with R² < 0.5 flagged as WARNING

### Phase 1c — ML engine

- [ ] Implement `src/ml_engine.py`
  - [ ] Load all models and scaler on startup
  - [ ] Implement `_fill_defaults()` using registry training medians
  - [ ] Implement zero-inflation inference logic
  - [ ] Implement phase-2 null return logic
  - [ ] Return structured `PredictionResult` per output

### Phase 1d — Raw ML API

- [ ] Implement `src/ml_api.py` with FastAPI
  - [ ] `GET /health`
  - [ ] `POST /predict`
  - [ ] `POST /predict/selective`
  - [ ] `GET /outputs`
  - [ ] `GET /inputs`
  - [ ] Error responses per Section 22

### Phase 1e — Semantic layer

- [ ] Implement `src/schemas.py` with `ScenarioRequest` and `ScenarioResponse` Pydantic models
- [ ] Implement `src/param_translator.py`
  - [ ] `VOLUME_MAP` (complete, Section 15)
  - [ ] `PORT_ROUTING` (complete, Section 17)
  - [ ] `VESSEL_CAP_MAP` (complete, Section 15)
  - [ ] `RESOURCE_PARAM_MAP` (complete, Section 15)
  - [ ] `CHECK_REGIME_PRESETS` (complete, Section 16)
  - [ ] `translate()` function — 8 steps from Section 15
- [ ] Implement `src/output_filter.py`
  - [ ] `OUTPUT_FILTER_MAP` (Section 18)
  - [ ] `OUTPUT_FILTER_FALLBACK` (Section 18)
- [ ] Implement `src/corridor_router.py`
  - [ ] Detect `active_corridor` from Vol* input values
- [ ] Implement `src/semantic_api.py`
  - [ ] `POST /scenario/predict`
  - [ ] `POST /scenario/validate`
  - [ ] `GET /scenario/options`
  - [ ] `GET /scenario/schema`

### Phase 1f — Tests

- [ ] `tests/test_translator.py`
  - [ ] Test: Ireland/Dublin/agri/export/Liverpool/standard → verify VolAgriExGB is set, all other Vol* are 0
  - [ ] Test: check_regime="hard"/agri → verify PerPhyChkAgriImIR = 0.3
  - [ ] Test: destination_port="holyhead" → verify PerProductMoveHoly=1.0, PerProductMoveLiv=0.0
- [ ] `tests/test_output_filter.py`
  - [ ] Test: (agri, import, direct_gb, dublin, liverpool) → verify correct output list returned
- [ ] `tests/test_api.py`
  - [ ] Test: GET /health returns 200
  - [ ] Test: POST /predict with empty body returns predictions filled from medians
  - [ ] Test: POST /scenario/predict with Phase 1 example from Section 19

### Phase 1g — Incremental retraining

- [ ] Implement `--append` flag in `src/train.py` per Section 8
- [ ] Test: append 10 dummy rows, verify run count increases in registry.json

### Phase 2 (future — after new AnyLogic runs generated)

- [ ] Run new AnyLogic scenarios for Landbridge, Cherbourg, Rotterdam/Zeebrugge, Bilbao, Dover/Calais
- [ ] Append to training data: `python src/train.py --append --new-runs phase2_runs.xlsx`
- [ ] Verify Phase 2 outputs change from `not_trained` to `ok` in `/health` response

---

*End of specification. All data in this document is derived directly from the 228-run AnyLogic export. No external reference required.*
