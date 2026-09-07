# NOLHC ML Engine — Post-Brexit Border Capacity Surrogate

A machine-learning surrogate of an AnyLogic discrete-event simulation of Irish
port border control, built so that capacity questions can be answered in
milliseconds instead of minutes, with an explicit statement of how far each
answer can be trusted.

MSc Business Analytics, Business Consulting Project — Maynooth University, 2026.

---

## The problem

Post-Brexit, goods moving between Ireland and Great Britain pass through customs
and Department of Agriculture (DAFM) checks at Dublin and Rosslare. Planners need
to know what happens to transit times, queue lengths and inspection-resource
utilisation when volumes, staffing, bay counts or inspection rates change.

The AnyLogic discrete-event model answers that, but each configuration takes
minutes to run and the software is proprietary and licensed. That cost rules out
the thing planners actually want: sweeping hundreds of scenarios, or moving a
slider and seeing the effect immediately.

A surrogate — a model trained on simulation output that predicts what the
simulation would have said — removes the cost. It also introduces a risk: a
surrogate will answer confidently anywhere it is asked, including in regions of
the input space it has never seen. Most of the engineering here addresses that
second problem rather than the first.

## What this delivers

- **A trained surrogate for all 20 simulation KPIs**, each with its own model
  family selected on evidence rather than a single algorithm applied uniformly.
- **A prediction interval and a trust verdict on every prediction**, so an
  unreliable answer is visible as unreliable rather than indistinguishable from
  a good one.
- **A browser interface** where a non-technical planner sets a scenario and reads
  the KPIs, the drivers behind them (SHAP) and the confidence attached to them.
- **A loop that grows its own training set**: the system proposes the scenarios
  it is least certain about, those are run in AnyLogic, the results are ingested
  and the models retrained.

## Results

Trained 2 April 2026 on the 129-run Nearly Orthogonal Latin Hypercube design —
35 continuous inputs, 20 KPIs, pairwise input correlations held within ±0.3.
Split 103/26, seed 42, 5-fold cross-validation, 19 candidate model families
benchmarked per KPI.

| Measure | Value |
|---|---|
| Mean R² across all 20 KPIs | **0.736** |
| R² range | −0.117 to 0.977 |
| KPIs where a stacked ensemble beat every individual model | 8 of 20 |
| Per-KPI confidence recorded in the registry | 6 high, 9 good, 3 poor, 2 low |

Selected families vary by KPI, which is the point of benchmarking rather than
assuming: stacking (8), Matérn-kernel GPR (3), Extra Trees (2), and one each of
RBF GPR, Random Forest, CatBoost, SVR, Ridge, Lasso and Elastic Net.

**The weak KPIs are reported, not hidden.** Direct-route inbound transit time has
a negative cross-validated R² (−0.117) — the model is worse than predicting the
mean, and is marked `poor` in the registry so the UI can flag it. Three KPIs are
`poor` and two `low`. A surrogate that claimed uniform accuracy across 20
heterogeneous outputs would not be believable.

## Repository layout

| Path | What it is | Status |
|---|---|---|
| `nolhc_ml/` | The engine: per-KPI model registry (`models/v1/`), FastAPI inference API, parameter UI | **Authoritative** |
| `experimenting_ml/` | Research pipeline (CV, model selection, statistical testing, SHAP, conformal calibration) plus the uncertainty/novelty/self-extension loop and the decision-intelligence UI | **Authoritative** |
| `loop/des_backend/` | Synthetic DES backend and ground-truth GPs for testing the loop without AnyLogic | supporting |
| `brexit_ml/` | Phase 1 Ireland↔GB corridor surrogate, trained on an earlier unstructured run export | **Superseded**, kept for provenance |
| `docs/` | Engineering specs, figures, due-diligence report | reference |

Trained artefacts are committed. A fresh clone serves predictions without
retraining anything.

## Quick start

Python 3.8.10, one interpreter for all three packages, installed from the
committed lock files. `requirements.txt` holds looser ranges for the hosted
deployment — **use the lock file for reproduction.**

```bash
cd nolhc_ml            # then experimenting_ml, then optionally brexit_ml
python3.8 -m venv .venv
./.venv/bin/pip install -r requirements.lock.txt
```

Confirm the clone is sound:

```bash
cd nolhc_ml         && ./.venv/bin/python -m pytest -q   #   9 passed
cd experimenting_ml && ./.venv/bin/python -m pytest -q   # 172 passed
cd brexit_ml        && ./.venv/bin/python -m pytest -q   #  52 passed, 1 skipped
```

Run the decision-intelligence UI:

```bash
cd experimenting_ml
./.venv/bin/python run_ui_inference_api.py --port 8000
#   simulator        http://localhost:8000/UI/index.html
#   settings         http://localhost:8000/UI/settings.html
#   operator console http://localhost:8000/UI/operator.html
```

Full detail, including regeneration commands and Windows equivalents, is in
[`REPRODUCE.md`](REPRODUCE.md).

## How it works

**Model selection.** Every KPI is fitted with 19 candidate families spanning
linear, kernel, tree-ensemble, boosting, neighbour and Gaussian-process methods.
Selection uses a composite of cross-validated error, held-out error and paired
statistical testing, with Friedman and Nemenyi tests and critical-difference
diagrams to establish whether apparent differences are real. Where a stacked
ensemble of the strongest bases beats them individually, the stack is registered.

**Uncertainty.** Each prediction carries an interval, produced by one of three
routes according to the registered family: jackknife over the bagged estimators
for tree ensembles, the native posterior standard deviation for Gaussian
processes, and split-conformal calibration otherwise. Conformal coverage adapts
to model quality — a well-fitted KPI gets a 90% interval, a weaker one 95% or
99%, so the interval widens where the model deserves less trust.

**Novelty.** An Isolation Forest over the 35-dimensional input space scores how
far a requested scenario sits from the training design. Interval width and
novelty combine into a trust score, thresholded at the 90th percentile of
in-sample scores, which drives an accept/verify verdict on the KPI card.

**Self-extension.** The loop proposes candidate scenarios, scores them, flags the
most informative, and exports a run worksheet. Those runs are executed in
AnyLogic Cloud, the results ingested, the affected models retrained and the
uncertainty methods re-checked against the grown data. Three rounds have been
ingested, taking the training set from 129 to 179 rows.

## Limitations

Stated plainly, because a surrogate whose limits are undocumented is not usable
for planning.

- **The AnyLogic simulation is not in this repository.** It is proprietary, and
  the Cloud API is a paid subscription, so the AnyLogic step of the loop is
  driven manually through the dashboard. The 129-run export and every round's
  results CSV are committed; the model itself cannot be.
- **Growth is uneven across KPIs.** Some columns were excluded from rounds for
  unresolved data-quality reasons, so per-KPI training counts range from 129 to
  179 rather than growing uniformly.
- **One ingested round came from a dashboard running a meta-model** rather than
  the full discrete-event simulation. Whether that output is admissible training
  data for this surrogate is an open question with the supervisory team; the
  round is ingested but flagged rather than silently accepted.
- **Conformal coverage is marginal, not conditional.** The stated coverage holds
  on average across the input space, not necessarily within any given region.
- **Novelty detection is joint, not per-dimension.** A scenario extreme in a
  single factor but ordinary overall may not be flagged.

## Author

Sakshi Dhamane — MSc Business Analytics, Maynooth University.
Task allocation between contributors is recorded in the project's implementation
timeline; the technical report documents design decisions, statistical
methodology and open questions in full.
