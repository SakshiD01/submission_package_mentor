# experimenting_ml/reports/

Result workbooks from the uncertainty-quantification (UQ) work
(spec.md §7 item 13, "PROVEN_6", 29-Aug 2026).

| Workbook | Contents |
|---|---|
| `UQ_Method_Benchmark.xlsx` | For each of 6 model families (GPR-Matérn, ExtraTrees, ElasticNet, Lasso, SVR-RBF, GradientBoosting): several candidate UQ methods run on the held-out split, empirical coverage vs the ~90% target, 95% Wilson score CIs, a "considered vs tested" sheet, and the one method chosen per family. Also records the hand-rolled bootstrap-ensemble comparison (lost in every family). |
| `PROVEN_6_Trust_Report.xlsx` | For one real loop round (`round_20260829_181116`): each PROVEN_6 KPI's held-out coverage, plus the live per-candidate flagging decision (trust the ML prediction vs refer to AnyLogic) for all 25 proposed candidates, with the 10 exported ones marked. |
| `UQ_Prediction_Report.xlsx` | Earlier per-KPI conformal interval / coverage snapshot. |

## Reproducible vs result-only

**Reproducible (covered by tests):**

* The six chosen UQ methods and their KPI→method routing —
  `experimenting_ml/src/loop/proven6.py`, verified by
  `tests/test_proven6.py` (including the `tt_ib_lb` GradientBoosting-override
  caveat).
* The UQ estimators themselves (bagged-tree jackknife, GPR-native,
  split-conformal fallback, MAPIE CV+/jackknife+) —
  `experimenting_ml/src/loop/uq/`, verified by `tests/test_uq_estimators.py`
  on real data.
* The live flagging half of `PROVEN_6_Trust_Report.xlsx` — regenerate with
  `python -m loop.cli_export_manual_round --kpi-scope proven6 --seed 42`
  (from `experimenting_ml/src`).

**Result-only (no committed generator script):**

* The per-family method-selection coverage table in
  `UQ_Method_Benchmark.xlsx`. The script that ran the 3-methods-×-6-families
  comparison and emitted the workbook was never committed. The workbook is
  kept as the evidence the mentor reviewed; the *decisions* it produced are
  enforced in code (above). Re-deriving the exact coverage numbers would
  require rebuilding that comparison against the same held-out split
  (seed 42, 103/26) using the `loop/uq/` estimators — a documented follow-up,
  not a one-command reproduction.

See `docs/spec.md` §5.1 and §7 item 13 for the full method rationale, §7 item
14 for the mentor's 1-Sep feedback and how each point was addressed, and §7
item 18 for the recalibration-check mechanism below.

## Checking whether the method choice still holds as the dataset grows

`loop.recalibration_check` / `python -m loop.cli_recalibrate_uq_methods`
(from `experimenting_ml/src`) re-runs each `PROVEN_6` KPI's family
comparison against whatever `dataset_store.load_current_training_data()`
currently holds, and reports whether the fixed method is still the closest
to the 90% coverage target. It does **not** rebuild `UQ_Method_Benchmark.xlsx`
itself (the original 3-methods comparison per family, including the
hand-rolled bootstrap-ensemble candidate, stays result-only as above) — it's
a lighter, committed, tested check for "has anything changed enough to be
worth another mentor look," not a replacement for the original workbook.
Validated to reproduce the workbook's own `wt_ob_lb` numbers exactly
(spec.md §7 item 18) before being trusted for anything.
