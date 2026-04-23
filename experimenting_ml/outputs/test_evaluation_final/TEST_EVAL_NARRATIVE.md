# Test set evaluation — hold-out (finalization step 2)

## Scope
- **Hold-out fraction:** 20% of design rows (see `trained_models/split_meta.json`); **not** used in CV or training.
- **Nominal coverage for intervals:** **90%** (fixed symmetric intervals in summary tables below).
- **Caveat:** Intervals use the absolute residual quantile on the **same** hold-out points used for RMSE; interpret as **descriptive** marginal coverage, not full split-conformal guarantees.

## Point predictions + intervals
- Long table: `outputs/test_evaluation_final/selected_holdout_predictions_long.csv` — one row per hold-out point and selected model per target (y, ŷ, residual, **90%** lower/upper).
- Per-target summary: `outputs/test_evaluation_final/selected_holdout_summary.csv` — RMSE/MAE/R², **90%** quantile half-width, empirical coverage, diagnostic flags.

## Single narrative: point error + interval width + residual behaviour
- **TT_OB_Agri** (ExtraTrees): test RMSE=5.40977, 90% interval half-width q=|r| quantile=8.99321, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **WT_OB_A_GB-Dub** (Lasso): test RMSE=0.207594, 90% interval half-width q=|r| quantile=0.262803, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **WT_OB_A_GB-Ross** (GPR_Matern): test RMSE=0.0179418, 90% interval half-width q=|r| quantile=0.0302173, empirical coverage=0.885, bias_flag=False, tail_flag=False.
- **TT_IB_Agri** (ExtraTrees): test RMSE=7.91707, 90% interval half-width q=|r| quantile=9.399, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **WT_IB_A_Dub** (GPR_Matern): test RMSE=0.14661, 90% interval half-width q=|r| quantile=0.192973, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **WT_IB_A_Ross** (GPR_Matern): test RMSE=0.0729602, 90% interval half-width q=|r| quantile=0.114888, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **WT_IB_NA_Dub** (Lasso): test RMSE=29.2921, 90% interval half-width q=|r| quantile=44.2235, empirical coverage=0.885, bias_flag=False, tail_flag=False.
- **WT_OB_NA_GB-Dub** (Lasso): test RMSE=0.513219, 90% interval half-width q=|r| quantile=0.689849, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **WT_IB_NA_Ross** (SVR_RBF): test RMSE=9.65267, 90% interval half-width q=|r| quantile=1.68737, empirical coverage=0.885, bias_flag=True, tail_flag=True.
- **WT_OB_NA_GB-Ross** (ElasticNet): test RMSE=0.396383, 90% interval half-width q=|r| quantile=0.506297, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **TT_OB_LB** (ExtraTrees): test RMSE=0.180428, 90% interval half-width q=|r| quantile=0.214, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **WT_OB_LB** (GPR_Matern): test RMSE=0.278876, 90% interval half-width q=|r| quantile=0.403032, empirical coverage=0.885, bias_flag=False, tail_flag=False.
- **TT_IB_LB** (Lasso): test RMSE=22.1024, 90% interval half-width q=|r| quantile=32.5556, empirical coverage=0.885, bias_flag=False, tail_flag=False.
- **WT_IB_LB** (Lasso): test RMSE=28.792, 90% interval half-width q=|r| quantile=46.1973, empirical coverage=0.885, bias_flag=False, tail_flag=False.
- **TT_OB_DR** (CatBoost): test RMSE=0.559192, 90% interval half-width q=|r| quantile=0.827658, empirical coverage=0.885, bias_flag=False, tail_flag=False.
- **TT_IB_DR** (CatBoost): test RMSE=0.0771778, 90% interval half-width q=|r| quantile=0.122041, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **Uti_Cus_D** (GPR_Matern): test RMSE=0.0629668, 90% interval half-width q=|r| quantile=0.115009, empirical coverage=0.885, bias_flag=False, tail_flag=False.
- **Uti_DAFM_D** (GPR_Matern): test RMSE=0.0403696, 90% interval half-width q=|r| quantile=0.0611003, empirical coverage=0.885, bias_flag=False, tail_flag=True.
- **Uti_Cus_R** (Lasso): test RMSE=0.0415785, 90% interval half-width q=|r| quantile=0.0709954, empirical coverage=0.885, bias_flag=False, tail_flag=False.
- **Uti_DAFM_R** (GPR_Matern): test RMSE=0.0163984, 90% interval half-width q=|r| quantile=0.0255377, empirical coverage=0.885, bias_flag=False, tail_flag=False.

## Figures (residual diagnostics)
- Hold-out size **n = 26** per target.
- `outputs/test_evaluation_final/plots/TT_IB_Agri_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/TT_IB_DR_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/TT_IB_LB_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/TT_OB_Agri_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/TT_OB_DR_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/TT_OB_LB_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/Uti_Cus_D_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/Uti_Cus_R_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/Uti_DAFM_D_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/Uti_DAFM_R_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_IB_A_Dub_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_IB_A_Ross_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_IB_LB_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_IB_NA_Dub_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_IB_NA_Ross_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_OB_A_GB-Dub_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_OB_A_GB-Ross_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_OB_LB_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_OB_NA_GB-Dub_holdout_residual_diagnostics.png`
- `outputs/test_evaluation_final/plots/WT_OB_NA_GB-Ross_holdout_residual_diagnostics.png`

## Tabular summary (copy into final report)

| target | model | RMSE | MAE | R² | q(|r|) at nominal | empirical cov. | width 2q | bias? | tails? |
|---|---|--:|--:|--:|--:|--:|--:|:--:|:--:|
| TT_OB_Agri | ExtraTrees | 5.40977 | 3.10637 | 0.9655 | 8.99321 | 0.885 | 17.9864 | False | True |
| WT_OB_A_GB-Dub | Lasso | 0.207594 | 0.14753 | 0.8219 | 0.262803 | 0.885 | 0.525607 | False | True |
| WT_OB_A_GB-Ross | GPR_Matern | 0.0179418 | 0.014606 | 0.9156 | 0.0302173 | 0.885 | 0.0604345 | False | False |
| TT_IB_Agri | ExtraTrees | 7.91707 | 4.73746 | 0.9725 | 9.399 | 0.885 | 18.798 | False | True |
| WT_IB_A_Dub | GPR_Matern | 0.14661 | 0.0970157 | 0.8398 | 0.192973 | 0.885 | 0.385946 | False | True |
| WT_IB_A_Ross | GPR_Matern | 0.0729602 | 0.0407618 | 0.7915 | 0.114888 | 0.885 | 0.229775 | False | True |
| WT_IB_NA_Dub | Lasso | 29.2921 | 25.1913 | 0.8185 | 44.2235 | 0.885 | 88.447 | False | False |
| WT_OB_NA_GB-Dub | Lasso | 0.513219 | 0.33112 | 0.7586 | 0.689849 | 0.885 | 1.3797 | False | True |
| WT_IB_NA_Ross | SVR_RBF | 9.65267 | 2.89801 | 0.0272 | 1.68737 | 0.885 | 3.37474 | True | True |
| WT_OB_NA_GB-Ross | ElasticNet | 0.396383 | 0.257211 | 0.8214 | 0.506297 | 0.885 | 1.01259 | False | True |
| TT_OB_LB | ExtraTrees | 0.180428 | 0.126196 | 0.7905 | 0.214 | 0.885 | 0.428 | False | True |
| WT_OB_LB | GPR_Matern | 0.278876 | 0.214369 | 0.8913 | 0.403032 | 0.885 | 0.806065 | False | False |
| TT_IB_LB | Lasso | 22.1024 | 19.0001 | 0.8180 | 32.5556 | 0.885 | 65.1112 | False | False |
| WT_IB_LB | Lasso | 28.792 | 24.391 | 0.8207 | 46.1973 | 0.885 | 92.3945 | False | False |
| TT_OB_DR | CatBoost | 0.559192 | 0.427982 | 0.4470 | 0.827658 | 0.885 | 1.65532 | False | False |
| TT_IB_DR | CatBoost | 0.0771778 | 0.0389687 | -0.1948 | 0.122041 | 0.885 | 0.244082 | False | True |
| Uti_Cus_D | GPR_Matern | 0.0629668 | 0.044889 | 0.6528 | 0.115009 | 0.885 | 0.230018 | False | False |
| Uti_DAFM_D | GPR_Matern | 0.0403696 | 0.0267745 | 0.8646 | 0.0611003 | 0.885 | 0.122201 | False | True |
| Uti_Cus_R | Lasso | 0.0415785 | 0.0325605 | 0.9571 | 0.0709954 | 0.885 | 0.141991 | False | False |
| Uti_DAFM_R | GPR_Matern | 0.0163984 | 0.0128629 | 0.9294 | 0.0255377 | 0.885 | 0.0510753 | False | False |
