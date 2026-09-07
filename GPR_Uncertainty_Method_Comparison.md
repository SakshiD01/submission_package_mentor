# GPR Uncertainty Method Comparison — TT_IB_LB and WT_IB_LB

**Owner:** Sakshi
**Why these two KPIs:** both are GPR (Matérn)-won in production, both are highlighted green in the manual-test screenshot Amr shared, and both are the worst-performing KPIs among everything GPR handles (29.4% and 44.8% relative CV RMSE — see the earlier models/UQ background check). If a better GPR uncertainty method matters anywhere in this engine, it matters here first.
**Data:** the real 129-run `nolhc_runs.xlsx` (35 inputs, standardised). No synthetic data used.
**Code:** `gpr_uq_experiment.py`. Raw results: `gpr_uq_experiment_results.csv`.

## The 4 methods tested

| # | Method | What it is |
|---|---|---|
| A | **Analytic** | The GP's own closed-form posterior std from a single MLE-fit kernel (Matérn ν=1.5 + WhiteKernel, matching the project's existing convention). This is what the pipeline already implicitly relies on. |
| B | **Bayesian (grid)** | A lightweight stand-in for full Bayesian GP (Lalchand & Rasmussen, AABI 2020): instead of one length-scale, fit 3 GPs at 0.5×/1×/2× the optimised length-scale, weight each by its marginal likelihood, and combine into a mixture predictive distribution. True HMC/VI wasn't runnable here — `gpytorch`/`pymc` aren't installed in this environment and aren't in the project's `requirements.txt` — so treat this as an approximation, not the full method. |
| C | **Ensemble (bootstrap)** | 12-member ensemble, each a GP refit on a bootstrap resample of the training rows (Christiansen, Rønne & Hammer, 2024 use noisy-label ensembles specifically; bootstrap resampling is the standard variant used here instead, since it needs no extra assumptions about label noise). Uncertainty = within-model variance + between-model variance (law of total variance). |
| D | **Conformal (normalized)** | Split-conformal, but the nonconformity score is `\|residual\| / GP std` rather than the raw residual — so the resulting interval scales with the GP's own per-point uncertainty instead of being one fixed width for the whole KPI. This is the direct fix for the exact gap the manuscript itself admits ("the interval is therefore marginal, does not vary with x*") — the current `conformal_predict.py` in the repo uses the un-normalised version. |

## Protocol

129 points is not enough for a single held-out test set to be trustworthy, so each method was run on 20 repeated random 80/20 train/test splits per KPI, and coverage/width averaged. Target: 90% coverage (matching the coverage level the production pipeline actually uses for its winning models — see the earlier UQ background check).

## Results

| KPI | Method | Mean coverage (target 90%) | Coverage std across repeats | Mean interval width |
|---|---|---:|---:|---:|
| TT_IB_LB | Analytic | 91.3% | 0.069 | 70.6 |
| TT_IB_LB | Bayesian (grid) | 91.5% | 0.069 | 70.7 |
| TT_IB_LB | Ensemble (bootstrap) | **96.0%** | 0.037 | **84.1** |
| TT_IB_LB | Conformal (normalized) | 91.9% | 0.085 | 80.1 |
| WT_IB_LB | Analytic | 91.2% | 0.066 | 90.9 |
| WT_IB_LB | Bayesian (grid) | 91.2% | 0.066 | 90.8 |
| WT_IB_LB | Ensemble (bootstrap) | **95.4%** | 0.038 | **109.2** |
| WT_IB_LB | Conformal (normalized) | 91.5% | 0.068 | 100.2 |

## Reading the results honestly

**Bayesian (grid) barely moves the needle.** It lands almost exactly on top of Analytic for both KPIs (91.5% vs 91.3%, nearly identical widths). With only ~103 training points feeding a 3-point hyperparameter grid, the marginal likelihood concentrates hard on one length-scale — there isn't enough data for hyperparameter uncertainty to matter much here. This might look different with a genuine HMC-based fully Bayesian fit (a finer or wider grid, or real posterior sampling) — flagging this as a real limitation of the approximation, not a claim that fully-Bayesian GP adds nothing.

**Ensemble (bootstrap) overcovers and is the widest for both KPIs.** 95–96% coverage against a 90% target, and 15–20% wider intervals than Analytic. Bootstrap resampling on an already-small training set (103 points) adds resampling noise that isn't necessarily real epistemic uncertainty — it's the most conservative method here, not the most useful one. Dominated by the other three: wider AND overcovering isn't a trade worth taking.

**Analytic is the sharpest (narrowest) at essentially on-target coverage** — but it's still a fixed shape per point that assumes the GP's Gaussian posterior is exactly correct, with no distribution-free guarantee if that assumption is off.

**Recommendation: Conformal (normalized).** Not because it's the narrowest — Analytic is narrower — but because it's the only method here that combines two things the other three don't: it inherits the GP's own per-point std (so it's still locally adaptive, unlike the current production conformal wrapper), and it adds a distribution-free calibration guarantee on top, so it doesn't silently rely on the GP's Gaussian-posterior assumption being exactly right. That's the specific, named gap in the manuscript's own §4.4 ("the interval is therefore marginal... does not vary with x*") — this is the direct fix, built on the GP's own uncertainty rather than replacing it. The cost is visible in the numbers: slightly wider than Analytic and a higher coverage-std across repeats (0.085 vs 0.069) because the calibration split (~20 points) is small — worth naming as a limitation, not hiding it, and worth revisiting if/when the adaptive-sampling loop (Theme 7) grows the dataset past 129 points.

## What to bring to the mentor

Three GPR uncertainty methods tested against the current baseline (analytic), all on real data, all on the two KPIs already flagged by Amr's highlighting. Recommendation is normalized conformal, for the reason above — open to defending Analytic instead if the mentor prioritises interval sharpness over the distribution-free guarantee, since the numeric gap between the two is small (about 13–14% wider, not multiples).
