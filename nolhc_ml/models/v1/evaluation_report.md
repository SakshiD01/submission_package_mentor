# NOLHC ML surrogate — per-KPI evaluation

Model version **v1** · training runs **129** · holdout split **103/26** · CV **5-fold** (seed=42) · prediction intervals **90%** (split-conformal on OOF residuals).

> *Training* = registered model refit on the **full** dataset, evaluated on the same data (apparent error). *Test* = fresh model clone refit on the 80% training split, evaluated on the 20% holdout. *CV* = 5-fold mean ± std across folds; ‘pooled OOF’ stitches the five held-out folds back together.


## 1. Headline metrics per KPI

| # | KPI | Unit | Registered model | Train RMSE | Train MAE | Train R² | Test RMSE | Test MAE | Test R² | CV RMSE (mean ± std) | CV MAE (mean ± std) | CV R² (mean ± std) | 90% PI half-width |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | tt_ob_agri | hours | extra_trees | 1.724 | 0.771 | 0.997 | 11.102 | 6.450 | 0.842 | 8.943 ± 2.964 | 4.253 ± 1.366 | 0.901 ± 0.039 | 13.692 |
| 2 | wt_ob_a_gb_dub | hours | lasso | 0.183 | 0.126 | 0.898 | 0.146 | 0.113 | 0.900 | 0.199 ± 0.042 | 0.146 ± 0.027 | 0.873 ± 0.036 | 0.280 |
| 3 | wt_ob_a_gb_ross | hours | catboost | 0.004 | 0.003 | 0.996 | 0.024 | 0.019 | 0.863 | 0.023 ± 0.005 | 0.016 ± 0.002 | 0.846 ± 0.034 | 0.034 |
| 4 | tt_ib_agri | hours | stacking | 5.298 | 3.761 | 0.987 | 10.829 | 7.245 | 0.953 | 6.884 ± 1.640 | 4.630 ± 0.874 | 0.977 ± 0.007 | 12.751 |
| 5 | wt_ib_a_dub | hours | stacking | 0.053 | 0.043 | 0.971 | 0.068 | 0.052 | 0.921 | 0.095 ± 0.023 | 0.070 ± 0.014 | 0.900 ± 0.037 | 0.165 |
| 6 | wt_ib_a_ross | hours | stacking | 0.014 | 0.009 | 0.985 | 0.030 | 0.021 | 0.927 | 0.046 ± 0.023 | 0.030 ± 0.009 | 0.842 ± 0.078 | 0.068 |
| 7 | wt_ib_na_dub | hours | ridge | 23.396 | 18.881 | 0.858 | 26.317 | 21.274 | 0.834 | 28.306 ± 2.296 | 23.063 ± 1.544 | 0.783 ± 0.048 | 43.174 |
| 8 | wt_ob_na_gb_dub | hours | stacking | 0.192 | 0.140 | 0.957 | 0.332 | 0.269 | 0.885 | 0.387 ± 0.056 | 0.285 ± 0.015 | 0.801 ± 0.064 | 0.590 |
| 9 | wt_ib_na_ross | hours | svr_rbf | 7.193 | 1.081 | 0.289 | 14.931 | 3.554 | 0.054 | 6.022 ± 5.515 | 1.833 ± 1.205 | 0.141 ± 0.181 | 1.815 |
| 10 | wt_ob_na_gb_ross | hours | gpr_matern | 0.000 | 0.000 | 1.000 | 0.250 | 0.188 | 0.928 | 0.260 ± 0.051 | 0.198 ± 0.027 | 0.885 ± 0.039 | 0.416 |
| 11 | tt_ob_lb | hours | extra_trees | 0.056 | 0.032 | 0.985 | 0.189 | 0.132 | 0.847 | 0.247 ± 0.058 | 0.170 ± 0.038 | 0.651 ± 0.220 | 0.453 |
| 12 | wt_ob_lb | hours | gpr_matern | 0.000 | 0.000 | 1.000 | 0.170 | 0.135 | 0.956 | 0.209 ± 0.038 | 0.161 ± 0.026 | 0.912 ± 0.033 | 0.331 |
| 13 | tt_ib_lb | hours | stacking | 10.875 | 8.909 | 0.947 | 20.924 | 16.111 | 0.833 | 21.214 ± 1.576 | 17.245 ± 1.602 | 0.792 ± 0.038 | 34.106 |
| 14 | wt_ib_lb | hours | stacking | 10.048 | 8.064 | 0.974 | 29.703 | 22.056 | 0.826 | 26.981 ± 2.233 | 21.948 ± 2.039 | 0.802 ± 0.035 | 44.627 |
| 15 | tt_ob_dr | hours | random_forest | 0.213 | 0.162 | 0.866 | 0.468 | 0.383 | 0.360 | 0.461 ± 0.033 | 0.371 ± 0.013 | 0.248 ± 0.299 | 0.708 |
| 16 | tt_ib_dr | hours | stacking | 0.144 | 0.063 | 0.551 | 0.284 | 0.116 | -0.018 | 0.180 ± 0.116 | 0.085 ± 0.041 | -0.117 ± 0.179 | 0.240 |
| 17 | uti_cus_d | fraction | stacking | 0.008 | 0.006 | 0.997 | 0.046 | 0.038 | 0.803 | 0.070 ± 0.016 | 0.052 ± 0.009 | 0.719 ± 0.058 | 0.111 |
| 18 | uti_dafm_d | fraction | gpr_matern | 0.000 | 0.000 | 1.000 | 0.033 | 0.027 | 0.773 | 0.029 ± 0.006 | 0.023 ± 0.004 | 0.870 ± 0.062 | 0.051 |
| 19 | uti_cus_r | fraction | elastic_net | 0.041 | 0.030 | 0.947 | 0.055 | 0.038 | 0.909 | 0.043 ± 0.009 | 0.032 ± 0.006 | 0.939 ± 0.016 | 0.066 |
| 20 | uti_dafm_r | fraction | gpr_rbf | 0.000 | 0.000 | 1.000 | 0.010 | 0.008 | 0.961 | 0.011 ± 0.003 | 0.009 ± 0.002 | 0.949 ± 0.017 | 0.016 |

## 2. Residual analysis (out-of-fold)

| # | KPI | resid mean | resid std | |resid| mean | q05 | q50 | q95 | min | max |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | tt_ob_agri | 0.648 | 9.457 | 4.264 | -9.501 | -0.043 | 17.152 | -32.825 | 47.888 |
| 2 | wt_ob_a_gb_dub | -0.003 | 0.204 | 0.146 | -0.271 | -0.016 | 0.267 | -0.762 | 0.894 |
| 3 | wt_ob_a_gb_ross | 0.000 | 0.024 | 0.016 | -0.028 | -0.005 | 0.039 | -0.041 | 0.127 |
| 4 | tt_ib_agri | 0.258 | 7.099 | 4.629 | -12.200 | 1.586 | 12.300 | -27.843 | 23.285 |
| 5 | wt_ib_a_dub | 0.002 | 0.098 | 0.070 | -0.144 | -0.003 | 0.161 | -0.266 | 0.359 |
| 6 | wt_ib_a_ross | 0.001 | 0.051 | 0.030 | -0.054 | -0.008 | 0.079 | -0.078 | 0.297 |
| 7 | wt_ib_na_dub | 1.665 | 28.451 | 23.046 | -43.649 | 1.754 | 41.998 | -65.481 | 108.901 |
| 8 | wt_ob_na_gb_dub | -0.005 | 0.392 | 0.285 | -0.601 | -0.012 | 0.567 | -1.062 | 1.841 |
| 9 | wt_ib_na_ross | 1.036 | 8.116 | 1.824 | -1.426 | -0.162 | 2.003 | -2.547 | 75.966 |
| 10 | wt_ob_na_gb_ross | 0.000 | 0.266 | 0.197 | -0.401 | -0.008 | 0.439 | -0.862 | 1.091 |
| 11 | tt_ob_lb | -0.000 | 0.256 | 0.170 | -0.440 | -0.007 | 0.457 | -0.779 | 0.977 |
| 12 | wt_ob_lb | -0.001 | 0.212 | 0.161 | -0.289 | -0.010 | 0.336 | -0.539 | 0.789 |
| 13 | tt_ib_lb | 0.693 | 21.331 | 17.231 | -34.093 | 0.636 | 31.959 | -51.032 | 65.295 |
| 14 | wt_ib_lb | 1.122 | 27.142 | 21.933 | -44.834 | 3.183 | 41.261 | -69.698 | 82.233 |
| 15 | tt_ob_dr | 0.010 | 0.463 | 0.371 | -0.751 | 0.072 | 0.599 | -1.121 | 1.316 |
| 16 | tt_ib_dr | 0.002 | 0.215 | 0.086 | -0.121 | -0.020 | 0.263 | -1.019 | 0.984 |
| 17 | uti_cus_d | 0.001 | 0.073 | 0.052 | -0.147 | 0.013 | 0.089 | -0.250 | 0.169 |
| 18 | uti_dafm_d | -0.001 | 0.030 | 0.023 | -0.044 | -0.003 | 0.052 | -0.082 | 0.108 |
| 19 | uti_cus_r | 0.000 | 0.044 | 0.032 | -0.054 | 0.000 | 0.069 | -0.211 | 0.125 |
| 20 | uti_dafm_r | 0.000 | 0.011 | 0.009 | -0.016 | 0.000 | 0.016 | -0.025 | 0.041 |

## 3. GPR-native 90% interval (Gaussian, out-of-fold σ̂)

| KPI | median σ̂ (OOF) | mean σ̂ (OOF) | median half-width (1.645·σ̂) | mean half-width | empirical coverage |
|---|---:|---:|---:|---:|---:|
| wt_ob_na_gb_ross | 0.248 | 0.249 | 0.408 | 0.409 | 0.868 |
| wt_ob_lb | 0.208 | 0.208 | 0.342 | 0.343 | 0.899 |
| uti_dafm_d | 0.032 | 0.032 | 0.052 | 0.053 | 0.922 |
| uti_dafm_r | 0.011 | 0.011 | 0.018 | 0.018 | 0.915 |

## 4. Per-fold CV (R²)

| KPI | fold 1 | fold 2 | fold 3 | fold 4 | fold 5 | mean | std |
|---|---:|---:|---:|---:|---:|---:|---:|
| tt_ob_agri | 0.842 | 0.927 | 0.890 | 0.886 | 0.958 | 0.901 | 0.039 |
| wt_ob_a_gb_dub | 0.900 | 0.911 | 0.843 | 0.892 | 0.819 | 0.873 | 0.036 |
| wt_ob_a_gb_ross | 0.879 | 0.830 | 0.788 | 0.853 | 0.880 | 0.846 | 0.034 |
| tt_ib_agri | 0.965 | 0.987 | 0.976 | 0.980 | 0.979 | 0.977 | 0.007 |
| wt_ib_a_dub | 0.931 | 0.926 | 0.833 | 0.924 | 0.887 | 0.900 | 0.037 |
| wt_ib_a_ross | 0.925 | 0.847 | 0.890 | 0.853 | 0.697 | 0.842 | 0.078 |
| wt_ib_na_dub | 0.834 | 0.747 | 0.809 | 0.707 | 0.817 | 0.783 | 0.048 |
| wt_ob_na_gb_dub | 0.884 | 0.826 | 0.827 | 0.690 | 0.781 | 0.801 | 0.064 |
| wt_ib_na_ross | 0.054 | -0.081 | 0.370 | 0.342 | 0.021 | 0.141 | 0.181 |
| wt_ob_na_gb_ross | 0.928 | 0.891 | 0.922 | 0.824 | 0.862 | 0.885 | 0.039 |
| tt_ob_lb | 0.845 | 0.234 | 0.719 | 0.647 | 0.811 | 0.651 | 0.220 |
| wt_ob_lb | 0.956 | 0.910 | 0.936 | 0.860 | 0.899 | 0.912 | 0.033 |
| tt_ib_lb | 0.848 | 0.769 | 0.799 | 0.735 | 0.807 | 0.792 | 0.038 |
| wt_ib_lb | 0.843 | 0.779 | 0.819 | 0.746 | 0.823 | 0.802 | 0.035 |
| tt_ob_dr | 0.383 | 0.423 | -0.313 | 0.211 | 0.536 | 0.248 | 0.299 |
| tt_ib_dr | -0.049 | -0.474 | -0.006 | -0.009 | -0.049 | -0.117 | 0.179 |
| uti_cus_d | 0.783 | 0.625 | 0.778 | 0.710 | 0.701 | 0.719 | 0.058 |
| uti_dafm_d | 0.773 | 0.911 | 0.833 | 0.952 | 0.882 | 0.870 | 0.062 |
| uti_cus_r | 0.909 | 0.952 | 0.946 | 0.950 | 0.936 | 0.939 | 0.016 |
| uti_dafm_r | 0.961 | 0.920 | 0.958 | 0.966 | 0.938 | 0.949 | 0.017 |

## Methodology notes

- **RMSE / MAE** are reported in the KPI's native unit (hours for travel/wait times, fractions for utilisation). **R²** is unitless.
- **Train / Test / CV split.** All three views share the same `KFold(5, shuffle=True, random_state=42)` seed used during training. The 80/20 holdout uses the same seed.
- **Prediction intervals.** Marginal 90% intervals are built by split-conformal calibration on out-of-fold residuals: half-width = quantile(|y − ŷ_OOF|, ⌈0.90·(n+1)⌉/n). Coverage is guaranteed in distribution under exchangeability.
- **GPR-native intervals** are reported for KPIs whose registered model is `gpr_rbf` or `gpr_matern`: σ̂(x) is the GP posterior std and the 90% interval is ±1.6449·σ̂(x). We summarise σ̂ with its median and mean over the training set.
- **Residual analysis.** All residuals are OOF (y − ŷ from 5-fold CV) — the honest residuals an operator would see on a new run with the same data-generating process. Per-row residuals are persisted to `residuals/<slug>.csv` for downstream plotting.
