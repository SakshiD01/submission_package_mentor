# NOLHC XAI crosswalk — inputs, outputs, and review

This document ties **code identifiers** in `nolhc_ml` / `experimenting_ml` to **plain-language semantics** for SHAP review and reporting.  
It is aligned with:

- `nolhc_ml/src/training_columns.py` (`TRAINING_COLUMN_ORDER`, `OUTPUT_COLUMN_ORDER`, `INPUT_DESCRIPTIONS`, `OUTPUT_DESCRIPTIONS`)
- `docs/SIG Presentation - NOLHC results Students (1).pdf` (slides 15–16: Post-Brexit parameters and performance indicators)
- Your technical report (`Technical-report-Final.docx`) — use it to add nuance where a parameter has extra modelling detail

**Machine-readable tables (fill in the last columns for your workshop):**

- `docs/nolhc_inputs_crosswalk.csv` — 35 features  
- `docs/nolhc_outputs_crosswalk.csv` — 20 targets  

## 1. How to use this for SHAP (Step 3)

**Automated join (recommended):** From `experimenting_ml/`, run `python run_shap_top_features_report.py`. It reads `outputs/step4_shap/*__importance.csv` (paired with `shap_selected_models.csv` when present), merges `docs/nolhc_inputs_crosswalk.csv`, and writes `outputs/step4_shap/xai_review/xai_shap_top_features_long.csv` plus `xai_shap_domain_review.xlsx` (includes a short review checklist). Use that table to validate **per-scenario** top-feature rankings against domain knowledge before stakeholder-facing text.

**Manual path:** For each target, open `outputs/step4_shap/*__importance.csv` (or the SHAP master workbook), take the **top 5** by mean |SHAP|, and cross-check descriptions in the CSV below.

1. For each feature, read **short_description** and **sig_category** (from the automated long table or the crosswalk).  
2. In `nolhc_inputs_crosswalk.csv`, fill **`xai_review_expected_surprising_flag`**: `expected` / `surprising` / `red_flag` and one sentence if needed.  
3. Optional: re-run SHAP with `--explain-split train` vs `--explain-split test` and check whether top-5 features stay similar; note any large flips in the report.

## 2. Input parameters (35) — groups (SIG slide 15)

| SIG-style group | Role |
|-----------------|------|
| Shifts in trade volume | GB↔IRE non-agri and agri import/export tonnes (`NA_*`, `A_*`). |
| Direct routes vs land-bridge | Volumes and shifts onto Cherbourg/Direct route (`Shift_*`, `*_LB`, `*_DR`). |
| Land-bridge vessel capacity | Dublin/Rosslare ferry capacities to GB (`VCap_*`). |
| Customs expertise & resources | Check times and shed/bay counts (`ChkTime_*`, `Num*`). |
| Border checks intervention | Green/red/pre-board routing fractions (`Pct_*`). |

**Units:** tonnes (volumes), trailers (capacities), minutes (check times), counts (sheds/bays), **fraction** 0–1 for `Pct_*` (see `input_unit()` in `training_columns.py`).

Full row-level list is in **`nolhc_inputs_crosswalk.csv`** (same strings as `INPUT_DESCRIPTIONS` in code).

## 3. Output KPIs (20) — SIG slide 16

| Prefix | Meaning |
|--------|--------|
| `TT_` | Transportation time (hours) |
| `WT_` | Waiting time at checkpoints (hours) |
| `Uti_` | Utilisation (fraction 0–1) |
| `IB` / `OB` | Inbound to Ireland / Outbound from Ireland |
| `LB` / `DR` | Land-bridge / Direct route |
| `Dub` / `Ross` | Dublin / Rosslare |
| `A` / `NA` | Agri / Non-agri |
| `GB-Dub` / `GB-Ross` | UK-side checkpoint associated with Dublin/Rosslare corridor |

**Note:** Slide 16 may show minor punctuation differences (e.g. `TT-OB-Agri`); the **canonical names** are the ones in `OUTPUT_COLUMN_ORDER` and in **`nolhc_outputs_crosswalk.csv`**.

## 4. References in code

- Feature list: `TRAINING_COLUMN_ORDER`  
- Target list: `OUTPUT_COLUMN_ORDER`  
- Descriptions: `INPUT_DESCRIPTIONS`, `OUTPUT_DESCRIPTIONS` in `nolhc_ml/src/training_columns.py`  

## 5. NOLHC design (context)

The SIG deck notes **nearly orthogonal Latin hypercube** designs with **129 runs** and bounded percentage-of-change inputs — consistent with the experimental design used for surrogate training. Use this when explaining **generalisation limits** (small *n*, extrapolation) alongside SHAP.

## 6. XAI attribution layer (automation)

| Artifact | Role |
|----------|------|
| `experimenting_ml/run_shap_top_features_report.py` | CLI: `--shap-dir`, `--crosswalk`, `--selected-models`, `--top-k`, `--out-dir` (default `outputs/step4_shap/xai_review/`). |
| `experimenting_ml/src/shap_crosswalk_report.py` | Library: `build_shap_review_long_table`, `write_shap_xai_review_artifacts`. |

SHAP must be computed **per scenario** (each target × selected model importance file). The long CSV and Excel surface top‑*k* features with crosswalk fields so reviewers can **cross-check consistency with domain knowledge** before anything is shared externally.

---

*Generated for XAI attribution review; extend with bullets from `Technical-report-Final.docx` where needed.*
