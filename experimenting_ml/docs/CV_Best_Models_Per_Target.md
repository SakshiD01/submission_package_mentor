# CV summary — best model per target (5-fold RMSE)

Generated from `outputs/cv_results.json`. Regenerate:

```bash
python generate_cv_summary_md.py
```

| # | Target | Best model (lowest mean CV RMSE) | Mean CV RMSE | Std CV RMSE | Selected hyperparameters |
|---:|---|---|---|---:|---|
| 1 | `TT_OB_Agri` | **ExtraTrees** | 7.3009 | 4.4663 | `max_depth`=10, `min_samples_split`=2, `n_estimators`=200 |
| 2 | `WT_OB_A_GB-Dub` | **ElasticNet** | 0.1954 | 0.0762 | `alpha`=0.1, `l1_ratio`=0.2 |
| 3 | `WT_OB_A_GB-Ross` | **GradientBoosting** | 0.0241 | 0.0063 | `learning_rate`=0.1, `max_depth`=3, `n_estimators`=100 |
| 4 | `TT_IB_Agri` | **ExtraTrees** | 8.3214 | 2.0045 | `max_depth`=null, `min_samples_split`=2, `n_estimators`=200 |
| 5 | `WT_IB_A_Dub` | **GPR_Matern** | 0.1154 | 0.0178 | `alpha`=1e-06 |
| 6 | `WT_IB_A_Ross` | **GPR_Matern** | 0.0376 | 0.0034 | `alpha`=1e-10 |
| 7 | `WT_IB_NA_Dub` | **Lasso** | 28.2438 | 4.4146 | `alpha`=1 |
| 8 | `WT_OB_NA_GB-Dub` | **ElasticNet** | 0.3797 | 0.0979 | `alpha`=0.1, `l1_ratio`=0.2 |
| 9 | `WT_IB_NA_Ross` | **SVR_RBF** | 4.6880 | 6.1596 | `C`=10, `epsilon`=0.01, `gamma`='scale' |
| 10 | `WT_OB_NA_GB-Ross` | **Lasso** | 0.2354 | 0.0197 | `alpha`=0.01 |
| 11 | `TT_OB_LB` | **ExtraTrees** | 0.2620 | 0.0717 | `max_depth`=10, `min_samples_split`=2, `n_estimators`=100 |
| 12 | `WT_OB_LB` | **GPR_Matern** | 0.1983 | 0.0224 | `alpha`=0.001 |
| 13 | `TT_IB_LB` | **GPR_Matern** | 21.4914 | 3.8389 | `alpha`=1e-06 |
| 14 | `WT_IB_LB` | **GPR_Matern** | 27.5631 | 5.4820 | `alpha`=0.001 |
| 15 | `TT_OB_DR` | **ExtraTrees** | 0.4501 | 0.0371 | `max_depth`=5, `min_samples_split`=5, `n_estimators`=100 |
| 16 | `TT_IB_DR` | **SVR_RBF** | 0.2056 | 0.1124 | `C`=0.1, `epsilon`=0.01, `gamma`='scale' |
| 17 | `Uti_Cus_D` | **GPR_Matern** | 0.0849 | 0.0215 | `alpha`=1e-06 |
| 18 | `Uti_DAFM_D` | **GPR_Matern** | 0.0296 | 0.0033 | `alpha`=1e-10 |
| 19 | `Uti_Cus_R` | **ElasticNet** | 0.0417 | 0.0143 | `alpha`=0.01, `l1_ratio`=0.5 |
| 20 | `Uti_DAFM_R` | **GPR_Matern** | 0.0104 | 0.0009 | `alpha`=0.001 |
