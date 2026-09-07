# NOLHC AnyLogic Simulation ML Engine — Technical Design Specification

**Version:** 2.0  
**Scope:** Multi-corridor Ireland Brexit simulation — GB, Landbridge & Direct EU routes  
**Purpose:** Self-contained implementation reference for Cursor + Superpower plugin. No external document required.  
**Source data:** `NOLHC_Designs_-_AL_Students.xlsx` — 129 AnyLogic simulation runs  
**Predecessor spec:** `brexit_ml_engine_spec.md` (v1.0, 228-run dataset — superseded by this document)

---

## Table of Contents

1. [System Purpose](#1-system-purpose)
2. [Architecture Overview](#2-architecture-overview)
3. [Repository & Module Structure](#3-repository--module-structure)
4. [Dataset Facts](#4-dataset-facts)
5. [Input Parameters — Complete Reference](#5-input-parameters--complete-reference)
6. [Output Targets — Complete Reference](#6-output-targets--complete-reference)
7. [ML Core Design](#7-ml-core-design)
8. [Model Selection & Benchmarking Strategy](#8-model-selection--benchmarking-strategy)
9. [Training Pipeline](#9-training-pipeline)
10. [Inference Pipeline](#10-inference-pipeline)
11. [Model Registry Schema](#11-model-registry-schema)
12. [Incremental Retraining](#12-incremental-retraining)
13. [FastAPI Endpoint Contract](#13-fastapi-endpoint-contract)
14. [Error Handling Contract](#14-error-handling-contract)
15. [Technology Stack & Dependencies](#15-technology-stack--dependencies)
16. [Implementation Checklist for Cursor](#16-implementation-checklist-for-cursor)

---

## 1. System Purpose

The system replaces the need to run a full AnyLogic discrete-event simulation for every scenario. A trained ML model ensemble predicts 20 simulation KPIs from 35 input parameters in milliseconds rather than the time a full AnyLogic run takes.

**Key difference from predecessor spec:** The new NOLHC dataset is a structured experimental design (Latin Hypercube / factorial design) with 129 runs, 35 numeric input parameters grouped into 4 high-level factors, and 20 clearly named output performance indicators — all non-zero (no zero-inflation problem). This makes the ML task cleaner and allows a proper multi-model benchmarking approach to find the highest-precision model per output.

**Three goals:**
1. Train ML models on the 129 simulation runs to predict all 20 KPIs.
2. Systematically benchmark **19 candidate models** per output — including Gaussian Process Regression, polynomial regression, CatBoost, and all major classical families — and select the highest-precision model (by R²) per output.
3. Build a **stacking ensemble** on top of the individual winners to squeeze out additional precision, and register whichever is better (stack vs. best individual).

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                   │
│  data/raw/nolhc_runs.xlsx         (source — never modified)  │
│  data/processed/X_train.parquet   (129 rows × 35 features)   │
│  data/processed/Y_train.parquet   (129 rows × 20 targets)    │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  TRAINING LAYER  (src/train.py)                              │
│  - Loads and validates data                                  │
│  - Fits StandardScaler on X                                  │
│  - For each of 20 outputs:                                   │
│    · Benchmarks 19 candidate models with 5-fold CV           │
│    · Selects model with highest mean R² (best_individual)    │
│    · Builds stacking ensemble from top-K base learners       │
│    · Registers whichever is better: stack vs individual      │
│    · Saves final model as model_{output_slug}.pkl            │
│  - Writes registry.json with all metrics                     │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  ML ENGINE  (src/ml_engine.py)                               │
│  - Loads scaler + all 20 best models from registry          │
│  - Accepts 35-feature input dict                             │
│  - Returns {output_name: PredictionResult} dict             │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  API LAYER  (src/ml_api.py)                                  │
│  POST /predict                                               │
│  POST /predict/selective                                     │
│  GET  /outputs                                               │
│  GET  /inputs                                                │
│  GET  /health                                                │
│  GET  /benchmark                                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Repository & Module Structure

```
nolhc_ml/
│
├── data/
│   ├── raw/
│   │   └── nolhc_runs.xlsx               # Source AnyLogic export (never modified)
│   └── processed/
│       ├── X_train.parquet               # 129 rows × 35 input features
│       └── Y_train.parquet               # 129 rows × 20 output targets
│
├── models/
│   └── v1/
│       ├── scaler_X.pkl                  # sklearn StandardScaler fitted on X_train
│       ├── model_{output_slug}.pkl       # registered best model per output (20 files)
│       │                                 #   may be individual or stacking ensemble
│       ├── stack_{output_slug}.pkl       # stacking ensemble (saved regardless of whether it won)
│       ├── benchmark_{output_slug}.json  # per-output comparison of all 19 candidate models
│       └── registry.json                 # metadata: best model, R², MAE, training date
│
├── src/
│   ├── data_loader.py                    # reads xlsx, extracts X/Y, saves parquet
│   ├── train.py                          # benchmark + training pipeline
│   ├── ml_engine.py                      # loads models, runs prediction
│   ├── ml_api.py                         # FastAPI: /predict, /health, /outputs, /inputs
│   └── schemas.py                        # Pydantic request/response models
│
├── tests/
│   ├── test_data_loader.py
│   └── test_api.py
│
├── requirements.txt
├── main.py                               # entrypoint: uvicorn app
└── README.md
```

---

## 4. Dataset Facts

All numbers in this section are derived directly from the xlsx file.

### 4.1 Dimensions

| Property | Value |
|---|---|
| Source file | `NOLHC_Designs_-_AL_Students.xlsx` |
| Sheet — parameter descriptions | `Input Parameter Design` |
| Sheet — input values | `ExpValues` |
| Sheet — simulation outputs | `SimResults` |
| Header rows in ExpValues | Rows 1–3 (3-row merged header; data starts row 4) |
| Header rows in SimResults | Rows 1–3 (3-row merged header; data starts row 4) |
| Total simulation runs | **129** |
| Input features (columns) | **35** |
| Output targets | **20** |
| Zero values in inputs | **None** (confirmed by dataset spec) |
| Zero values in outputs | **None** (confirmed by dataset spec) |

### 4.2 Input Factor Groups

The 35 input parameters are organised into 4 high-level experimental factors:

| Factor | Parameters | Description |
|---|---|---|
| 1. Shifts in Trade Volume | 4 | Trade volumes for agri and non-agri, inbound and outbound (GB ↔ IRE) |
| 2. Direct Routes to Mainland Europe | 17 | Volume shifts LB↔Direct, vessel capacities on each route |
| 3. Customs Expertise & Resources | 6 | Check timing (doc, physical) and headcount (Custom sheds, DAFM bays) at Dublin and Rosslare |
| 4. Border Checks Intervention | 8 | Percentage of trucks in each routing category (green/red/pre-boarding) at each port |

### 4.3 Output Target Groups

The 20 outputs are organised into 4 categories:

| Category | KPI codes | Description |
|---|---|---|
| Agri Products | TT_OB_Agri, WT_OB_A_GB-Dub, WT_OB_A_GB-Ross, TT_IB_Agri, WT_IB_A_Dub, WT_IB_A_Ross | Transport times and waiting times for agri products |
| Non-Agri Products | WT_IB_NA_Dub, WT_OB_NA_GB-Dub, WT_IB_NA_Ross, WT_OB_NA_GB-Ross | Waiting times for non-agri products at Dublin and Rosslare |
| Routes | TT_OB_LB, WT_OB_LB, TT_IB_LB, WT_IB_LB, TT_OB_DR, TT_IB_DR | Transport and waiting times for Landbridge and Direct routes |
| Staff Utilisation | Uti_Cus_D, Uti_DAFM_D, Uti_Cus_R, Uti_DAFM_R | Utilisation rates for customs and DAFM staff at Dublin and Rosslare |

---

## 5. Input Parameters — Complete Reference

### Column name mapping

The `ExpValues` sheet uses a 3-row merged header. The column index mapping is:

```python
# Column index (0-based) → parameter name
TRAINING_COLUMN_ORDER = [
    "NA_Im",          # col 1:  Non-agri inbound volume (GB→IRE), tonnes
    "NA_Ex",          # col 2:  Non-agri outbound volume (IRE→GB), tonnes
    "A_Im",           # col 3:  Agri inbound volume (GB→IRE), tonnes
    "A_Ex",           # col 4:  Agri outbound volume (IRE→GB), tonnes
    "NA_Im_LB",       # col 6:  Non-agri inbound volume via Landbridge
    "NA_Im_DR",       # col 7:  Non-agri inbound volume via Direct route
    "NA_Ex_LB",       # col 9:  Non-agri outbound volume via Landbridge
    "NA_Ex_DR",       # col 10: Non-agri outbound volume via Direct route
    "A_Im_LB",        # col 12: Agri inbound volume via Landbridge
    "A_Im_DR",        # col 13: Agri inbound volume via Direct route
    "A_Ex_LB",        # col 15: Agri outbound volume via Landbridge
    "A_Ex_DR",        # col 16: Agri outbound volume via Direct route
    "VCap_Dub_Hey",   # col 17: Vessel capacity Dublin→Heysham (trailers)
    "VCap_Dub_Holy",  # col 18: Vessel capacity Dublin→Holyhead (trailers)
    "VCap_Dub_Liv",   # col 19: Vessel capacity Dublin→Liverpool (trailers)
    "VCap_Ross_Fish", # col 20: Vessel capacity Rosslare→Fishguard (trailers)
    "VCap_Ross_Pem",  # col 21: Vessel capacity Rosslare→Pembroke (trailers)
    "ChkTime_Doc",    # col 22: Check time — documentary & seal identity (minutes)
    "ChkTime_Phy",    # col 23: Check time — physical inspection (minutes)
    "NumCusShed_D",   # col 24: Number of custom sheds at Dublin
    "NumDAFM_D",      # col 25: Number of DAFM bays at Dublin
    "NumCusShed_R",   # col 26: Number of custom sheds at Rosslare
    "NumDAFM_R",      # col 27: Number of DAFM bays at Rosslare
    "Pct_NA_OB_Green",# col 28: % non-agri outbound trucks → green route (fraction)
    "Pct_NA_OB_Red",  # col 29: % non-agri outbound trucks → red route (fraction)
    "Pct_A_OB_Red",   # col 30: % agri outbound trucks → red route (fraction)
    "Pct_NA_IB_Green",# col 31: % non-agri inbound trucks → green route (fraction)
    "Pct_NA_IB_Red",  # col 32: % non-agri inbound trucks → red route (fraction)
    "Pct_A_IB_Red",   # col 33: % agri inbound trucks → red route (fraction)
    "Pct_IB_PreBoard",# col 34: % inbound trucks stopped due to pre-boarding status (fraction)
    "Pct_OB_PreBoard",# col 35: % outbound trucks stopped due to pre-boarding status (fraction)
]
# Total: 35 columns (note: col 0 is the run index — excluded from features)
```

> **CRITICAL parsing note:** The `ExpValues` sheet has a 3-level merged header across rows 1–3. Row 4 onward is data. Column 0 (index 0) is the run number — exclude it from features. Columns 5, 8, 11, and 14 in the header rows contain group labels ("Shift_Vol") for the sub-columns — these rows do not have corresponding data columns and should be skipped. The actual data columns align with the codes listed in header row 3.

### Factor descriptions

**Factor 1 — Shifts in Trade Volume (4 parameters)**

| Code | Description | Unit | Range (observed) |
|---|---|---|---|
| NA_Im | Non-agri inbound demand, GB→IRE | tonnes | ~4.7M – 7.6M |
| NA_Ex | Non-agri outbound demand, IRE→GB | tonnes | ~4.2M – 6.7M |
| A_Im | Agri inbound demand, GB→IRE | tonnes | ~2.2M – 3.5M |
| A_Ex | Agri outbound demand, IRE→GB | tonnes | ~1.6M – 2.6M |

**Factor 2 — Direct Routes to Mainland Europe (17 parameters)**

| Code | Description | Unit |
|---|---|---|
| NA_Im_LB | Non-agri inbound via Landbridge | tonnes |
| NA_Im_DR | Non-agri inbound via Direct route (Cherbourg/Rotterdam etc.) | tonnes |
| NA_Ex_LB | Non-agri outbound via Landbridge | tonnes |
| NA_Ex_DR | Non-agri outbound via Direct route | tonnes |
| A_Im_LB | Agri inbound via Landbridge | tonnes |
| A_Im_DR | Agri inbound via Direct route | tonnes |
| A_Ex_LB | Agri outbound via Landbridge | tonnes |
| A_Ex_DR | Agri outbound via Direct route | tonnes |
| VCap_Dub_Hey | Vessel capacity, Dublin→Heysham | trailers |
| VCap_Dub_Holy | Vessel capacity, Dublin→Holyhead | trailers |
| VCap_Dub_Liv | Vessel capacity, Dublin→Liverpool | trailers |
| VCap_Ross_Fish | Vessel capacity, Rosslare→Fishguard | trailers |
| VCap_Ross_Pem | Vessel capacity, Rosslare→Pembroke | trailers |

**Factor 3 — Customs Expertise & Resources (6 parameters)**

| Code | Description | Unit |
|---|---|---|
| ChkTime_Doc | Check duration per truck — documentary & seal identity | minutes |
| ChkTime_Phy | Check duration per truck — physical inspection | minutes |
| NumCusShed_D | Number of custom sheds at Dublin | count |
| NumDAFM_D | Number of DAFM inspection bays at Dublin | count |
| NumCusShed_R | Number of custom sheds at Rosslare | count |
| NumDAFM_R | Number of DAFM inspection bays at Rosslare | count |

**Factor 4 — Border Checks Intervention (8 parameters)**

| Code | Description | Unit |
|---|---|---|
| Pct_NA_OB_Green | % non-agri outbound trucks → green route | fraction (0–1) |
| Pct_NA_OB_Red | % non-agri outbound trucks → red route | fraction (0–1) |
| Pct_A_OB_Red | % agri outbound trucks → red route | fraction (0–1) |
| Pct_NA_IB_Green | % non-agri inbound trucks → green route | fraction (0–1) |
| Pct_NA_IB_Red | % non-agri inbound trucks → red route | fraction (0–1) |
| Pct_A_IB_Red | % agri inbound trucks → red route | fraction (0–1) |
| Pct_IB_PreBoard | % inbound trucks stopped: pre-boarding status | fraction (0–1) |
| Pct_OB_PreBoard | % outbound trucks stopped: pre-boarding status | fraction (0–1) |

---

## 6. Output Targets — Complete Reference

The `SimResults` sheet has a 3-row merged header. Row 4 onward is data. Column 0 is the run index. All **20** output columns begin at column 1.

```python
OUTPUT_COLUMN_ORDER = [
    "TT_OB_Agri",       # Transport time, agri outbound (IRE→GB), hours
    "WT_OB_A_GB-Dub",   # Waiting time, agri outbound, at Dublin GB-side, hours
    "WT_OB_A_GB-Ross",  # Waiting time, agri outbound, at Rosslare GB-side, hours
    "TT_IB_Agri",       # Transport time, agri inbound (GB→IRE), hours
    "WT_IB_A_Dub",      # Waiting time, agri inbound, at Dublin IRE-side, hours
    "WT_IB_A_Ross",     # Waiting time, agri inbound, at Rosslare IRE-side, hours
    "WT_IB_NA_Dub",     # Waiting time, non-agri inbound, at Dublin, hours
    "WT_OB_NA_GB-Dub",  # Waiting time, non-agri outbound, at Dublin GB-side, hours
    "WT_IB_NA_Ross",    # Waiting time, non-agri inbound, at Rosslare, hours
    "WT_OB_NA_GB-Ross", # Waiting time, non-agri outbound, at Rosslare GB-side, hours
    "TT_OB_LB",         # Transport time, Landbridge outbound, hours
    "WT_OB_LB",         # Waiting time, Landbridge outbound, hours
    "TT_IB_LB",         # Transport time, Landbridge inbound, hours
    "WT_IB_LB",         # Waiting time, Landbridge inbound, hours
    "TT_OB_DR",         # Transport time, Direct route outbound, hours
    "TT_IB_DR",         # Transport time, Direct route inbound, hours
    "Uti_Cus_D",        # Staff utilisation — Customs at Dublin (fraction 0–1)
    "Uti_DAFM_D",       # Staff utilisation — DAFM at Dublin (fraction 0–1)
    "Uti_Cus_R",        # Staff utilisation — Customs at Rosslare (fraction 0–1)
    "Uti_DAFM_R",       # Staff utilisation — DAFM at Rosslare (fraction 0–1)
]
```

**Output unit summary:**

| Prefix | Unit |
|---|---|
| TT_* | Hours (transport time) |
| WT_* | Hours (waiting time) |
| Uti_* | Fraction 0.0–1.0 (staff utilisation) |

---

## 7. ML Core Design

### 7.1 Problem type

**Multi-output regression** — 20 separate continuous targets, no zero-inflation (all outputs non-zero across all 129 runs per dataset spec). One model is trained per output for maximum precision.

### 7.2 No zero-inflation strategy needed

Unlike the predecessor spec (which required a two-stage zero-inflation classifier for sparse outputs), the NOLHC dataset contains **no zero values in inputs or outputs**. Plain regressors are trained on all 129 rows for every output.

### 7.3 Preprocessing

```python
# 1. Parse ExpValues header correctly (3-row merged header — see Section 4 parsing note)
# 2. Parse SimResults header correctly (3-row merged header)
# 3. Align both sheets on run index (column 0)
# 4. No NaN filling required — dataset has no missing values per spec
#    (but add a defensive check and raise ValueError if any NaN found)
# 5. Fit StandardScaler on X_train, save as scaler_X.pkl
# 6. Apply scaler to X before all training and inference

from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_train)
```

### 7.4 Validation strategy

- **5-fold cross-validation** on all 129 rows for every model/output combination
- Primary metric: **R²** (coefficient of determination — measures precision)
- Secondary metric: **MAE** (mean absolute error)
- The model with the **highest mean CV R²** wins the benchmark for each output
- Final registry records: `r2_cv_mean`, `r2_cv_std`, `mae_cv_mean`, `best_model_type`

```python
from sklearn.model_selection import cross_val_score
cv_r2  = cross_val_score(model, X_scaled, y, cv=5, scoring="r2")
cv_mae = cross_val_score(model, X_scaled, y, cv=5, scoring="neg_mean_absolute_error")
```

---

## 8. Model Selection & Benchmarking Strategy

Because the dataset has only 129 rows, the right algorithm is not known a priori. The training pipeline benchmarks **19 candidate models** for each output, then builds a stacking ensemble, and registers the best overall result by CV R².

### 8.1 Candidate model families and rationale

The 19 candidates are organised into 6 families, each included for a specific reason:

| Family | Models | Why included for this dataset |
|---|---|---|
| **Gaussian Process** | GPR (RBF), GPR (Matérn) | Theoretically optimal surrogate for structured experimental designs (LHS/factorial); provides uncertainty estimates; excellent at ≤500 rows |
| **Gradient boosting** | XGBoost, LightGBM, GradientBoosting, CatBoost | Dominant on tabular data; CatBoost adds different regularisation that sometimes wins where XGB/LGBM don't |
| **Tree ensembles** | RandomForest, ExtraTrees | Strong baselines; ExtraTrees adds extra randomisation that can reduce variance on small datasets |
| **Kernel / SVM** | SVR-RBF, SVR-Poly | Often excellent on small datasets; RBF captures smooth response surfaces, Poly captures polynomial interactions |
| **Polynomial regression** | PolynomialRegression-deg2, PolynomialRegression-deg3 | Classic response surface methodology for simulation surrogates; interpretable; competitive when the true surface is smooth |
| **Linear regularised** | Ridge, Lasso, ElasticNet, BayesianRidge | Fast baselines; BayesianRidge also provides prediction intervals; useful when response is near-linear |
| **Other** | KNN, MLP, AdaBoost | KNN captures local structure; MLP is a deep learning reference point (expected to underperform at 129 rows but included for completeness); AdaBoost is a historical boosting baseline |

### 8.2 Candidate model instantiation

```python
from sklearn.ensemble import (
    GradientBoostingRegressor, RandomForestRegressor, ExtraTreesRegressor,
    AdaBoostRegressor
)
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, Matern, ConstantKernel as C
from sklearn.linear_model import Ridge, Lasso, ElasticNet, BayesianRidge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor

CANDIDATE_MODELS = {

    # ── Gaussian Process ─────────────────────────────────────────────────
    "gpr_rbf": GaussianProcessRegressor(
        kernel=C(1.0) * RBF(length_scale=1.0),
        n_restarts_optimizer=10,
        normalize_y=True,
        random_state=42,
    ),
    "gpr_matern": GaussianProcessRegressor(
        kernel=C(1.0) * Matern(length_scale=1.0, nu=1.5),
        n_restarts_optimizer=10,
        normalize_y=True,
        random_state=42,
    ),

    # ── Gradient boosting ────────────────────────────────────────────────
    "xgboost": XGBRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        reg_alpha=0.1, reg_lambda=1.0, objective="reg:squarederror",
        random_state=42, n_jobs=-1,
    ),
    "lightgbm": LGBMRegressor(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_samples=5,
        reg_alpha=0.1, reg_lambda=1.0, random_state=42, n_jobs=-1,
        verbose=-1,
    ),
    "catboost": CatBoostRegressor(
        iterations=300, depth=4, learning_rate=0.05,
        l2_leaf_reg=3.0, random_seed=42, verbose=0,
    ),
    "gradient_boosting": GradientBoostingRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, min_samples_split=5, random_state=42,
    ),

    # ── Tree ensembles ───────────────────────────────────────────────────
    "random_forest": RandomForestRegressor(
        n_estimators=300, max_depth=None, min_samples_split=4,
        min_samples_leaf=2, random_state=42, n_jobs=-1,
    ),
    "extra_trees": ExtraTreesRegressor(
        n_estimators=300, max_depth=None, min_samples_split=4,
        min_samples_leaf=2, random_state=42, n_jobs=-1,
    ),

    # ── Kernel / SVM ─────────────────────────────────────────────────────
    "svr_rbf":  SVR(kernel="rbf",  C=10.0, epsilon=0.1, gamma="scale"),
    "svr_poly": SVR(kernel="poly", degree=3, C=5.0, epsilon=0.1, gamma="scale"),

    # ── Polynomial regression (response surface methodology) ─────────────
    # Pipeline: PolynomialFeatures → Ridge (regularised to avoid overfitting
    # with degree-3 expansion of 35 features = ~7,000 interaction terms)
    "poly_deg2": Pipeline([
        ("poly", PolynomialFeatures(degree=2, include_bias=False)),
        ("ridge", Ridge(alpha=10.0)),
    ]),
    "poly_deg3": Pipeline([
        ("poly", PolynomialFeatures(degree=3, include_bias=False)),
        ("ridge", Ridge(alpha=100.0)),  # stronger regularisation for degree-3 expansion
    ]),

    # ── Linear regularised ───────────────────────────────────────────────
    "ridge":        Ridge(alpha=1.0),
    "lasso":        Lasso(alpha=0.01, max_iter=5000),
    "elastic_net":  ElasticNet(alpha=0.01, l1_ratio=0.5, max_iter=5000),
    "bayesian_ridge": BayesianRidge(),

    # ── Other ────────────────────────────────────────────────────────────
    "knn": KNeighborsRegressor(n_neighbors=7, weights="distance"),
    "mlp": MLPRegressor(
        hidden_layer_sizes=(128, 64), activation="relu",
        max_iter=500, random_state=42, early_stopping=True,
        validation_fraction=0.15,
    ),
    "adaboost": AdaBoostRegressor(
        n_estimators=200, learning_rate=0.05, random_state=42,
    ),
}
# Total: 19 candidate models
```

> **GPR scaling note:** GPR has O(n³) training complexity. At 129 rows this is fast (<1 second per fit), but will become slow above ~2,000 rows. If the dataset grows significantly, consider switching GPR to `sklearn.gaussian_process.GaussianProcessRegressor` with `n_restarts_optimizer=3` or replacing with `GPy` / `GPflow` for larger data.

> **poly_deg3 note:** A degree-3 expansion of 35 features produces ~7,000 interaction columns. Ridge regularisation (`alpha=100.0`) is essential. If memory becomes an issue, use `PolynomialFeatures(degree=3, interaction_only=True)` to reduce to ~6,500 columns, or drop `poly_deg3` and retain only `poly_deg2`.

### 8.3 Benchmark execution

```python
from sklearn.model_selection import cross_val_score, KFold

CV_FOLDS = 5
cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)

def benchmark_models(X_scaled, y, output_slug):
    """
    Runs 5-fold CV for all 19 candidate models on a single output.
    Returns results dict sorted by r2_mean descending.
    """
    results = {}
    for name, model in CANDIDATE_MODELS.items():
        try:
            cv_r2  = cross_val_score(model, X_scaled, y, cv=cv, scoring="r2")
            cv_mae = cross_val_score(model, X_scaled, y, cv=cv,
                                     scoring="neg_mean_absolute_error")
            results[name] = {
                "r2_mean":  float(cv_r2.mean()),
                "r2_std":   float(cv_r2.std()),
                "mae_mean": float(-cv_mae.mean()),
                "mae_std":  float(cv_mae.std()),
                "status":   "ok",
            }
        except Exception as e:
            # poly_deg3 may fail if expansion exceeds memory; log and skip
            results[name] = {
                "r2_mean": -999.0, "r2_std": 0.0,
                "mae_mean": 999.0, "mae_std": 0.0,
                "status": f"failed: {str(e)[:120]}",
            }

    sorted_results = dict(
        sorted(results.items(), key=lambda x: x[1]["r2_mean"], reverse=True)
    )
    return sorted_results
```

### 8.4 Stacking ensemble

After all 19 individual models have been benchmarked, a stacking ensemble is built using the **top-K base learners** (default K=5) with a Ridge meta-learner trained on out-of-fold predictions.

```python
from sklearn.ensemble import StackingRegressor

STACK_TOP_K = 5   # number of best individual models to use as base learners

def build_stacking_ensemble(benchmark_results, X_scaled, y):
    """
    Selects top-K models from benchmark, builds StackingRegressor,
    evaluates with 5-fold CV, returns (stack_model, stack_r2_mean, stack_r2_std).
    """
    # Pick top-K by r2_mean, excluding failed models
    ranked = [
        (name, info) for name, info in benchmark_results.items()
        if info["status"] == "ok"
    ][:STACK_TOP_K]

    estimators = [(name, clone(CANDIDATE_MODELS[name])) for name, _ in ranked]

    stack = StackingRegressor(
        estimators=estimators,
        final_estimator=Ridge(alpha=1.0),
        cv=5,                          # inner CV for generating meta-features
        passthrough=False,             # only meta-features, not raw X, fed to meta-learner
        n_jobs=-1,
    )

    cv_r2  = cross_val_score(stack, X_scaled, y, cv=cv, scoring="r2")
    cv_mae = cross_val_score(stack, X_scaled, y, cv=cv,
                             scoring="neg_mean_absolute_error")

    stack_results = {
        "r2_mean":  float(cv_r2.mean()),
        "r2_std":   float(cv_r2.std()),
        "mae_mean": float(-cv_mae.mean()),
        "mae_std":  float(cv_mae.std()),
        "base_learners": [name for name, _ in ranked],
    }
    return stack, stack_results
```

### 8.5 Final model selection rule

```python
def select_final_model(benchmark_results, stack_results, X_scaled, y):
    """
    Compares best individual model vs stacking ensemble by CV R².
    Returns (final_model_object, final_model_name, final_r2).
    winner_name will be 'stacking' or the individual model name.
    """
    best_individual_name = max(
        [k for k, v in benchmark_results.items() if v["status"] == "ok"],
        key=lambda k: benchmark_results[k]["r2_mean"]
    )
    best_individual_r2 = benchmark_results[best_individual_name]["r2_mean"]
    stack_r2           = stack_results["r2_mean"]

    if stack_r2 > best_individual_r2:
        winner_name = "stacking"
        winner_r2   = stack_r2
        # Refit stacking ensemble on full dataset
        estimators = [
            (name, clone(CANDIDATE_MODELS[name]))
            for name in stack_results["base_learners"]
        ]
        final_model = StackingRegressor(
            estimators=estimators,
            final_estimator=Ridge(alpha=1.0),
            cv=5, passthrough=False, n_jobs=-1,
        )
        final_model.fit(X_scaled, y)
    else:
        winner_name = best_individual_name
        winner_r2   = best_individual_r2
        # Refit best individual on full dataset
        final_model = clone(CANDIDATE_MODELS[best_individual_name])
        final_model.fit(X_scaled, y)

    return final_model, winner_name, winner_r2
```

The final model (individual or stack) is saved as `model_{output_slug}.pkl`. The stacking ensemble is **always** saved as `stack_{output_slug}.pkl` regardless of whether it won.

### 8.6 Expected performance guidelines

Given 129 rows and 35 features, acceptable R² thresholds:

| R² range | Assessment | `confidence` tag |
|---|---|---|
| ≥ 0.90 | Excellent — use with high confidence | `"high"` |
| 0.75–0.89 | Good — moderate uncertainty | `"good"` |
| 0.50–0.74 | Acceptable — flag low confidence in responses | `"low"` |
| < 0.50 | Poor — log warning, output still returned but flagged | `"poor"` |

### 8.7 Priority expectations by model type

For this dataset (structured LHS design, 129 rows, continuous smooth simulation outputs), the most likely ordering by performance is:

1. **GPR (RBF or Matérn)** — highest probability of winning; designed exactly for this scenario
2. **Stacking ensemble** — often beats all individuals when GPR + a boosting model combine
3. **XGBoost / LightGBM / CatBoost** — strong across all output types
4. **SVR-RBF** — competitive on smooth response surfaces
5. **Polynomial degree-2** — competitive when true surface is near-quadratic
6. **RandomForest / ExtraTrees** — solid baselines
7. **Ridge / BayesianRidge** — strong if response is near-linear (utilisation outputs)
8. **Polynomial degree-3** — may overfit; depends heavily on regularisation
9. **KNN / AdaBoost** — mid-tier; useful comparison points
10. **MLP** — expected to underperform at 129 rows but retained for completeness

---

## 9. Training Pipeline

File: `src/train.py`

### Step-by-step execution order

```
1.  data_loader.load_data()
    - reads ExpValues sheet; skips rows 1–3 (header), starts row 4
    - reads SimResults sheet; skips rows 1–3 (header), starts row 4
    - drops column 0 (run index) from both
    - aligns on shared row index
    - asserts shape: X = (129, 35), Y = (129, 20)
    - raises ValueError if any NaN found in X or Y
    - saves X_train.parquet and Y_train.parquet

2.  scaler = StandardScaler().fit(X)
    - saves to models/v{N}/scaler_X.pkl

3.  For each output column in Y (20 total):
    a.  run benchmark_models(X_scaled, y_col) → benchmark dict (19 candidates)
    b.  save benchmark dict to models/v{N}/benchmark_{slug}.json
    c.  build stacking ensemble from top-5 individual models
    d.  evaluate stacking ensemble with 5-fold CV → stack_results
    e.  run select_final_model() → compare stack R² vs best individual R²
    f.  refit winner on full X_scaled and y_col → save model_{slug}.pkl
    g.  always save stacking ensemble (even if it lost) → save stack_{slug}.pkl
    h.  record all metrics in registry

4.  build registry.json (see Section 11)

5.  print summary table:
    - one row per output: output name | winner | winner R² mean | R² std | MAE | stack R²
    - flag any output with R² < 0.75 as ⚠ WARNING
    - print overall avg R² across all 20 outputs
    - print count of outputs where stacking beat best individual
```

### Column slug generation

```python
import re
def col_to_slug(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug[:80]

# Examples:
# "TT_OB_Agri"        → "tt_ob_agri"
# "WT_IB_A_Dub"       → "wt_ib_a_dub"
# "WT_OB_A_GB-Dub"    → "wt_ob_a_gb_dub"
# "Uti_Cus_D"         → "uti_cus_d"
# "TT_IB_LB"          → "tt_ib_lb"
```

---

## 10. Inference Pipeline

File: `src/ml_engine.py`

```python
class MLEngine:
    def __init__(self, model_version: str = "v1"):
        self.scaler   = joblib.load(f"models/{model_version}/scaler_X.pkl")
        self.models   = {}     # {output_slug: fitted regressor}
        self.registry = json.load(open(f"models/{model_version}/registry.json"))
        self._load_all_models(model_version)

    def predict(self, input_vector: dict) -> dict:
        """
        input_vector: dict keyed by TRAINING_COLUMN_ORDER names.
        Missing keys are filled with training medians from registry.
        Returns: dict of {output_slug: PredictionResult}
        """
        # 1. Fill any missing inputs with training medians
        X = {col: input_vector.get(col, self.registry["training_medians"][col])
             for col in TRAINING_COLUMN_ORDER}

        # 2. Build ordered numpy array
        x_arr = np.array([X[col] for col in TRAINING_COLUMN_ORDER]).reshape(1, -1)

        # 3. Apply scaler
        x_scaled = self.scaler.transform(x_arr)

        # 4. Run each model
        results = {}
        for slug, model in self.models.items():
            info = self.registry["outputs"][slug]
            value = float(model.predict(x_scaled)[0])
            r2    = info["r2_cv_mean"]
            status = "ok" if r2 >= 0.75 else "low_confidence"
            results[slug] = PredictionResult(
                value=value,
                unit=info["unit"],
                status=status,
                r2=r2,
                best_model_type=info["best_model_type"],
                mae=info["mae_cv_mean"],
            )
        return results

    def _load_all_models(self, version):
        for slug in self.registry["outputs"]:
            path = f"models/{version}/model_{slug}.pkl"
            self.models[slug] = joblib.load(path)
```

---

## 11. Model Registry Schema

File: `models/v{N}/registry.json`

```json
{
  "version": "v1",
  "trained_at": "2024-06-01T10:00:00Z",
  "training_runs": 129,
  "input_features": 35,
  "output_targets": 20,
  "candidate_models_benchmarked": 19,
  "scaler": "scaler_X.pkl",
  "avg_r2_all_outputs": 0.91,
  "stacking_won_count": 7,
  "training_medians": {
    "NA_Im":           6140332.8,
    "NA_Ex":           5387457.6,
    "A_Im":            2826919.5,
    "A_Ex":            2111498.91,
    "NA_Im_LB":        747571.2,
    "NA_Im_DR":        681188.8,
    "NA_Ex_LB":        835756.8,
    "NA_Ex_DR":        480163.2,
    "A_Im_LB":         427437.78,
    "A_Im_DR":         301281.22,
    "A_Ex_LB":         344142.07,
    "A_Ex_DR":         119461.93,
    "VCap_Dub_Hey":    63.44,
    "VCap_Dub_Holy":   108.68,
    "VCap_Dub_Liv":    63.96,
    "VCap_Ross_Fish":  51.75,
    "VCap_Ross_Pem":   84.18,
    "ChkTime_Doc":     4.28,
    "ChkTime_Phy":     33.99,
    "NumCusShed_D":    2.14,
    "NumDAFM_D":       15.45,
    "NumCusShed_R":    0.79,
    "NumDAFM_R":       0.28,
    "Pct_NA_OB_Green": 0.27,
    "Pct_NA_OB_Red":   0.38,
    "Pct_A_OB_Red":    0.83,
    "Pct_NA_IB_Green": 0.33,
    "Pct_NA_IB_Red":   0.28,
    "Pct_A_IB_Red":    0.30,
    "Pct_IB_PreBoard": 0.29,
    "Pct_OB_PreBoard": 0.29
  },
  "outputs": {
    "tt_ob_agri": {
      "raw_key":              "TT_OB_Agri",
      "description":          "Transport time, agri outbound (IRE→GB)",
      "unit":                 "hours",
      "model_file":           "model_tt_ob_agri.pkl",
      "stack_file":           "stack_tt_ob_agri.pkl",
      "benchmark_file":       "benchmark_tt_ob_agri.json",
      "registered_as":        "stacking",
      "best_individual":      "gpr_rbf",
      "best_individual_r2":   0.91,
      "stack_r2_cv_mean":     0.93,
      "r2_cv_mean":           0.93,
      "r2_cv_std":            0.03,
      "mae_cv_mean":          1.1,
      "stack_base_learners":  ["gpr_rbf", "xgboost", "lightgbm", "svr_rbf", "catboost"],
      "confidence":           "high"
    },
    "wt_ob_a_gb_dub": {
      "raw_key":              "WT_OB_A_GB-Dub",
      "description":          "Waiting time, agri outbound, Dublin GB-side",
      "unit":                 "hours",
      "model_file":           "model_wt_ob_a_gb_dub.pkl",
      "stack_file":           "stack_wt_ob_a_gb_dub.pkl",
      "benchmark_file":       "benchmark_wt_ob_a_gb_dub.json",
      "registered_as":        "gpr_rbf",
      "best_individual":      "gpr_rbf",
      "best_individual_r2":   0.87,
      "stack_r2_cv_mean":     0.85,
      "r2_cv_mean":           0.87,
      "r2_cv_std":            0.05,
      "mae_cv_mean":          0.08,
      "stack_base_learners":  ["gpr_rbf", "svr_rbf", "xgboost", "catboost", "poly_deg2"],
      "confidence":           "good"
    }
    // ... one entry per output (20 total)
  }
}
```

**Benchmark file format** (`benchmark_{slug}.json`):

```json
{
  "output": "TT_OB_Agri",
  "slug":   "tt_ob_agri",
  "results": {
    "gpr_rbf":           { "r2_mean": 0.91, "r2_std": 0.03, "mae_mean": 1.1, "mae_std": 0.2, "status": "ok" },
    "gpr_matern":        { "r2_mean": 0.90, "r2_std": 0.04, "mae_mean": 1.2, "mae_std": 0.3, "status": "ok" },
    "xgboost":           { "r2_mean": 0.89, "r2_std": 0.04, "mae_mean": 1.3, "mae_std": 0.3, "status": "ok" },
    "catboost":          { "r2_mean": 0.88, "r2_std": 0.05, "mae_mean": 1.4, "mae_std": 0.4, "status": "ok" },
    "lightgbm":          { "r2_mean": 0.87, "r2_std": 0.05, "mae_mean": 1.5, "mae_std": 0.4, "status": "ok" },
    "svr_rbf":           { "r2_mean": 0.86, "r2_std": 0.06, "mae_mean": 1.6, "mae_std": 0.5, "status": "ok" },
    "poly_deg2":         { "r2_mean": 0.84, "r2_std": 0.06, "mae_mean": 1.8, "mae_std": 0.5, "status": "ok" },
    "random_forest":     { "r2_mean": 0.83, "r2_std": 0.07, "mae_mean": 2.0, "mae_std": 0.6, "status": "ok" },
    "gradient_boosting": { "r2_mean": 0.82, "r2_std": 0.07, "mae_mean": 2.1, "mae_std": 0.6, "status": "ok" },
    "extra_trees":       { "r2_mean": 0.81, "r2_std": 0.07, "mae_mean": 2.2, "mae_std": 0.6, "status": "ok" },
    "bayesian_ridge":    { "r2_mean": 0.78, "r2_std": 0.08, "mae_mean": 2.5, "mae_std": 0.7, "status": "ok" },
    "svr_poly":          { "r2_mean": 0.76, "r2_std": 0.09, "mae_mean": 2.7, "mae_std": 0.7, "status": "ok" },
    "ridge":             { "r2_mean": 0.74, "r2_std": 0.09, "mae_mean": 2.9, "mae_std": 0.8, "status": "ok" },
    "knn":               { "r2_mean": 0.72, "r2_std": 0.10, "mae_mean": 3.1, "mae_std": 0.8, "status": "ok" },
    "elastic_net":       { "r2_mean": 0.70, "r2_std": 0.10, "mae_mean": 3.2, "mae_std": 0.8, "status": "ok" },
    "lasso":             { "r2_mean": 0.68, "r2_std": 0.11, "mae_mean": 3.4, "mae_std": 0.9, "status": "ok" },
    "adaboost":          { "r2_mean": 0.65, "r2_std": 0.11, "mae_mean": 3.7, "mae_std": 0.9, "status": "ok" },
    "mlp":               { "r2_mean": 0.61, "r2_std": 0.13, "mae_mean": 4.1, "mae_std": 1.0, "status": "ok" },
    "poly_deg3":         { "r2_mean": -999, "r2_std": 0.0,  "mae_mean": 999, "mae_std": 0.0, "status": "failed: MemoryError" }
  },
  "stacking": {
    "r2_mean": 0.93, "r2_std": 0.03, "mae_mean": 1.0, "mae_std": 0.2,
    "base_learners": ["gpr_rbf", "xgboost", "catboost", "lightgbm", "svr_rbf"]
  },
  "winner": "stacking"
}
```

---

## 12. Incremental Retraining

```bash
# Add new runs and retrain (full benchmark re-run)
python src/train.py --new-runs path/to/new_runs.xlsx --append

# Full retrain from scratch
python src/train.py
```

**Append logic:**
1. Load existing `X_train.parquet` and `Y_train.parquet`
2. Load new xlsx, apply same 3-row-header parsing
3. Deduplicate on run index column
4. Concatenate and save updated parquet files
5. Bump version: `v1 → v2`, create `models/v2/`
6. Re-run full benchmark + training pipeline on combined dataset
7. Print R² delta per output (new R² − old R²) and flag any regressions

---

## 13. FastAPI Endpoint Contract

```
Server:    localhost:8000
Framework: FastAPI + Uvicorn
Launch:    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### GET /health

```json
{
  "status": "ok",
  "model_version": "v1",
  "training_runs": 129,
  "output_models": 20,
  "candidate_models_benchmarked": 19,
  "avg_r2": 0.91,
  "stacking_won_count": 7,
  "outputs_below_threshold": []
}
```

### POST /predict

**Request body:** JSON object with up to 35 input parameter names (any missing keys filled from training medians).

```json
{
  "NA_Im": 6140332.8,
  "A_Im": 2826919.5,
  "NumCusShed_D": 2.14,
  "Pct_A_IB_Red": 0.30
}
```

**Response 200:**
```json
{
  "tt_ob_agri":  { "value": 23.5, "unit": "hours",    "status": "ok", "r2": 0.93, "registered_as": "stacking", "mae": 1.0 },
  "wt_ib_a_dub": { "value": 0.38, "unit": "hours",    "status": "ok", "r2": 0.87, "registered_as": "gpr_rbf",  "mae": 0.08 },
  "uti_cus_d":   { "value": 0.81, "unit": "fraction", "status": "ok", "r2": 0.94, "registered_as": "stacking", "mae": 0.02 }
  // ... 20 total
}
```

### POST /predict/selective

Same as `/predict` but with an additional `"outputs"` key listing only the output slugs you want:

```json
{
  "NA_Im": 6140332.8,
  "outputs": ["tt_ob_agri", "uti_cus_d", "uti_dafm_d"]
}
```

### GET /outputs

Returns the full registry `outputs` dict — one entry per KPI with description, unit, best model, and CV metrics.

### GET /inputs

Returns a list of all 35 input parameters with their descriptions, units, and training medians.

### GET /benchmark/{output_slug}

Returns the full `benchmark_{slug}.json` for that output — all 19 individual model scores ranked by R², plus the stacking ensemble result and the overall winner.

---

## 14. Error Handling Contract

| HTTP code | `error` value | Trigger |
|---|---|---|
| 400 | `invalid_input` | Input value outside plausible range (e.g. fraction > 1.0, negative volume) |
| 404 | `output_not_found` | Slug in `/predict/selective` not in registry |
| 503 | `model_not_ready` | Model files not found — `train.py` has not been run |
| 500 | `prediction_error` | Unexpected error during model inference |

```python
# Example error responses
{"error": "invalid_input",   "detail": "Pct_A_IB_Red must be between 0.0 and 1.0, got 1.3"}
{"error": "output_not_found","detail": "Output 'tt_ob_agri_x' not found. Valid slugs: tt_ob_agri, wt_ib_a_dub, ..."}
{"error": "model_not_ready", "detail": "No model files in models/v1/. Run: python src/train.py"}
```

---

## 15. Technology Stack & Dependencies

### requirements.txt

```
xgboost>=1.7.0
lightgbm>=3.3.0
catboost>=1.2.0
scikit-learn>=1.3.0        # includes GPR, PolynomialFeatures, StackingRegressor
pandas>=2.0.0
numpy>=1.24.0
pyarrow>=12.0.0
openpyxl>=3.1.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
joblib>=1.3.0
python-dotenv>=1.0.0
```

### Python version

Python 3.10 or higher required.

### Local only

No cloud services, no database server required. Everything runs on localhost with filesystem-based model storage.

---

## 16. Implementation Checklist for Cursor

Use this checklist with the Superpower plugin. Each item is a discrete, testable task.

### Phase 0 — Environment setup

- [ ] Create `nolhc_ml/` directory with structure from Section 3
- [ ] Create `requirements.txt` from Section 15
- [ ] Copy source xlsx to `data/raw/nolhc_runs.xlsx`
- [ ] Run `pip install -r requirements.txt`

### Phase 1a — Data layer (`src/data_loader.py`)

- [ ] Parse `ExpValues` sheet:
  - [ ] Skip header rows 1–3 (merged header)
  - [ ] Drop column 0 (run index)
  - [ ] Map remaining columns to `TRAINING_COLUMN_ORDER` (35 params)
  - [ ] Assert shape: (129, 35)
- [ ] Parse `SimResults` sheet:
  - [ ] Skip header rows 1–3 (merged header)
  - [ ] Drop column 0 (run index)
  - [ ] Map remaining columns to `OUTPUT_COLUMN_ORDER` (20 KPIs)
  - [ ] Assert shape: (129, 20)
- [ ] Validate no NaN in X or Y (raise `ValueError` if found)
- [ ] Save `X_train.parquet` and `Y_train.parquet`
- [ ] Save training medians to a JSON file for use by inference

### Phase 1b — Training pipeline (`src/train.py`)

- [ ] Fit and save `StandardScaler`
- [ ] Implement `col_to_slug()` per Section 9
- [ ] Implement `benchmark_models()` per Section 8.3:
  - [ ] All 19 candidate models instantiated per Section 8.2
  - [ ] GPR (RBF kernel) instantiated with `n_restarts_optimizer=10`, `normalize_y=True`
  - [ ] GPR (Matérn kernel, nu=1.5) instantiated similarly
  - [ ] CatBoost instantiated with `verbose=0`
  - [ ] `poly_deg2` as `Pipeline([PolynomialFeatures(degree=2), Ridge(alpha=10)])`
  - [ ] `poly_deg3` as `Pipeline([PolynomialFeatures(degree=3), Ridge(alpha=100)])`
  - [ ] 5-fold CV with `KFold(shuffle=True, random_state=42)` for each model/output combination
  - [ ] Wrap each model CV in try/except — log failure, assign r2_mean=-999
  - [ ] Results sorted by `r2_mean` descending
- [ ] Implement `build_stacking_ensemble()` per Section 8.4:
  - [ ] Select top-5 individual models (excluding failed ones)
  - [ ] Use `StackingRegressor` with `Ridge` meta-learner and `cv=5`
  - [ ] Evaluate stack with 5-fold CV
- [ ] Implement `select_final_model()` per Section 8.5:
  - [ ] Compare stack R² vs best individual R²
  - [ ] Refit winner on full dataset → save `model_{slug}.pkl`
  - [ ] Always refit and save stack → save `stack_{slug}.pkl`
- [ ] For each of 20 outputs:
  - [ ] Run benchmark, save `benchmark_{slug}.json` (including stacking result and winner field)
  - [ ] Save registered model as `model_{slug}.pkl`
  - [ ] Save stacking ensemble as `stack_{slug}.pkl`
- [ ] Write `registry.json` per Section 11 schema (includes `registered_as`, `stacking_won_count`)
- [ ] Print summary table: output | winner | R² mean | R² std | stack R² | MAE
- [ ] Print: "Stacking won for X/20 outputs"
- [ ] Flag ⚠ WARNING for any output with R² < 0.75

### Phase 1c — ML engine (`src/ml_engine.py`)

- [ ] Load scaler + all 20 models on startup
- [ ] Implement `_fill_defaults()` using registry training medians
- [ ] Implement ordered numpy array construction matching `TRAINING_COLUMN_ORDER`
- [ ] Return structured `PredictionResult` per output with status, unit, R², best model name

### Phase 1d — API (`src/ml_api.py`)

- [ ] `GET /health` — returns model status + avg R²
- [ ] `POST /predict` — full 20-output prediction
- [ ] `POST /predict/selective` — filtered output prediction
- [ ] `GET /outputs` — full registry outputs dict
- [ ] `GET /inputs` — all 35 input param descriptions + medians
- [ ] `GET /benchmark/{output_slug}` — full benchmark comparison for one output
- [ ] Error responses per Section 14

### Phase 1e — Tests (`tests/`)

- [ ] `test_data_loader.py`:
  - [ ] Assert X shape = (129, 35)
  - [ ] Assert Y shape = (129, 20)
  - [ ] Assert no NaN in X or Y
  - [ ] Assert all column names present in TRAINING_COLUMN_ORDER
- [ ] `test_api.py`:
  - [ ] `GET /health` returns 200 and includes `stacking_won_count` field
  - [ ] `POST /predict` with empty body returns 20 predictions (filled from medians)
  - [ ] `POST /predict/selective` with `["tt_ob_agri", "uti_cus_d"]` returns 2 predictions
  - [ ] `GET /benchmark/tt_ob_agri` returns 19 individual model entries + stacking entry + winner field
  - [ ] `POST /predict` with `Pct_A_IB_Red: 1.5` returns 400
- [ ] `test_train.py`:
  - [ ] After running `train.py`, assert `stack_{slug}.pkl` exists for all 20 outputs
  - [ ] Assert `benchmark_{slug}.json` `winner` field is either `"stacking"` or a valid model name
  - [ ] Assert registry `stacking_won_count` is an integer between 0 and 20

### Phase 1f — Incremental retraining

- [ ] Implement `--append` flag per Section 12
- [ ] Test: append 5 dummy rows, verify run count increases in registry.json and R² delta printed

---

*End of specification. All structural facts in this document are derived directly from the NOLHC_Designs_-_AL_Students.xlsx file. The predecessor spec (brexit_ml_engine_spec.md) covers the 228-run dataset and should not be mixed with this implementation.*
