# ML Surrogate Modelling Pipeline — Specification Document
**Dataset:** NOLHC Designs — AL Students | **Version:** 1.0 | **March 2026**

---

## Quick Reference

| Item | Detail |
|---|---|
| Input File | NOLHC_Designs_-_AL_Students.xlsx |
| Feature Sheet | ExpValues (35 input parameters) |
| Target Sheet | SimResults (20 output variables) |
| Total Samples | 129 rows |
| Train / Test Split | 80% train (103 rows) / 20% test (26 rows) |
| Models | 19 regression models |
| CV Strategy | 5-Fold on training set only |
| HP Selection | Best mean RMSE + lowest std across folds |
| Statistical Test | Pairwise Paired t-test (171 pairs × 20 targets) |
| Conformal Prediction | Adaptive coverage per model from test residuals |
| Outputs | Excel report + Python script |

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Step-by-Step Pipeline](#2-step-by-step-pipeline)
3. [Model Selection Strategy](#3-model-selection-strategy)
4. [Code Architecture](#4-code-architecture)
5. [Cursor Prompts](#5-cursor-prompts)
6. [Implementation Checklist](#6-implementation-checklist)

---

## 1. Project Overview

This pipeline builds and evaluates 19 ML surrogate models for each of 20 continuous target variables derived from the NOLHC simulation dataset. The pipeline is strictly designed to prevent data leakage — the 20% test set is never exposed during training or hyperparameter tuning.

### 1.1 Dataset Summary

| Item | Detail |
|---|---|
| Input File | NOLHC_Designs_-_AL_Students.xlsx |
| Feature Sheet | ExpValues — rows 4+ are data; row 3 has short variable codes |
| Target Sheet | SimResults — rows 4+ are data; row 3 has variable names |
| Feature Count | 35 columns (after dropping Run index) |
| Target Count | 20 columns (after dropping Run index) |
| Sample Count | 129 rows (complete cases) |

### 1.2 Target Variables (20)

| # | Variable | Description Group |
|---|---|---|
| 1 | TT_OB_Agri | Agri Products — Outbound Transit Time |
| 2 | WT_OB_A_GB-Dub | Agri Products — Outbound Wait Time (Dublin) |
| 3 | WT_OB_A_GB-Ross | Agri Products — Outbound Wait Time (Rosslare) |
| 4 | TT_IB_Agri | Agri Products — Inbound Transit Time |
| 5 | WT_IB_A_Dub | Agri Products — Inbound Wait Time (Dublin) |
| 6 | WT_IB_A_Ross | Agri Products — Inbound Wait Time (Rosslare) |
| 7 | WT_IB_NA_Dub | Non-Agri Products — Inbound Wait (Dublin) |
| 8 | WT_OB_NA_GB-Dub | Non-Agri Products — Outbound Wait (Dublin) |
| 9 | WT_IB_NA_Ross | Non-Agri Products — Inbound Wait (Rosslare) |
| 10 | WT_OB_NA_GB-Ross | Non-Agri Products — Outbound Wait (Rosslare) |
| 11 | TT_OB_LB | Routes — Outbound Landbridge Transit Time |
| 12 | WT_OB_LB | Routes — Outbound Landbridge Wait Time |
| 13 | TT_IB_LB | Routes — Inbound Landbridge Transit Time |
| 14 | WT_IB_LB | Routes — Inbound Landbridge Wait Time |
| 15 | TT_OB_DR | Routes — Outbound Direct Route Transit Time |
| 16 | TT_IB_DR | Routes — Inbound Direct Route Transit Time |
| 17 | Uti_Cus_D | Staff Utilisation — Customs Dublin |
| 18 | Uti_DAFM_D | Staff Utilisation — DAFM Dublin |
| 19 | Uti_Cus_R | Staff Utilisation — Customs Rosslare |
| 20 | Uti_DAFM_R | Staff Utilisation — DAFM Rosslare |

---

## 2. Step-by-Step Pipeline

### Step 1 — Environment Setup

Create the following folder structure in your Cursor project:

```
project/
  ├── data/
  │     └── NOLHC_Designs_-_AL_Students.xlsx
  ├── outputs/
  │     ├── pipeline_results.xlsx
  │     └── figures/
  ├── pipeline.py          ← main orchestration script
  ├── models.py            ← model definitions & hyperparameter grids
  ├── evaluation.py        ← metrics, t-tests, conformal prediction
  └── report.py            ← Excel report generation
```

**Install required packages:**

```bash
pip install pandas numpy scikit-learn xgboost lightgbm catboost scipy openpyxl matplotlib seaborn
```

| Package | Version | Purpose |
|---|---|---|
| pandas | >=1.5 | Data loading and manipulation |
| numpy | >=1.23 | Numerical computation |
| scikit-learn | >=1.1 | 17 sklearn models + CV utilities |
| xgboost | >=1.7 | XGBoost regressor |
| lightgbm | >=3.3 | LightGBM regressor |
| catboost | >=1.1 | CatBoost regressor |
| scipy | >=1.9 | Paired t-test (scipy.stats.ttest_rel) |
| openpyxl | >=3.0 | Excel report generation |
| matplotlib | >=3.6 | Heatmap figures |
| seaborn | >=0.12 | Styled heatmaps |

---

### Step 2 — Data Loading & Parsing

Load and parse both sheets. Both have a 3-row header; data starts at row 4 (0-indexed row 3).

**Parsing logic for ExpValues:**
- Row index 0 — group labels (e.g., Shifts in Trade Volume, Customs Expertise)
- Row index 1 — full English descriptions of each sub-variable
- Row index 2 — short variable codes (NA_Im, NA_Ex, A_Im, etc.) → use as column names
- Row index 3+ — numeric data rows
- Column 0 is the Run index (1–129), drop it
- Some short codes repeat; deduplicate by appending `_2`, `_3`, `_4` suffix

**Parsing logic for SimResults:**
- Row index 0 — group labels (Agri Products, Non-Agri, Routes, Staff Utilisation)
- Row index 1 — sub-group labels (Outbound, Inbound, Dublin, Rosslare)
- Row index 2 — variable short codes → use as column names
- Row index 3+ — numeric data rows
- Column 0 is the Run index, drop it

> **CRITICAL:** After parsing, assert that both DataFrames have exactly 129 rows and no NaN values in feature or target columns. Drop any rows with NaNs before splitting.

---

### Step 3 — Train/Test Split (Strict 80/20)

This is the most critical data integrity step. The 20% test set must be completely isolated from all training, validation, and hyperparameter selection.

**Split procedure:**
1. Set random seed: `np.random.seed(42)`
2. Shuffle all 129 row indices
3. Take first 80% (103 rows) as `train_idx`, remaining 20% (26 rows) as `test_idx`
4. Create `X_train`, `Y_train` from `train_idx`
5. Create `X_test`, `Y_test` from `test_idx`
6. Store `X_test` and `Y_test` in separate variables — do NOT use in any CV or training step

> **WARNING:** Never pass `X_test` or `Y_test` into any cross-validation, `StandardScaler.fit()`, or hyperparameter search. Fitting a scaler on test data = data leakage.

**Scaling strategy:**
- Fit `StandardScaler` ONLY on `X_train`
- Transform `X_train` using `scaler.fit_transform(X_train)`
- Transform `X_test` using `scaler.transform(X_test)` — fit already done on train
- Models requiring scaled features: GPR, SVR, KNN, MLP, Ridge, Lasso, ElasticNet, BayesianRidge, PolynomialRegression
- Tree-based models (RF, ET, GB, AdaBoost, XGB, LGBM, CatBoost) use raw unscaled features

---

### Step 4 — Model Definitions & Hyperparameter Grids

Define all 19 models with their associated hyperparameter search grids. Use `ParameterGrid` from sklearn for grid enumeration.

| # | Model Name | Class | Key Hyperparameters |
|---|---|---|---|
| 1 | GPR_RBF | `GaussianProcessRegressor(RBF+WhiteKernel)` | `alpha: [1e-10, 1e-6, 1e-3]` |
| 2 | GPR_Matern | `GaussianProcessRegressor(Matern nu=1.5)` | `alpha: [1e-10, 1e-6, 1e-3]` |
| 3 | RandomForest | `RandomForestRegressor` | `n_estimators: [50,100,200]`, `max_depth: [None,5,10]`, `min_samples_split: [2,5]` |
| 4 | ExtraTrees | `ExtraTreesRegressor` | `n_estimators: [50,100,200]`, `max_depth: [None,5,10]`, `min_samples_split: [2,5]` |
| 5 | GradientBoosting | `GradientBoostingRegressor` | `n_estimators: [50,100]`, `learning_rate: [0.05,0.1,0.2]`, `max_depth: [3,5]` |
| 6 | AdaBoost | `AdaBoostRegressor` | `n_estimators: [50,100,200]`, `learning_rate: [0.5,1.0]` |
| 7 | XGBoost | `xgboost.XGBRegressor` | `n_estimators: [50,100]`, `learning_rate: [0.05,0.1]`, `max_depth: [3,5,7]` |
| 8 | LightGBM | `lightgbm.LGBMRegressor` | `n_estimators: [50,100]`, `learning_rate: [0.05,0.1]`, `num_leaves: [15,31]` |
| 9 | CatBoost | `catboost.CatBoostRegressor` | `iterations: [50,100]`, `learning_rate: [0.05,0.1]`, `depth: [4,6]` |
| 10 | SVR_RBF | `SVR(kernel='rbf')` | `C: [0.1,1,10,100]`, `epsilon: [0.01,0.1,0.5]`, `gamma: ['scale','auto']` |
| 11 | SVR_Poly | `SVR(kernel='poly')` | `C: [0.1,1,10]`, `degree: [2,3]`, `epsilon: [0.01,0.1]` |
| 12 | PolynomialReg_deg2 | `Pipeline(PolynomialFeatures(2)+Ridge)` | `alpha: [0.001,0.01,0.1,1,10]` |
| 13 | PolynomialReg_deg3 | `Pipeline(PolynomialFeatures(3)+Ridge)` | `alpha: [0.001,0.01,0.1,1,10]` |
| 14 | Ridge | `Ridge` | `alpha: [0.001,0.01,0.1,1,10,100]` |
| 15 | Lasso | `Lasso` | `alpha: [0.0001,0.001,0.01,0.1,1]` |
| 16 | ElasticNet | `ElasticNet` | `alpha: [0.001,0.01,0.1,1]`, `l1_ratio: [0.2,0.5,0.8]` |
| 17 | BayesianRidge | `BayesianRidge` | `alpha_1: [1e-6,1e-5]`, `alpha_2: [1e-6,1e-5]`, `lambda_1: [1e-6,1e-5]` |
| 18 | KNN | `KNeighborsRegressor` | `n_neighbors: [3,5,7,10,15]`, `weights: ['uniform','distance']`, `p: [1,2]` |
| 19 | MLP | `MLPRegressor` | `hidden_layer_sizes: [(50,),(100,),(50,50)]`, `alpha: [0.0001,0.001]`, `max_iter: [500]` |

> **NOTE:** For GPR models, limit the grid to `alpha` only — kernel parameters are learned during fitting via `n_restarts_optimizer=2`.

---

### Step 5 — 5-Fold Cross-Validation on Training Set

For each of the 20 target variables and each of the 19 models, perform 5-fold CV on the 80% training data to evaluate every hyperparameter combination.

**CV procedure (per target, per model):**
1. Create `KFold(n_splits=5, shuffle=True, random_state=42)`
2. For each hyperparameter combination in the model's grid:
   - For each fold (k = 1..5):
     - Split `X_train` / `y_train` into fold-train and fold-validation sets
     - If model needs scaling: fit scaler on fold-train only, transform fold-val
     - Fit model on fold-train data
     - Predict on fold-val
     - Compute RMSE: `sqrt(mean_squared_error(y_val, y_pred))`
   - After 5 folds: record `[rmse_fold1, rmse_fold2, ..., rmse_fold5]`
   - Compute: `mean_rmse = np.mean(fold_rmses)`, `std_rmse = np.std(fold_rmses)`
3. Select best hyperparameter set: lowest `mean_rmse`; break ties by lowest `std_rmse`
4. Store: `best_params`, `best_mean_rmse`, `best_std_rmse`, `fold_rmses` for best params

**Data storage structure:**

```python
cv_results[target_name][model_name] = {
    'best_params': dict,   # e.g. {'n_estimators': 100, 'max_depth': 5}
    'mean_rmse':   float,  # mean RMSE across 5 folds
    'std_rmse':    float,  # std  RMSE across 5 folds
    'fold_rmses':  list,   # [rmse_fold1, ..., rmse_fold5] for best params
}
```

> **IMPORTANT:** Save `fold_rmses` for the best hyperparameter config. These 5 values per model per target will be used directly in the paired t-test in Step 8.

---

#### experimenting_ml — generated artefacts & scripts (this repo)

After CV, companion outputs and commands live under `experimenting_ml/`:

| Artefact | Path / command |
|---|---|
| Full CV JSON (all targets × models, `best_params`, `fold_rmses`) | `experimenting_ml/outputs/cv_results.json` |
| Long CSV (380 rows: every target × model + best params) | `experimenting_ml/outputs/cv_best_hyperparameters_long.csv` |
| **Readable Markdown summary** (best single model per target by mean CV RMSE + params) | `experimenting_ml/docs/CV_Best_Models_Per_Target.md` — regenerate with `python generate_cv_summary_md.py` |
| Paired t-tests (171 pairs × 20 targets) | `experimenting_ml/outputs/paired_ttests_all_targets.csv` — `python run_paired_ttests.py` |
| Final fitted models (Step 6) | `experimenting_ml/outputs/trained_models/` — `python run_step6_retrain.py` (writes `scaler.joblib`, `split_meta.json`, and one `*.joblib` regressor per target/model) |
| Test metrics (Step 7) | `experimenting_ml/outputs/test_results.json`, `test_results.csv` — `python run_step7_9_evaluate.py` |
| Conformal summaries (Step 9) | `experimenting_ml/outputs/conformal_results.json`, `conformal_results.csv` — same script as Step 7 |
| Excel report (Step 10) | `experimenting_ml/outputs/pipeline_results.xlsx` — `python run_step10_report.py` (requires CV, paired t-tests, test/conformal JSON, and `paired_ttests_all_targets.csv`) |
| **Selected model vs test actuals** | `selected_model_test_predictions.csv` + `selected_model_test_summary.csv` — `python run_selected_model_test_predictions.py` (26 holdout rows × 20 targets; **only** the `Model_Selection` winner per target). |

**Holdout use (clarity):** The 20% test split is **not** used for training or CV. Step 7 **does** evaluate **every** model on that holdout for reporting and (in the current composite rule) for model selection. For a table that matches “chosen model only: predicted vs actual on the unseen 26 runs,” use the two `selected_model_*` CSVs above.

Use the **same** random seed (**42**) and 80/20 split for `run_step1_cv.py`, `run_step6_retrain.py`, and any test-set evaluation so indices stay aligned (`split_meta.json` records `train_idx` / `test_idx`).

---

### Step 6 — Final Training on Full 80% Training Set

After CV selects the best hyperparameters, retrain each model from scratch on the entire training set (all 103 rows) using those best hyperparameters.

**Training procedure:**
1. For each target variable (20 targets):
   - Extract `y_train` for this target
   - For each model (19 models):
     - Retrieve `best_params` from `cv_results[target][model]`
     - Instantiate fresh model with `best_params`
     - If model requires scaling: use the scaler already fitted on `X_train` from Step 3
     - Call `model.fit(X_train_scaled, y_train)` (or `X_train_raw` for tree models)
     - Store fitted model in `trained_models[target][model]`

> **CRITICAL:** Do NOT refit the scaler at this step. Use the scaler already fitted on full `X_train` in Step 3.

---

### Step 7 — Test Set Evaluation

Now unlock the 20% test set. Use each trained model to predict on `X_test`. Compute three metrics per model per target.

| Metric | Formula | Interpretation |
|---|---|---|
| RMSE | `sqrt(mean((y_true - y_pred)²))` | Lower = better. Same units as target. |
| MAE | `mean(\|y_true - y_pred\|)` | Lower = better. Robust to outliers. |
| R² | `1 - SS_res / SS_tot` | Higher = better. 1.0 = perfect fit. |

**Test evaluation procedure:**

```python
for target in target_names:
    for model in model_names:
        y_pred   = trained_models[target][model].predict(X_test_scaled)
        rmse     = sqrt(mean_squared_error(y_test_target, y_pred))
        mae      = mean_absolute_error(y_test_target, y_pred)
        r2       = r2_score(y_test_target, y_pred)
        residuals = y_test_target - y_pred   # store for conformal prediction

        test_results[target][model] = {
            'rmse': rmse, 'mae': mae, 'r2': r2,
            'y_pred': y_pred, 'residuals': residuals
        }
```

---

### Step 8 — Pairwise Paired t-test

For each target variable, perform a round-robin paired t-test comparing every pair of models using their 5 CV fold RMSE scores. With 19 models, there are **C(19,2) = 171 unique pairs**.

**Why CV fold RMSEs?** The paired t-test requires matched observations. Since both models in a pair share the same 5 fold splits, the fold RMSE scores are naturally paired — one score per fold per model.

**Procedure:**

```python
from itertools import combinations
from scipy.stats import ttest_rel

for target in target_names:
    pairs_rows = []
    matrix = pd.DataFrame(index=model_names, columns=model_names, dtype=float)

    for model_i, model_j in combinations(model_names, 2):
        rmses_i = cv_results[target][model_i]['fold_rmses']  # 5 values
        rmses_j = cv_results[target][model_j]['fold_rmses']  # 5 values

        t_stat, p_value = ttest_rel(rmses_i, rmses_j)
        significant = p_value < 0.05
        better = model_i if np.mean(rmses_i) < np.mean(rmses_j) else model_j

        matrix.loc[model_i, model_j] = p_value
        matrix.loc[model_j, model_i] = p_value

        pairs_rows.append({
            'Model_A': model_i, 'Model_B': model_j,
            'Mean_RMSE_A': np.mean(rmses_i), 'Mean_RMSE_B': np.mean(rmses_j),
            't_stat': t_stat, 'p_value': p_value,
            'Significant': significant, 'Better_Model': better
        })

    ttest_results[target] = {
        'pairs_df':  pd.DataFrame(pairs_rows),
        'matrix_df': matrix   # 19×19 p-value matrix; diagonal = NaN
    }
```

> **NOTE:** `p_value < 0.05` means the performance difference is statistically significant. A lower mean RMSE in the better model with `p < 0.05` is strong evidence for model superiority.

---

### Step 9 — Conformal Prediction (Adaptive Coverage)

Rather than a fixed coverage level, calibrate coverage based on each model's test RMSE relative to the best model for that target.

**Coverage calibration logic:**

```python
best_rmse = min(test_results[target][m]['rmse'] for m in model_names)

for model in model_names:
    relative_error = test_results[target][model]['rmse'] / best_rmse

    if   relative_error <= 1.05:  coverage = 0.90   # very close to best
    elif relative_error <= 1.20:  coverage = 0.95   # slightly worse
    else:                         coverage = 0.99   # much worse → wider interval
```

**Conformal interval procedure:**

```python
for target in target_names:
    for model in model_names:
        y_pred    = test_results[target][model]['y_pred']
        residuals = test_results[target][model]['residuals']

        scores = np.abs(residuals)                      # nonconformity scores
        q      = np.quantile(scores, coverage)          # conformal quantile

        lower = y_pred - q
        upper = y_pred + q

        empirical_coverage = np.mean(
            (y_test_target >= lower) & (y_test_target <= upper)
        )

        conformal_results[target][model] = {
            'coverage_level':    coverage,
            'quantile':          q,
            'empirical_coverage': empirical_coverage,
            'interval_width':    2 * q
        }
```

> **NOTE:** This is split conformal prediction (inductive CP). Nonconformity scores are computed on the test set. With only 26 test points, this is an acceptable approximation. For production, use a dedicated calibration set.

---

### Step 10 — Excel Report Generation

Generate a fully formatted Excel workbook using `openpyxl`.

**Sheet structure:**

| Sheet Name | Contents |
|---|---|
| Summary | Overall best model per target; ranked leaderboard by mean test RMSE |
| CV_Results | Per target + model: best_params, mean CV RMSE, std CV RMSE |
| Test_Results | Per target + model: RMSE, MAE, R² with green-yellow-red color scale |
| Target_01_TT_OB_Agri | Pairwise t-test table (171 rows) + 19×19 p-value matrix |
| Target_02_WT_OB_A_GB-Dub | Pairwise t-test table + 19×19 p-value matrix |
| ... (one sheet per target) | ... |
| Target_20_Uti_DAFM_R | Pairwise t-test table + 19×19 p-value matrix |
| Conformal_Prediction | Per target × model: coverage level, quantile, empirical coverage, width |
| Model_Selection | Final recommended model per target with composite score |

**Formatting requirements:**
- Header rows: dark blue fill `#1F4E79`, white bold text
- Alternating row shading: white and light grey `#F2F2F2`
- Test_Results sheet: `ColorScaleRule` green→yellow→red on RMSE columns per target
- p-value matrix: `ColorScaleRule` dark blue (p=0) → white (p=1); bold red text for p < 0.05
- Significant pairs in pairwise table: highlight row light yellow if p < 0.05
- Model_Selection sheet: highlight best model row in green
- All numeric cells: 4 decimal places
- Auto-fit column widths to content
- Freeze top row on all sheets

---

## 3. Model Selection Strategy

### 3.1 Selection Criteria

For each of the 20 target variables, the best model is selected using a composite scoring approach:

| Criterion | Weight | Metric | Rule |
|---|---|---|---|
| CV Stability | 40% | Mean CV RMSE + Std CV RMSE | Lower mean + lower std = better generalisation |
| Test Performance | 40% | Test RMSE, MAE, R² | Lower RMSE, lower MAE, higher R² |
| Statistical Significance | 20% | Paired t-test wins vs. others | Count of significant wins (p<0.05) |

### 3.2 Composite Score Formula

```python
# Normalise each metric to [0,1] across models for a given target
norm_cv_rmse   = (cv_rmse   - min_cv)   / (max_cv   - min_cv   + 1e-10)
norm_test_rmse = (test_rmse - min_test) / (max_test - min_test + 1e-10)

composite_score = (0.4 * (1 - norm_cv_rmse)
                 + 0.4 * (1 - norm_test_rmse)
                 + 0.2 * (ttest_wins / 18))   # fraction of 18 pairwise wins

# Select model with highest composite score
best_model = max(composite_scores, key=composite_scores.get)
```

### 3.3 Tiebreaker Rules

1. If two models have composite scores within 0.01: prefer lower CV std (more stable)
2. If still tied: prefer simpler model (Ridge > RandomForest > GBM > GPR)
3. If GPR wins: verify prediction intervals via conformal coverage before finalising

### 3.4 Model_Selection Sheet Columns

| Column | Description |
|---|---|
| Target | Target variable name |
| Best_Model | Name of the selected model |
| CV_Mean_RMSE | Cross-validation mean RMSE (best params) |
| CV_Std_RMSE | Cross-validation RMSE standard deviation |
| Test_RMSE | RMSE on held-out 20% test set |
| Test_MAE | MAE on held-out 20% test set |
| Test_R2 | R² on held-out 20% test set |
| TTest_Wins | Number of significant pairwise t-test wins (p<0.05) |
| Composite_Score | Weighted composite score (0–1) |
| Conformal_Coverage | Adaptive coverage level assigned |
| Empirical_Coverage | Observed coverage fraction on test set |
| Interval_Width | Mean prediction interval width |
| Justification | Short text: why this model was selected |

---

## 4. Code Architecture

### 4.1 `models.py` — Model Definitions

```python
# models.py
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, Matern, WhiteKernel, ConstantKernel
from sklearn.ensemble import (RandomForestRegressor, ExtraTreesRegressor,
                               GradientBoostingRegressor, AdaBoostRegressor)
from sklearn.svm import SVR
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge, Lasso, ElasticNet, BayesianRidge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor

# Models that require StandardScaler on features
NEEDS_SCALING = {
    'GPR_RBF', 'GPR_Matern', 'SVR_RBF', 'SVR_Poly',
    'PolynomialReg_deg2', 'PolynomialReg_deg3',
    'Ridge', 'Lasso', 'ElasticNet', 'BayesianRidge', 'KNN', 'MLP'
}

def get_models():
    return {
        'GPR_RBF': {
            'model': GaussianProcessRegressor(
                kernel=ConstantKernel(1.0) * RBF(1.0) + WhiteKernel(1e-3),
                normalize_y=True, n_restarts_optimizer=2, random_state=42
            ),
            'grid': [{'alpha': [1e-10, 1e-6, 1e-3]}]
        },
        'GPR_Matern': {
            'model': GaussianProcessRegressor(
                kernel=ConstantKernel(1.0) * Matern(nu=1.5) + WhiteKernel(1e-3),
                normalize_y=True, n_restarts_optimizer=2, random_state=42
            ),
            'grid': [{'alpha': [1e-10, 1e-6, 1e-3]}]
        },
        'RandomForest': {
            'model': RandomForestRegressor(random_state=42),
            'grid': [{'n_estimators': [50, 100, 200],
                      'max_depth': [None, 5, 10],
                      'min_samples_split': [2, 5]}]
        },
        'ExtraTrees': {
            'model': ExtraTreesRegressor(random_state=42),
            'grid': [{'n_estimators': [50, 100, 200],
                      'max_depth': [None, 5, 10],
                      'min_samples_split': [2, 5]}]
        },
        'GradientBoosting': {
            'model': GradientBoostingRegressor(random_state=42),
            'grid': [{'n_estimators': [50, 100],
                      'learning_rate': [0.05, 0.1, 0.2],
                      'max_depth': [3, 5]}]
        },
        'AdaBoost': {
            'model': AdaBoostRegressor(random_state=42),
            'grid': [{'n_estimators': [50, 100, 200],
                      'learning_rate': [0.5, 1.0]}]
        },
        'XGBoost': {
            'model': xgb.XGBRegressor(random_state=42, verbosity=0),
            'grid': [{'n_estimators': [50, 100],
                      'learning_rate': [0.05, 0.1],
                      'max_depth': [3, 5, 7]}]
        },
        'LightGBM': {
            'model': lgb.LGBMRegressor(random_state=42, verbose=-1),
            'grid': [{'n_estimators': [50, 100],
                      'learning_rate': [0.05, 0.1],
                      'num_leaves': [15, 31]}]
        },
        'CatBoost': {
            'model': CatBoostRegressor(random_state=42, verbose=0),
            'grid': [{'iterations': [50, 100],
                      'learning_rate': [0.05, 0.1],
                      'depth': [4, 6]}]
        },
        'SVR_RBF': {
            'model': SVR(kernel='rbf'),
            'grid': [{'C': [0.1, 1, 10, 100],
                      'epsilon': [0.01, 0.1, 0.5],
                      'gamma': ['scale', 'auto']}]
        },
        'SVR_Poly': {
            'model': SVR(kernel='poly'),
            'grid': [{'C': [0.1, 1, 10],
                      'degree': [2, 3],
                      'epsilon': [0.01, 0.1]}]
        },
        'PolynomialReg_deg2': {
            'model': Pipeline([('poly', PolynomialFeatures(degree=2)),
                               ('ridge', Ridge())]),
            'grid': [{'ridge__alpha': [0.001, 0.01, 0.1, 1, 10]}]
        },
        'PolynomialReg_deg3': {
            'model': Pipeline([('poly', PolynomialFeatures(degree=3)),
                               ('ridge', Ridge())]),
            'grid': [{'ridge__alpha': [0.001, 0.01, 0.1, 1, 10]}]
        },
        'Ridge': {
            'model': Ridge(),
            'grid': [{'alpha': [0.001, 0.01, 0.1, 1, 10, 100]}]
        },
        'Lasso': {
            'model': Lasso(max_iter=5000),
            'grid': [{'alpha': [0.0001, 0.001, 0.01, 0.1, 1]}]
        },
        'ElasticNet': {
            'model': ElasticNet(max_iter=5000),
            'grid': [{'alpha': [0.001, 0.01, 0.1, 1],
                      'l1_ratio': [0.2, 0.5, 0.8]}]
        },
        'BayesianRidge': {
            'model': BayesianRidge(),
            'grid': [{'alpha_1': [1e-6, 1e-5],
                      'alpha_2': [1e-6, 1e-5],
                      'lambda_1': [1e-6, 1e-5]}]
        },
        'KNN': {
            'model': KNeighborsRegressor(),
            'grid': [{'n_neighbors': [3, 5, 7, 10, 15],
                      'weights': ['uniform', 'distance'],
                      'p': [1, 2]}]
        },
        'MLP': {
            'model': MLPRegressor(random_state=42),
            'grid': [{'hidden_layer_sizes': [(50,), (100,), (50, 50)],
                      'alpha': [0.0001, 0.001],
                      'max_iter': [500]}]
        },
    }
```

---

### 4.2 `pipeline.py` — Main Orchestration

```python
# pipeline.py
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from collections import Counter
from itertools import combinations

from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import ParameterGrid
from scipy.stats import ttest_rel

from models import get_models, NEEDS_SCALING
from evaluation import compute_conformal, compute_composite_score
from report import generate_excel_report

# ── LOAD DATA ────────────────────────────────────────────────────────────────
FILE = 'data/NOLHC_Designs_-_AL_Students.xlsx'
df_exp_raw = pd.read_excel(FILE, sheet_name='ExpValues', header=None)
df_sim_raw = pd.read_excel(FILE, sheet_name='SimResults', header=None)

# Build unique feature column names from row 2 short codes
row1 = df_exp_raw.iloc[1].tolist()
row2 = df_exp_raw.iloc[2].tolist()
cols_raw = []
for i, (r1, r2) in enumerate(zip(row1, row2)):
    if i == 0:               cols_raw.append('Run')
    elif pd.notna(r2):       cols_raw.append(str(r2).strip())
    elif pd.notna(r1):       cols_raw.append(str(r1).strip()[:30])
    else:                    cols_raw.append(f'col_{i}')

seen = Counter()
unique_cols = []
for c in cols_raw:
    seen[c] += 1
    unique_cols.append(f'{c}_{seen[c]}' if seen[c] > 1 else c)

df_exp = df_exp_raw.iloc[3:].reset_index(drop=True)
df_exp.columns = unique_cols
df_exp = df_exp[df_exp['Run'].notna()].apply(pd.to_numeric, errors='coerce')

sim_cols = df_sim_raw.iloc[2].tolist()
df_sim = df_sim_raw.iloc[3:].reset_index(drop=True)
df_sim.columns = ['Run'] + sim_cols[1:]
df_sim = df_sim[df_sim['Run'].notna()].apply(pd.to_numeric, errors='coerce')

FEATURE_COLS = [c for c in df_exp.columns if c != 'Run']
TARGET_COLS  = [c for c in df_sim.columns if c != 'Run']

X_all = df_exp[FEATURE_COLS].values.astype(float)
Y_all = df_sim[TARGET_COLS].values.astype(float)

assert X_all.shape[0] == 129, "Expected 129 rows"
assert not np.isnan(X_all).any(), "NaN in features"
assert not np.isnan(Y_all).any(), "NaN in targets"

# ── SPLIT ────────────────────────────────────────────────────────────────────
np.random.seed(42)
idx = np.arange(X_all.shape[0])
np.random.shuffle(idx)
split = int(0.8 * len(idx))
train_idx, test_idx = idx[:split], idx[split:]

X_train_raw, X_test_raw = X_all[train_idx], X_all[test_idx]
Y_train,     Y_test     = Y_all[train_idx], Y_all[test_idx]

scaler = StandardScaler().fit(X_train_raw)   # fit on train ONLY
X_train_scaled = scaler.transform(X_train_raw)
X_test_scaled  = scaler.transform(X_test_raw)

# ── CV ───────────────────────────────────────────────────────────────────────
models_dict = get_models()
model_names = list(models_dict.keys())
kf = KFold(n_splits=5, shuffle=True, random_state=42)
cv_results = {t: {} for t in TARGET_COLS}

for ti, target in enumerate(TARGET_COLS):
    y_train = Y_train[:, ti]
    print(f"\n[{ti+1}/20] Target: {target}")

    for model_name, spec in models_dict.items():
        needs_scale = model_name in NEEDS_SCALING
        X_tr = X_train_scaled if needs_scale else X_train_raw

        best_mean, best_std, best_params, best_folds = np.inf, np.inf, None, None

        for params in ParameterGrid(spec['grid']):
            fold_rmses = []
            for tr_idx, val_idx in kf.split(X_tr):
                Xf_tr, Xf_val = X_tr[tr_idx], X_tr[val_idx]
                yf_tr, yf_val = y_train[tr_idx], y_train[val_idx]

                # For scaled models, refit scaler on fold-train to avoid leakage
                if needs_scale:
                    fold_scaler = StandardScaler().fit(X_train_raw[tr_idx])
                    Xf_tr  = fold_scaler.transform(X_train_raw[tr_idx])
                    Xf_val = fold_scaler.transform(X_train_raw[val_idx])

                m = spec['model'].__class__(**{**spec['model'].get_params(), **params})
                m.fit(Xf_tr, yf_tr)
                pred = m.predict(Xf_val)
                fold_rmses.append(np.sqrt(mean_squared_error(yf_val, pred)))

            mean_r = np.mean(fold_rmses)
            std_r  = np.std(fold_rmses)
            if mean_r < best_mean or (mean_r == best_mean and std_r < best_std):
                best_mean, best_std, best_params, best_folds = mean_r, std_r, params, fold_rmses

        cv_results[target][model_name] = {
            'best_params': best_params,
            'mean_rmse':   best_mean,
            'std_rmse':    best_std,
            'fold_rmses':  best_folds,
        }
        print(f"  {model_name}: mean_rmse={best_mean:.4f} std={best_std:.4f} params={best_params}")

# ── FINAL TRAINING ───────────────────────────────────────────────────────────
trained_models = {t: {} for t in TARGET_COLS}

for ti, target in enumerate(TARGET_COLS):
    y_train = Y_train[:, ti]
    for model_name, spec in models_dict.items():
        best_params = cv_results[target][model_name]['best_params']
        needs_scale = model_name in NEEDS_SCALING
        X_tr = X_train_scaled if needs_scale else X_train_raw

        m = spec['model'].__class__(**{**spec['model'].get_params(), **best_params})
        m.fit(X_tr, y_train)
        trained_models[target][model_name] = m

# ── TEST EVALUATION ──────────────────────────────────────────────────────────
test_results = {t: {} for t in TARGET_COLS}

for ti, target in enumerate(TARGET_COLS):
    y_true = Y_test[:, ti]
    for model_name in model_names:
        needs_scale = model_name in NEEDS_SCALING
        X_te = X_test_scaled if needs_scale else X_test_raw

        y_pred    = trained_models[target][model_name].predict(X_te)
        residuals = y_true - y_pred

        test_results[target][model_name] = {
            'rmse':      np.sqrt(mean_squared_error(y_true, y_pred)),
            'mae':       mean_absolute_error(y_true, y_pred),
            'r2':        r2_score(y_true, y_pred),
            'y_pred':    y_pred,
            'residuals': residuals,
        }

# ── PAIRED T-TEST ────────────────────────────────────────────────────────────
ttest_results = {}

for target in TARGET_COLS:
    pairs_rows = []
    matrix = pd.DataFrame(np.nan, index=model_names, columns=model_names)

    for model_i, model_j in combinations(model_names, 2):
        ri = cv_results[target][model_i]['fold_rmses']
        rj = cv_results[target][model_j]['fold_rmses']
        t_stat, p_val = ttest_rel(ri, rj)
        sig     = p_val < 0.05
        better  = model_i if np.mean(ri) < np.mean(rj) else model_j

        matrix.loc[model_i, model_j] = p_val
        matrix.loc[model_j, model_i] = p_val

        pairs_rows.append({
            'Model_A': model_i, 'Model_B': model_j,
            'Mean_RMSE_A': np.mean(ri), 'Mean_RMSE_B': np.mean(rj),
            't_stat': t_stat, 'p_value': p_val,
            'Significant': sig, 'Better_Model': better,
        })

    ttest_results[target] = {
        'pairs_df':  pd.DataFrame(pairs_rows),
        'matrix_df': matrix,
    }

# ── CONFORMAL + MODEL SELECTION ──────────────────────────────────────────────
from evaluation import compute_conformal, compute_composite_score

conformal_results = {t: {} for t in TARGET_COLS}
selection_rows    = []

for ti, target in enumerate(TARGET_COLS):
    y_true    = Y_test[:, ti]
    best_rmse = min(test_results[target][m]['rmse'] for m in model_names)

    cv_rmses   = [cv_results[target][m]['mean_rmse'] for m in model_names]
    test_rmses = [test_results[target][m]['rmse']    for m in model_names]

    composite_scores = {}
    for model_name in model_names:
        conf = compute_conformal(
            y_true,
            test_results[target][model_name]['y_pred'],
            test_results[target][model_name]['rmse'],
            best_rmse
        )
        conformal_results[target][model_name] = conf

        wins = sum(
            1 for _, row in ttest_results[target]['pairs_df'].iterrows()
            if row['Significant'] and row['Better_Model'] == model_name
        )
        score = compute_composite_score(
            cv_results[target][model_name]['mean_rmse'],
            test_results[target][model_name]['rmse'],
            wins, cv_rmses, test_rmses
        )
        composite_scores[model_name] = score

    best_model = max(composite_scores, key=composite_scores.get)
    tr = test_results[target][best_model]
    cr = conformal_results[target][best_model]
    selection_rows.append({
        'Target': target, 'Best_Model': best_model,
        'CV_Mean_RMSE': cv_results[target][best_model]['mean_rmse'],
        'CV_Std_RMSE':  cv_results[target][best_model]['std_rmse'],
        'Test_RMSE': tr['rmse'], 'Test_MAE': tr['mae'], 'Test_R2': tr['r2'],
        'TTest_Wins': composite_scores[best_model],
        'Composite_Score': composite_scores[best_model],
        'Conformal_Coverage': cr['coverage_level'],
        'Empirical_Coverage': cr['empirical_coverage'],
        'Interval_Width': cr['interval_width'],
    })

selection_df = pd.DataFrame(selection_rows)

# ── GENERATE REPORT ──────────────────────────────────────────────────────────
generate_excel_report(
    cv_results, test_results, ttest_results,
    conformal_results, selection_df,
    TARGET_COLS, model_names,
    output_path='outputs/pipeline_results.xlsx'
)
print("\nDone. Results saved to outputs/pipeline_results.xlsx")
```

---

### 4.3 `evaluation.py` — Metrics & Conformal Logic

```python
# evaluation.py
import numpy as np

def compute_conformal(y_true, y_pred, test_rmse, best_rmse):
    """Adaptive conformal prediction intervals."""
    relative_error = test_rmse / best_rmse

    if   relative_error <= 1.05:  coverage = 0.90
    elif relative_error <= 1.20:  coverage = 0.95
    else:                         coverage = 0.99

    scores           = np.abs(y_true - y_pred)
    q                = np.quantile(scores, coverage)
    lower, upper     = y_pred - q, y_pred + q
    empirical        = np.mean((y_true >= lower) & (y_true <= upper))

    return {
        'coverage_level':     coverage,
        'quantile':           q,
        'empirical_coverage': empirical,
        'interval_width':     2 * q,
    }


def compute_composite_score(cv_rmse, test_rmse, ttest_wins,
                             all_cv_rmses, all_test_rmses):
    """Weighted composite score for model selection."""
    eps = 1e-10
    norm_cv   = (cv_rmse   - min(all_cv_rmses))   / (max(all_cv_rmses)   - min(all_cv_rmses)   + eps)
    norm_test = (test_rmse - min(all_test_rmses)) / (max(all_test_rmses) - min(all_test_rmses) + eps)
    return 0.4 * (1 - norm_cv) + 0.4 * (1 - norm_test) + 0.2 * (ttest_wins / 18)
```

---

### 4.4 `report.py` — Excel Report

```python
# report.py
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.utils import get_column_letter
import pandas as pd

HEADER_FILL  = PatternFill('solid', fgColor='1F4E79')
ALT_FILL     = PatternFill('solid', fgColor='F2F2F2')
SIG_FILL     = PatternFill('solid', fgColor='FFF2CC')
BEST_FILL    = PatternFill('solid', fgColor='E2EFDA')
HEADER_FONT  = Font(bold=True, color='FFFFFF', name='Arial', size=11)
NORMAL_FONT  = Font(name='Arial', size=10)
CENTER       = Alignment(horizontal='center', vertical='center', wrap_text=True)

def style_header(ws, row, n_cols):
    for col in range(1, n_cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill, cell.font, cell.alignment = HEADER_FILL, HEADER_FONT, CENTER

def write_df(ws, df, start_row=1, highlight_sig=False, highlight_best_col=None):
    # Write headers
    for ci, col in enumerate(df.columns, 1):
        ws.cell(row=start_row, column=ci, value=col)
    style_header(ws, start_row, len(df.columns))

    # Write data rows
    for ri, (_, row_data) in enumerate(df.iterrows(), start_row + 1):
        fill = ALT_FILL if ri % 2 == 0 else PatternFill()
        for ci, val in enumerate(row_data, 1):
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.font = NORMAL_FONT
            cell.alignment = CENTER
            if isinstance(val, float):
                cell.number_format = '0.0000'
        if highlight_sig and row_data.get('Significant'):
            for ci in range(1, len(df.columns) + 1):
                ws.cell(row=ri, column=ci).fill = SIG_FILL

def autofit_columns(ws):
    for col in ws.columns:
        max_len = max((len(str(c.value or '')) for c in col), default=0)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)

def generate_excel_report(cv_results, test_results, ttest_results,
                           conformal_results, selection_df,
                           target_names, model_names, output_path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # ── Model_Selection sheet ────────────────────────────────────────────────
    ws = wb.create_sheet('Model_Selection')
    write_df(ws, selection_df)
    # Highlight best model rows in green
    for ri in range(2, len(selection_df) + 2):
        for ci in range(1, len(selection_df.columns) + 1):
            ws.cell(row=ri, column=ci).fill = BEST_FILL
    ws.freeze_panes = 'A2'
    autofit_columns(ws)

    # ── Summary sheet ────────────────────────────────────────────────────────
    ws = wb.create_sheet('Summary')
    summary_df = selection_df[['Target','Best_Model','CV_Mean_RMSE','Test_RMSE','Test_R2','Composite_Score']]
    write_df(ws, summary_df)
    ws.freeze_panes = 'A2'
    autofit_columns(ws)

    # ── CV_Results sheet ─────────────────────────────────────────────────────
    ws = wb.create_sheet('CV_Results')
    cv_rows = []
    for target in target_names:
        for model in model_names:
            r = cv_results[target][model]
            cv_rows.append({'Target': target, 'Model': model,
                            'Best_Params': str(r['best_params']),
                            'Mean_RMSE': r['mean_rmse'], 'Std_RMSE': r['std_rmse']})
    write_df(ws, pd.DataFrame(cv_rows))
    ws.freeze_panes = 'A2'
    autofit_columns(ws)

    # ── Test_Results sheet ───────────────────────────────────────────────────
    ws = wb.create_sheet('Test_Results')
    test_rows = []
    for target in target_names:
        for model in model_names:
            r = test_results[target][model]
            test_rows.append({'Target': target, 'Model': model,
                              'RMSE': r['rmse'], 'MAE': r['mae'], 'R2': r['r2']})
    test_df = pd.DataFrame(test_rows)
    write_df(ws, test_df)
    # Color scale on RMSE column (col 3)
    last_row = len(test_df) + 1
    ws.conditional_formatting.add(
        f'C2:C{last_row}',
        ColorScaleRule(start_type='min', start_color='63BE7B',
                       mid_type='percentile', mid_value=50, mid_color='FFEB84',
                       end_type='max', end_color='F8696B')
    )
    ws.freeze_panes = 'A2'
    autofit_columns(ws)

    # ── Per-target t-test sheets ──────────────────────────────────────────────
    for ti, target in enumerate(target_names):
        sheet_name = f'Target_{ti+1:02d}_{target}'[:31]
        ws = wb.create_sheet(sheet_name)

        # Pairwise table
        ws.cell(row=1, column=1, value='PAIRWISE PAIRED T-TEST RESULTS')
        ws.cell(row=1, column=1).font = Font(bold=True, name='Arial', size=12, color='1F4E79')
        write_df(ws, ttest_results[target]['pairs_df'], start_row=2, highlight_sig=True)

        # 19x19 p-value matrix (offset below the table)
        offset = len(ttest_results[target]['pairs_df']) + 5
        ws.cell(row=offset, column=1, value='P-VALUE MATRIX (19x19)')
        ws.cell(row=offset, column=1).font = Font(bold=True, name='Arial', size=12, color='1F4E79')

        matrix_df = ttest_results[target]['matrix_df']
        # Write column headers
        for ci, col in enumerate(model_names, 2):
            ws.cell(row=offset+1, column=ci, value=col).font = Font(bold=True, name='Arial', size=9)
        for ri, row_model in enumerate(model_names, offset+2):
            ws.cell(row=ri, column=1, value=row_model).font = Font(bold=True, name='Arial', size=9)
            for ci, col_model in enumerate(model_names, 2):
                val = matrix_df.loc[row_model, col_model]
                cell = ws.cell(row=ri, column=ci, value=val)
                cell.number_format = '0.0000'
                cell.font = Font(name='Arial', size=9,
                                 bold=(not pd.isna(val) and val < 0.05),
                                 color=('FF0000' if not pd.isna(val) and val < 0.05 else '000000'))

        # Color scale on matrix
        mat_range = f'B{offset+2}:T{offset+2+len(model_names)}'
        ws.conditional_formatting.add(
            mat_range,
            ColorScaleRule(start_type='min', start_color='1F4E79',
                           mid_type='num', mid_value=0.05, mid_color='FFFFFF',
                           end_type='max', end_color='FFFFFF')
        )
        ws.freeze_panes = 'A2'
        autofit_columns(ws)

    # ── Conformal_Prediction sheet ───────────────────────────────────────────
    ws = wb.create_sheet('Conformal_Prediction')
    conf_rows = []
    for target in target_names:
        for model in model_names:
            c = conformal_results[target][model]
            conf_rows.append({'Target': target, 'Model': model,
                              'Coverage_Level': c['coverage_level'],
                              'Conformal_Quantile': c['quantile'],
                              'Empirical_Coverage': c['empirical_coverage'],
                              'Interval_Width': c['interval_width']})
    write_df(ws, pd.DataFrame(conf_rows))
    ws.freeze_panes = 'A2'
    autofit_columns(ws)

    wb.save(output_path)
    print(f"Excel report saved: {output_path}")
```

---

## 5. Cursor Prompts

Use these prompts in sequence in Cursor. Each one builds on the outputs of the previous.

---

### Prompt 1 — Data Loading

```
Write a Python function load_data(filepath) that loads
NOLHC_Designs_-_AL_Students.xlsx. Parse the ExpValues sheet:
skip rows 0–2 as headers, use row index 2 as column names,
column 0 is Run index (drop it). Deduplicate repeated column names
by appending _2, _3 etc. Parse SimResults sheet the same way using
row 2 as column names, drop Run column. Return X (numpy array of
features), Y (numpy array of 20 targets), feature_names (list),
target_names (list). Assert both have 129 rows and no NaN values.
```

---

### Prompt 2 — Train/Test Split & Scaler

```
Write a function split_and_scale(X, Y, test_size=0.2, random_state=42)
that: (1) shuffles indices with np.random.seed(42), (2) splits into
80% train / 20% test — never leaking test data, (3) fits StandardScaler
ONLY on X_train, (4) returns X_train_raw, X_train_scaled, X_test_raw,
X_test_scaled, Y_train, Y_test, scaler. Tree-based models will use
X_train_raw; kernel/linear models will use X_train_scaled.
```

---

### Prompt 3 — Models & Hyperparameter Grids

```
Create models.py with a function get_models() returning a dict of 19
models: GPR_RBF (RBF+WhiteKernel, alpha grid), GPR_Matern (Matern
nu=1.5, alpha grid), RandomForest, ExtraTrees, GradientBoosting,
AdaBoost, XGBoost (xgboost.XGBRegressor), LightGBM (lgb.LGBMRegressor),
CatBoost (CatBoostRegressor verbose=0), SVR_RBF, SVR_Poly,
PolynomialReg_deg2 (Pipeline of PolynomialFeatures(2)+Ridge),
PolynomialReg_deg3, Ridge, Lasso, ElasticNet, BayesianRidge, KNN, MLP.
Each entry has keys 'model' and 'grid' (list of dicts for ParameterGrid).
Also export NEEDS_SCALING as a set of model names requiring StandardScaler.
```

---

### Prompt 4 — 5-Fold CV Loop

```
Write run_cv(models_dict, X_train_raw, X_train_scaled, Y_train,
target_names, n_splits=5) that: for each target and model, iterates
over all param combinations using ParameterGrid, runs 5-fold CV
(KFold shuffle=True seed=42), computes per-fold RMSE. For scaled
models refit StandardScaler on the fold-train split only (not the
global scaler). Selects best params by lowest mean RMSE, tiebreak
= lowest std. Stores best_params, mean_rmse, std_rmse, fold_rmses
(list of 5). Returns nested dict cv_results[target][model].
Print progress per target.
```

---

### Prompt 5 — Final Training & Test Evaluation

```
Write train_and_evaluate(cv_results, models_dict, X_train_raw,
X_train_scaled, X_test_raw, X_test_scaled, Y_train, Y_test,
target_names) that: retrains each model with best_params on full
X_train (use X_train_scaled for NEEDS_SCALING models, X_train_raw
for tree models), then predicts on X_test (never on train). Returns
test_results[target][model] = {rmse, mae, r2, y_pred, residuals}.
Use sklearn mean_squared_error, mean_absolute_error, r2_score.
Never use X_test or Y_test during training.
```

---

### Prompt 6 — Paired t-test

```
Write run_paired_ttests(cv_results, target_names, model_names) that
for each target computes all 171 unique pairwise paired t-tests using
scipy.stats.ttest_rel on fold_rmses (5 values per model from CV).
Returns ttest_results[target] = {
  'pairs_df': DataFrame with columns [Model_A, Model_B, Mean_RMSE_A,
              Mean_RMSE_B, t_stat, p_value, Significant, Better_Model],
  'matrix_df': 19×19 DataFrame of p-values, model names as index/columns,
               diagonal = NaN
}
```

---

### Prompt 7 — Conformal Prediction & Model Selection

```
Write compute_conformal_and_select(test_results, ttest_results,
cv_results, target_names, model_names) that:
(1) For each target+model: compute adaptive coverage — 0.90 if
    test_rmse/best_rmse<=1.05, 0.95 if <=1.20, else 0.99. Then
    conformal quantile q=np.quantile(|residuals|, coverage),
    intervals = y_pred +/- q, empirical coverage fraction.
(2) Count ttest_wins = significant pairs (p<0.05) where this model
    is the Better_Model.
(3) Compute composite_score = 0.4*(1-norm_cv_rmse) +
    0.4*(1-norm_test_rmse) + 0.2*(wins/18), normalised per target.
(4) Select best model per target = highest composite_score.
Return conformal_results[target][model] and selection_df DataFrame
with columns: Target, Best_Model, CV_Mean_RMSE, CV_Std_RMSE,
Test_RMSE, Test_MAE, Test_R2, TTest_Wins, Composite_Score,
Conformal_Coverage, Empirical_Coverage, Interval_Width.
```

---

### Prompt 8 — Excel Report

```
Write generate_excel_report(cv_results, test_results, ttest_results,
conformal_results, selection_df, target_names, model_names, output_path)
using openpyxl that creates these sheets:
1. Model_Selection — best model per target, best rows highlighted green
2. Summary — leaderboard by test RMSE
3. CV_Results — all models × targets with best params and CV scores
4. Test_Results — RMSE/MAE/R2 with green-yellow-red ColorScaleRule on
   RMSE column
5. Target_NN_<name> (one per target) — full 171-row pairwise t-test
   table (significant rows highlighted yellow) + 19×19 p-value matrix
   with blue-white ColorScaleRule and red bold text for p<0.05
6. Conformal_Prediction — coverage, quantile, empirical coverage, width
Formatting: dark blue headers (#1F4E79) with white bold text, alternating
row shading, 4 decimal places on floats, freeze first row, auto-fit
column widths on all sheets.
```

---

## 6. Implementation Checklist

### Data & Split
- [ ] ExpValues parsed correctly (129 rows × 35 features, no NaN)
- [ ] SimResults parsed correctly (129 rows × 20 targets, no NaN)
- [ ] Duplicate column names deduplicated with `_2` `_3` `_4` suffix
- [ ] 80/20 split done with `random_state=42`
- [ ] `X_test` and `Y_test` variables never used before Step 7
- [ ] `StandardScaler` fitted ONLY on `X_train`

### Cross-Validation
- [ ] 5-fold CV with `KFold(shuffle=True, random_state=42)`
- [ ] All 19 models have hyperparameter grids defined
- [ ] Tree models use raw features; kernel/linear use scaled features
- [ ] Inside each CV fold, scaler refit on fold-train only (not global scaler)
- [ ] Best params selected by lowest mean RMSE, tiebreak = lowest std
- [ ] `fold_rmses` (5 values) stored for EACH model × target combination

### Training & Evaluation
- [ ] Final models retrained on full `X_train` with best hyperparams
- [ ] Scaler NOT refit at this stage — use scaler from Step 3
- [ ] Test RMSE, MAE, R² computed for all 19 models × 20 targets
- [ ] Residuals stored for conformal prediction

### Statistical Tests
- [ ] 171 unique pairs per target (C(19,2) = 171 confirmed)
- [ ] `scipy.stats.ttest_rel` used on `fold_rmses` (5 paired values)
- [ ] Full pairwise DataFrame + 19×19 p-value matrix per target
- [ ] `Significant` column = `True` if `p_value < 0.05`

### Conformal Prediction
- [ ] Adaptive coverage: 0.90 / 0.95 / 0.99 based on relative RMSE
- [ ] Nonconformity scores = `|y_test - y_pred|`
- [ ] Quantile `q = np.quantile(scores, coverage_level)`
- [ ] Empirical coverage computed on test set

### Excel Report
- [ ] All 10 sheet types present in workbook (summary + 20 target sheets + others)
- [ ] `ColorScaleRule` on Test_Results RMSE column
- [ ] `ColorScaleRule` on each 19×19 p-value matrix (blue→white)
- [ ] `p < 0.05` rows highlighted yellow in pairwise tables
- [ ] Best model row highlighted green in Model_Selection sheet
- [ ] First row frozen on all sheets
- [ ] Column widths auto-fitted

---

*ML Surrogate Modelling Pipeline — Specification Document v1.0 | March 2026*
