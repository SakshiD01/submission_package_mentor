Step 3 — pre-conformal methodology

(a) Per-target selection: see per_target_cv_selection.csv (best = min mean CV RMSE per target).
    Excel Step 10 composite selection remains separate (CV + test + t-test wins).

(b) Baselines: DummyRegressor(mean) and LinearRegression are in get_models() as
    Baseline_Mean and Baseline_OLS. Merge CV with: python run_baselines_cv.py
    then: python run_paired_ttests.py

(c) Calibration: OOF pooled y vs ŷ; check mean_residual ~ 0 and slope_y_on_yhat ~ 1.
    Plots in calibration/ subdirectory.

(d) HP sensitivity: requires cv_fold_details.csv from run_step1_cv.py --save-fold-details.

Then: run_step6_retrain.py → run_step7_9_evaluate.py (conformal).
