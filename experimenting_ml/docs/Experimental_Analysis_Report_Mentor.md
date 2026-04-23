# Experimental Analysis Report — NOLHC Surrogate Modelling Pipeline

**Purpose:** This document summarises the machine-learning experimentation performed on the NOLHC (Nearly Orthogonal Latin Hypercube) simulation dataset for **20 continuous target variables** (simulation outputs) predicted from **35 input design parameters**. It is intended for project review: data use, train/validation/test logic, mentor-requested analyses (Step 2 and Step 3), SHAP explainability added before conformal/final testing, statistical tests, model selection, and how results are packaged for review.

**Repository location:** `experimenting_ml/` (scripts, outputs) with data aligned to `nolhc_ml/data/processed/` (parquet) or equivalent Excel source.

---

## 1. Dataset and design


| Item                         | Value                                                                                                      |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Design runs (complete cases) | **129**                                                                                                    |
| Input features               | **35** (after dropping run index; includes 4 Cherbourg shift-volume inputs in addition to the original 31) |
| Output targets               | **20** (SimResults KPIs: transit/wait times in hours, staff utilisation as fractions)                      |
| Missing values               | **None** in processed training matrices (asserted at load)                                                 |


The inputs mix **trade volumes** (tonnes), **route-mode volumes**, **vessel capacities**, **check times**, **resource counts**, and **route-mix fractions** (0–1). Outputs are **positive continuous** quantities on different scales (e.g. long transits vs short waits vs utilisation in [0,1]).

### 1.1 Data distributions (descriptive)

Summary statistics were computed on all **129** rows for every feature and target (35 inputs, 20 outputs) (**mean, standard deviation, min, max, skewness**). Highlights relevant for modelling:

- **Scale heterogeneity:** Targets such as `TT_IB_LB`, `WT_IB_LB`, `WT_IB_NA_Dub` show **large means and standard deviations** relative to others; utilisation targets (`Uti_*`) are **bounded** near [0,1] with smaller variance.
- **Skewness:** Several wait-time and transit targets show **right-skew** (e.g. `TT_OB_Agri` skew ≈ 3.0; `WT_IB_NA_Ross` very high skew), implying a few design points produce much larger values than the bulk. **Tree ensembles and non-linear models** are partly motivated by this; **linear models** remain useful baselines on some targets.
- **Near-constant routes:** Some targets have **tight ranges** (e.g. `TT_OB_LB` mean ≈ 25.7, std ≈ 0.46 on [25,27]), so **test error will be small in absolute terms** but **R² can be fragile** when variance is low.

*Note:* No distributional assumption (e.g. normality of residuals) is required for **cross-validated RMSE**; normality is only an informal motivation for interpreting paired *t*-tests on finite CV scores.

---

## 2. Train / validation / test — what percentage, and what each means

We use a **single held-out test set** plus **cross-validation inside the training set**. There is **no third random split** labelled “validation” in addition to CV.


| Split               | Rows    | Percentage (of 129)                             | Role                                                                                                             |
| ------------------- | ------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Training pool**   | **103** | **≈ 79.8%** (implemented as `round(0.8 × 129)`) | All **model fitting**, **hyperparameter tuning**, and **scaler fitting**                                         |
| **Test (hold-out)** | **26**  | **≈ 20.2%**                                     | **Final out-of-sample** evaluation only: metrics, conformal calibration as implemented, **not** used in CV grids |


**Within the 103 training rows:**

- **Default mode (current):** `repeated10` = **10-fold × n_repeats** (typically 3 or 5) on the train pool, for more stable estimates on the small sample.
- **Legacy mode:** `kfold5` = single shuffled 5-fold pass (kept for backward compatibility / comparisons).
- This is **nested in spirit**: the **outer** 26 rows are never seen until official hold-out evaluation; the **inner** folds only see the 103-row pool.

**Randomisation:** Index permutation with `**numpy.random.RandomState(42)`** and `train_frac=0.8`. The same indices are stored in `experimenting_ml/outputs/trained_models/split_meta.json` (`train_idx`, `test_idx`) so test evaluation and any “selected model” tables are **reproducible**.

**Scaling:** `StandardScaler` is **fit only on the 103 training rows** and applied to models that need scaled features (GPR, SVR, KNN, MLP, linear/polynomial models). **Tree-based models** use **unscaled** inputs, per project spec.

---

## 3. End-to-end experimental steps (what we built)

Below is the **actual implementation order** in `experimenting_ml/`, mapped to the internal specification (`docs/ML_Pipeline_Specification.md`).

### Step A — Data loading

- Load **X** (35 features) and **Y** (20 targets) from parquet (`nolhc_ml/data/processed/`) or Excel via the shared loader.
- Enforce **129 rows**, **no NaNs**.

### Step B — Strict train / test split

- **103 train / 26 test** as above; test indices **excluded** from all CV and from `StandardScaler.fit`.

### Step C — Model zoo and hyperparameter grids

- **Core set:** 19 regressors (e.g. GPR RBF/Matern, Random Forest, Extra Trees, Gradient Boosting, AdaBoost, XGBoost, LightGBM, CatBoost, SVR variants, polynomial+Ridge pipelines, Ridge/Lasso/ElasticNet, Bayesian Ridge, KNN, MLP).
- **Additional baselines (mentor request):** `Baseline_Mean` and `Baseline_OLS` can be merged into CV comparisons via `run_baselines_cv.py`.
- Each model has a **discrete grid** (`sklearn.model_selection.ParameterGrid`).

### Step D — Cross-validation (hyperparameter selection)

- For **each target** and **each model**, for **every grid point**, compute fold validation RMSE/MAE under selected CV mode.
- **Current default workflow:** repeated 10-fold (`--cv-mode repeated10 --n-repeats 3` unless overridden).
- **Select hyperparameters** that minimise **mean CV RMSE**; **tie-break:** lower **standard deviation** of fold RMSEs (stability).
- Store `**best_params`**, mean/std CV RMSE, and fold RMSE vectors for paired tests.

**Script:** `run_step1_cv.py`  
**Outputs:** `outputs/cv_results.json`, `cv_results.summary.csv`, derived `cv_best_hyperparameters_long.csv`, `cv_best_model_per_target.csv`, and optional detailed fold audit (`cv_fold_details.csv` / `cv_fold_details.xlsx`) including `cv_mode`, `cv_n_splits`, `cv_n_repeats`, expected fold-score count, and seed.

### Step E — Paired *t*-tests (model comparison on matched folds)

- For each target, for each unordered pair of models in the current CV result set, run `scipy.stats.ttest_rel` on matched vectors of CV validation RMSEs (same CV split design -> paired observations).
- **Significance:** row flagged when **p < 0.05** (conventional α); **“better” model** = lower **mean** CV RMSE for that pair.
- **Interpretation:** A significant result means the observed difference in fold-wise error is **unlikely under the null** of equal mean paired differences, *given the usual t-test assumptions* (small *n* of paired scores → treat as **exploratory** evidence, not definitive proof).

**Script:** `run_paired_ttests.py`  
**Output:** `outputs/paired_ttests_all_targets.csv` (row count depends on number of models included in current CV results).

### Step F — Mentor Step 2 (Friedman/Nemenyi + visual diagnostics)

- Added after mentor feedback to provide stronger global comparison and diagnostics:
  - Friedman omnibus test and Nemenyi post-hoc analysis.
  - Critical Difference (CD) diagrams per target.
  - Learning-curve grids (all models).
  - CV residual-by-fold grids (all models).
- Outputs can be consolidated into a one-tab-per-target workbook.

**Scripts:** `run_mentor_step2.py`, `run_build_master_excel.py`  
**Outputs:** `outputs/step2/*`, `outputs/experiment_master.xlsx`

### Step G — Mentor Step 3 (pre-conformal checks)

- Added before official hold-out/conformal stage:
  - explicit per-target CV winner table,
  - optional baseline integration path,
  - OOF calibration diagnostics for top-K models,
  - hyperparameter sensitivity from `cv_fold_details.csv`,
  - one-sheet-per-target Step 3 workbook.

**Scripts:** `run_step3_pre_conformal.py`, `run_step3_master_excel.py`  
**Outputs:** `outputs/step3/*`, `outputs/step3_report.xlsx`

### Step H — Final retraining on full training set (103 rows)

- For each target and model, **re-instantiate** with `**best_params`**, fit on **all 103** rows using the **global** scaler (already fit on 103) for scaled models.

**Script:** `run_step6_retrain.py`  
**Outputs:** `outputs/trained_models/scaler.joblib`, per-target `*.joblib` models, `split_meta.json`.

### Step I — SHAP explainability (added pre-conformal)

- SHAP explanations are generated for the **selected model per target** (not all models).
- Selection options:
  - `cv` (lowest mean CV RMSE),
  - `composite_pre_test` (CV + t-test wins only; no hold-out dependency),
  - `composite` (full Step 10 composite, requires test/conformal outputs),
  - `json` (explicit mapping).
- For pre-conformal governance, explanations can use `--explain-split train` (default) to avoid touching hold-out rows before official evaluation.
- SHAP outputs are consolidated into a single workbook with one tab per target.

**Scripts:** `run_step4_shap.py`, `run_step4_shap_master_excel.py`  
**Outputs:** `outputs/step4_shap/*`, `outputs/shap_master.xlsx`

### Step J — Hold-out test evaluation (26 rows)

- Predict for **every** model and target; compute **RMSE, MAE, R²**.

**Script:** `run_step7_9_evaluate.py`  
**Outputs:** `test_results.json`, `test_results.csv`.

### Step K — Conformal-style intervals (adaptive coverage)

- For each target, **relative test RMSE** vs **best test RMSE** among the 19 models sets a **nominal coverage** (0.90 / 0.95 / 0.99 per spec).
- **Symmetric intervals:** `±` empirical quantile of **absolute test residuals** at that coverage.
- **Reported:** empirical coverage on the 26 points and **interval width** (`2q`).

**Note:** Residuals are computed on the **test** set (spec acknowledges this as a pragmatic **split conformal** variant; a dedicated calibration split would be preferable for production).

**Outputs:** `conformal_results.json`, `conformal_results.csv` (same script as Step G).

### Step L — Composite “best model” selection (for reporting)

For **each target**, a **single recommended model** is chosen using:


| Component       | Weight  | What it measures                                                                                       |
| --------------- | ------- | ------------------------------------------------------------------------------------------------------ |
| CV error        | **40%** | Normalised **mean CV RMSE** (lower better → higher score after `1 − norm`)                             |
| Test error      | **40%** | Normalised **test RMSE**                                                                               |
| T-test evidence | **20%** | **Wins / 18** — count of **other** models beaten with **p < 0.05** on paired fold RMSEs, divided by 18 |


**Tie-breakers (if composite scores within 0.01):** (1) lower **CV std**; (2) **simpler** model per an agreed ordering (e.g. Ridge preferred over large ensembles / GPR).

**Important caveat for mentors:** Because **test RMSE** enters the composite, the **named “best” model** is **not** a purely test-agnostic choice; it is **aligned with the written project spec**. For a **strict** “choose on CV only, then evaluate once on test,” the composite would need to drop the test term or use nested held-out data.

**Implementation:** `src/excel_report.py` → `compute_model_selection`.

### Step M — Excel workbook

**Script:** `run_step10_report.py` → `**outputs/pipeline_results.xlsx`**.

**Sheets (conceptual):**

1. **Summary** — One row per target: selected model and key metrics (CV, test, composite-related fields, conformal summary), sorted by test RMSE; executive title row.
2. **CV_Results** — Top block: **mini-table of selected best model metrics for all targets**; main table: every model’s **CV mean/std RMSE** and `**Is_Selected_Best_Model`**; **green** row highlight for the selected model per target.
3. **Test_Results** — Same top mini-block; full test metrics; **green** highlights; **conditional colour scale on RMSE** **per target block** (within-target comparison).
4. **Target_01 … Target_20** — **Banner** with that target’s **selected** model and metrics; **171 pairwise *t*-test rows** (yellow highlight if **p < 0.05**); **19×19 p-value matrix** with colour scale and **red bold** for **p < 0.05**.
5. **Conformal_Prediction** — Top mini-block; per model coverage, quantile, empirical coverage, width; **green** on selected model rows.
6. **Model_Selection** — Full table including **Justification** text column.

Formatting follows the spec: **header fill #1F4E79**, **alternating rows**, **frozen panes**, **autofit** (with a wider column for justification).

### Optional artefacts

- **Selected model vs test actuals:** `run_selected_model_test_predictions.py`.
- **Pre-conformal mentor checkpoint workbook:** `run_pre_conformal_report.py` -> `outputs/pre_conformal_checkpoint.xlsx` (aggregates Step 1/2/3/4 evidence before official conformal/final test sign-off).

---

## 4. What is “significant,” and how to read it


| Location                   | Criterion              | Meaning                                                                                                                                        |
| -------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Paired *t*-test**        | **p < 0.05**           | Reject equal mean paired fold-RMSE at α = 0.05; the **Better_Model** column names the lower-mean-RMSE side *if* the difference is significant. |
| **Pairwise table (Excel)** | Yellow row             | **Significant** pair at α = 0.05.                                                                                                              |
| **P-value matrix**         | Red bold, colour scale | Draws attention to **small p-values** (stronger evidence against equal performance on paired CV fold scores).                                  |


**Caveats:**

- **Multiple comparisons:** 171 tests × 20 targets ⇒ many hypotheses; **false positives** are possible. The composite score uses **win counts** as a **soft** summary, not formal FDR control.
- **Finite fold samples:** paired *t*-tests remain based on limited CV score vectors (even with repeated CV); treat as supporting evidence with practical effect sizes and metric differences.

---

## 5. Why these choices for cross-validation, testing, and conformal coverage


| Choice                                          | Rationale                                                                                                                                           |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Repeated 10-fold CV on train only (default)** | Increases stability of CV estimates on **n = 103** while keeping hold-out rows untouched.                                                           |
| **RMSE as CV metric**                           | Same units as targets; penalises large errors; standard for regression surrogates.                                                                  |
| **Tie-break on std of fold RMSEs**              | Favours **stable** configurations when mean RMSE is similar.                                                                                        |
| **20% hold-out test**                           | Single **unbiased** snapshot of performance on **unseen** designs (given i.i.d.-style sampling of the NOLHC design).                                |
| **Paired *t*-test on fold errors**              | Pairs are aligned by identical fold partitions, satisfying pairing; compares fold-error distributions rather than a single scalar.                  |
| **Adaptive conformal coverage**                 | Worse models (relative test RMSE) receive **wider** intervals (higher nominal coverage), reflecting **higher uncertainty** in a simple way.         |
| **Composite selection**                         | Balances **internal CV**, **external test**, and **pairwise significance** in one score for **reporting**; weights match the project specification. |


---

## 6. Reproducibility checklist (files and commands)


| Stage                      | Command (from `experimenting_ml/`)                                              | Main outputs                                     |
| -------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------ |
| CV                         | `python run_step1_cv.py --cv-mode repeated10 --n-repeats 3 --save-fold-details` | `outputs/cv_results.json`, `cv_fold_details.csv` |
| Paired tests               | `python run_paired_ttests.py`                                                   | `outputs/paired_ttests_all_targets.csv`          |
| Mentor Step 2              | `python run_mentor_step2.py`                                                    | `outputs/step2/*`                                |
| Mentor Step 2 workbook     | `python run_build_master_excel.py`                                              | `outputs/experiment_master.xlsx`                 |
| Mentor Step 3              | `python run_step3_pre_conformal.py`                                             | `outputs/step3/*`                                |
| Mentor Step 3 workbook     | `python run_step3_master_excel.py`                                              | `outputs/step3_report.xlsx`                      |
| Retrain                    | `python run_step6_retrain.py`                                                   | `outputs/trained_models/`                        |
| SHAP (pre-conformal)       | `python run_step4_shap.py --selection composite_pre_test --explain-split train` | `outputs/step4_shap/*`                           |
| SHAP workbook              | `python run_step4_shap_master_excel.py`                                         | `outputs/shap_master.xlsx`                       |
| Mentor checkpoint workbook | `aqsw21`                                                                        | `outputs/pre_conformal_checkpoint.xlsx`          |
| Test + conformal           | `python run_step7_9_evaluate.py`                                                | `test_results.json`, `conformal_results.json`    |
| Excel                      | `python run_step10_report.py`                                                   | `outputs/pipeline_results.xlsx`                  |
| Selected-model test table  | `python run_selected_model_test_predictions.py`                                 | `selected_model_test_predictions.csv`            |


**Environment:** Python with `pandas`, `numpy`, `scikit-learn`, `scipy`, `xgboost`, `lightgbm`, `catboost`, `openpyxl`, `joblib` (see `experimenting_ml/requirements.txt`).

---

## 7. Limitations (suitable for mentor discussion)

1. **Sample size:** 129 runs is **small** for 31 inputs; risk of **overfitting** and **high-variance** test metrics on **26** points, despite using all 35 available inputs.
2. **Composite uses test RMSE (final report mode):** Selecting with test in the score is optimistic for strict blind claims; pre-conformal workflow uses `composite_pre_test` for SHAP/model explanation before hold-out evaluation.
3. **Conformal on test (current implementation):** Intervals are calibrated on the same 26 points used for scoring; interpret as descriptive rather than formal split-conformal guarantees.
4. **Small-data sensitivity:** repeated CV improves stability but cannot fully remove variance from a small 129-run design.
5. **No uncertainty on inputs:** Surrogates map design parameters only; propagation of input uncertainty is out of scope here.

---

## 8. Closing summary

This experiment now implements a staged mentor-reviewed pipeline across **20 targets** on a **129-run NOLHC** dataset: leakage-aware splitting, repeated CV tuning, paired statistical comparisons, mentor Step 2 global diagnostics, mentor Step 3 pre-conformal validation, SHAP explainability before official hold-out evaluation, and final test/conformal reporting once approved. Results are packaged into both checkpoint workbooks (including `**pre_conformal_checkpoint.xlsx`**) and the final integrated workbook (`**pipeline_results.xlsx**`) for audit and supervision.

---

*Report generated to accompany the `experimenting_ml` pipeline. For the formal algorithmic spec, see `experimenting_ml/docs/ML_Pipeline_Specification.md`.*