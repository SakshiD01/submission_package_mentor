# Uncertainty-Aware, Batch-Sequential Retraining Loop — SOTA Review (Task 1)

**Version:** 0.1 (draft for confirmation)
**Owner:** Sakshi (lead) — for Nila's review against Task 2 scaffolding choices
**Status:** Draft — content complete for 5 of 6 themes against verified sources; see "Sources I could not access" before this is finalised
**Relates to:** `uq_active_learning_loop_spec.md` §4

---

## 0. Sources I could not access (read this before the rest)

Per §4.3 of the spec, this review is required to build on, not re-derive, two existing documents:

1. `paper/icml2026/section_2_3_literature_themes.md` — **used.** I don't have a file by this exact path, but its content (five themes: ML surrogates for expensive simulation, LHS design, stacking, conformal/GPR uncertainty, DES-ML analogues) matches `Section_2.3_Five_Theme_Paragraphs.docx`, which I have reviewed in full. Everything below assumes that ground is already covered and does not restate it.
2. `docs/ManualScript/ML surrogates replacing simulation in supply chains.docx` ("the Analytics Life work") — **not available to me.** This file isn't in the folder I have access to. I can't confirm what it covers, so I can't guarantee zero overlap with it. Before this doc is finalised, either send me that file or have Nila spot-check for redundancy.
3. `NOLHC_ML_Engine_Due_Diligence_Report.md` (Appendix A, Objective 4) — **not available to me.** §4.2 of the spec asks the gist to cross-reference "Objective 4." I have not seen this report and will not invent what Objective 4 says. The gist below states the contribution on its own terms; add the cross-reference once one of you can paste me the relevant paragraph, or I can redo it in five minutes once I have the file.

Everything else below is built from sources I found and independently verified against publisher/arXiv/DOI records this session — not from memory. Full citation details are in §7.

---

## 1. The gist (half-to-one page)

**Where the field stands.** Three literatures run in parallel and none of them talk to each other. First, *model-native uncertainty*: RF jackknife variance, quantile regression forests, and NGBoost give tree ensembles a real per-prediction variance instead of a single fixed interval; deep/bootstrap ensembles reach similar input-dependent uncertainty through model disagreement; jackknife+/CV+ and Mondrian conformal variants improve on the split-conformal approach this engine already has, either by recovering wasted calibration data or by handling KPIs on very different scales consistently. Second, *active/batch-sequential design*: diversity-aware batch selection (determinantal point processes, greedy core-set/max-min) and batch-sequential calibration for stochastic simulators show that choosing where to spend the next expensive simulation run beats a fixed one-shot design — but always for a single simulator being built, never for one already frozen and shipped. Third, *novelty detection and noise separation*: Mahalanobis/one-class-SVM/isolation-forest novelty detection flags inputs outside a training distribution, with an explicit curse-of-dimensionality warning at small n relative to d; stochastic kriging (plus its common-random-numbers extension) and batch-means analysis show how to keep DES replication noise statistically separate from metamodel error rather than folding both into one term.

**What doesn't exist.** No source found couples all three into one loop that (a) gets its uncertainty signal from the model family actually in production for each KPI — tree-native where trees won, conformal where GPR/ElasticNet/SVR won — rather than assuming one model family throughout; (b) uses that same signal both to choose the next *proposed* DES batch and to vet a *live* scenario request arriving after deployment, under one shared threshold; and (c) does this at the specific, awkward scale this engine actually sits at — n≈130, d=35, a near-orthogonal LHS design rather than organically collected data, and a simulator that is manually operated, not an API. Every method reviewed here is demonstrated at a different scale, on a single homogeneous model family, or only at design time.

**Our contribution.** One trust score — per-KPI predictive variance, computed by whichever native or conformal method matches that KPI's winning model, plus a novelty term against the 35-dim training hull — drives two entry points of a single batch-sequential loop: proposed candidates before deployment, and live requests after it. *[Objective 4 cross-reference to be added once the due-diligence report is available to me — see §0.]*

---

## 2. Theme 1 — Native uncertainty for tree ensembles (RF jackknife, QRF, NGBoost)

| Paper | What it gives |
|---|---|
| Wager, Hastie and Efron (2014) | Infinitesimal-jackknife variance from bootstrap covariance between trees and predictions — a genuine per-point standard error for Random Forest, not a fixed band |
| Meinshausen (2006) | Quantile regression forests — full conditional distribution at each leaf, any quantile, not just the mean |
| Duan et al. (2020) | NGBoost — reframes gradient boosting as distributional regression via natural gradients |

**For this engine specifically:** `CV_Best_Models_Per_Target.md` shows ExtraTrees wins `TT_OB_Agri`, `TT_IB_Agri`, `TT_OB_LB`, and `TT_OB_DR`; GradientBoosting wins `WT_OB_A_GB-Ross`. These three methods are directly pluggable onto already-registered winners for at least five of the twenty KPIs, with zero change to which model is selected — only how its uncertainty is read out.

**What doesn't exist yet:** none of these three methods has been applied inside a per-KPI bank where *some* outputs are won by trees and others by GPR, ElasticNet, or SVR (as this engine's are — see `cv_best_model_per_target.csv`). A uniform trust-score contract across mixed model families, which is what this engine actually needs, isn't addressed by any one of them alone.

---

## 3. Theme 2 — Ensemble-based uncertainty (bootstrap ensembles, deep ensembles)

| Paper | What it gives |
|---|---|
| Lakshminarayanan, Pritzel and Blundell (2017) | Deep ensembles — prediction spread across independently trained networks approximates epistemic uncertainty |
| Yang and Yee (2024) | Extends the same logic to multi-output regression specifically |

**For this engine specifically:** at n=129 (103 after the holdout split), bootstrap-refitting the existing 19-model candidate benchmark on 20-50 resamples costs seconds on a laptop, not the GPU time deep ensembles assume. It's a cheap, almost-free second UQ signal to cross-check against Theme 1's tree-native variance.

**What doesn't exist yet:** both papers validate ensemble disagreement on deep nets with large datasets. Neither tests it as a UQ signal for a bench of classical regressors under an n=129, d=35, space-filling (not randomly collected) design — the small-n, structured-design regime this engine actually sits in.

---

## 4. Theme 3 — Conformal prediction, beyond split-conformal

| Paper | What it gives |
|---|---|
| Barber, Candès, Ramdas and Tibshirani (2021) | Jackknife+/CV+ — folds calibration into cross-validation instead of holding out a fixed split, recovering data the current split-conformal approach spends and never reuses |
| Papadopoulos, Gammerman and Vovk (2008) | Normalized nonconformity measures — scales interval width by a per-point difficulty estimate, addressing heteroscedasticity |
| Boström, Johansson and Löfström (2021) | Mondrian conformal predictive distributions — group-conditional coverage guarantees, not just marginal |

**For this engine specifically:** the current pipeline spends 26 of 129 rows purely on holdout/calibration and never lets the model train on them (`ML_Pipeline_Specification.md` §Step B). Jackknife+/CV+ would recover that ~20% for training without giving up the marginal coverage guarantee. Normalized/Mondrian variants matter because the twenty KPIs live on wildly different scales — utilisation in [0,1] versus `TT_IB_LB` in tens of hours — and a single coverage rule currently has to be re-tuned per KPI by hand.

**What doesn't exist yet:** no source combines CV+-style calibration-set recovery *and* Mondrian/normalized heteroscedastic weighting in one procedure for a multi-output, small-n regression bank. Each is demonstrated separately, usually on single-output problems.

---

## 5. Theme 4 — Batch/active learning for expensive simulations, diversity-aware

| Paper | What it gives |
|---|---|
| Bıyık, Wang, Anari and Sadigh (2019) | Determinantal-point-process batch selection — picks a diverse batch, not just the K most-uncertain points |
| Sener and Savarese (2018) | Core-set / greedy k-center (equivalent to greedy max-min) — the classical diversity-batch baseline |
| Sürer (2025) | Batch-sequential design for stochastic simulators — formalises replicate-vs-explore trade-off under a fixed budget |
| Bajracharya, Toledo-Marín, Fox, Jha and Wang (2024) | Active learning of surrogates for expensive physics simulations — training-run selection beats uniform sampling under a query budget |

**For this engine specifically:** top-K uncertainty sampling over the 35-dim input space will cluster candidates in whichever congestion regime the surrogate currently understands least — e.g. all near the transit-check threshold where `TT_IB_LB` jumps from 26 h to 68.5 h — and burn an entire DES batch confirming one region instead of covering several. This is the exact failure mode diversity-aware batching exists to prevent.

**What doesn't exist yet:** none of the four is demonstrated on a bounded, physically-constrained input space — route-share fractions that must sum to 1, check-time minutes, integer staffing counts — where "diversity" has to respect domain constraints, not just Euclidean spread. A domain-constrained diversity metric for a design space shaped like this one is unaddressed.

---

## 6. Theme 5 — Novelty/drift detection as OOD against the 35-dim training hull

| Paper | What it gives |
|---|---|
| Lee, Lee, Lee and Shin (2018) | Mahalanobis-distance OOD detection against a fitted class-conditional Gaussian |
| Liu, Ting and Zhou (2008) | Isolation forest — path-length-based, less distance-dependent than Mahalanobis/OCSVM |
| Schölkopf, Platt, Shawe-Taylor, Smola and Williamson (2001) | One-class SVM — the classical boundary-fitting baseline |
| Zimek, Schubert and Kriegel (2012) | Survey explaining why distance-based outlier/novelty methods lose discriminative power as dimensionality grows relative to sample size |

**For this engine specifically:** at n=129, d=35, Zimek et al. is the load-bearing citation, not a side note — it explains *why* plain Mahalanobis distance is a risky default here, and argues for either a reduced-dimension test (e.g. only the inputs a given scenario family actually varies, per `Mentor_UI_Parameter_Governance_Spec.md`'s editable/locked matrix) or a less distance-dependent method like isolation forest.

**What doesn't exist yet:** no source benchmarks these methods specifically at n≈130, d≈35 against a near-orthogonal-LHS-shaped training distribution rather than organically collected data. Whether the LHS's deliberate space-filling structure makes novelty detection easier or harder than on random data is an open, unstudied question — flag it as a real risk in the gist, not a solved problem.

---

## 7. Theme 6 — DES replication noise alongside ML metamodel uncertainty

| Paper | What it gives |
|---|---|
| Ankenman, Nelson and Staum (2010) | Stochastic kriging — partitions prediction uncertainty into intrinsic (replication) and extrinsic (metamodel) variance instead of one combined error term |
| Chen, Ankenman and Nelson (2012) | Extends stochastic kriging with common random numbers (CRN) across design points |
| Alexopoulos and Goldsman (2004) | Batch-means variance estimation from simulation output — the general-purpose tool when a GP-specific method (stochastic kriging) doesn't apply |

**For this engine specifically:** every one of the 129 design points was already run with five independent DES replications and reported as a mean (`Experimental_Analysis_Report_Mentor.md` §3.2, Layer 1). Within-point replication variance is sitting in the raw AnyLogic output right now and simply isn't being computed or retained — this is an unused-data gap, not a missing-data gap. A batch-means pass over the existing five-replication outputs would give an intrinsic-noise estimate per KPI without a single new DES run.

**What doesn't exist yet:** stochastic kriging is GP-specific, but this engine's winning models per KPI are a mix of tree ensembles, GPR, ElasticNet and SVR. Extending intrinsic/extrinsic variance decomposition to a *heterogeneous* per-KPI model bank — where the winning family differs by output — is new; nothing reviewed here does it.

---

## 8. What this means for Task 2 (informs, doesn't replace, §5.1)

- Themes 1 and 3 jointly answer "which UQ estimator per model family": tree winners get jackknife or QRF; non-tree winners keep the conformal wrapper, upgraded to jackknife+/CV+ plus normalized/Mondrian weighting.
- Theme 4 argues the v0 batch selection logic should not be simple top-K on trust score — it should be top-K *filtered through* a diversity constraint (greedy max-min is the cheapest correct baseline; DPP if the budget allows).
- Theme 5 argues the novelty term should not default to raw Mahalanobis distance at d=35 — start with isolation forest, or restrict the distance test to the scenario-family-specific editable subset.
- Theme 6 is a near-zero-cost win available immediately: a batch-means pass on the existing 5-replication-per-point data, independent of everything else in this loop, would sharpen every other estimate above it.

---

## 9. References (new — verified against publisher/arXiv/DOI records, not from memory)

Alexopoulos, C. and Goldsman, D. (2004) 'To batch or not to batch?', ACM Transactions on Modeling and Computer Simulation, 14(1), pp. 76–114. doi: 10.1145/974734.974738.

Ankenman, B., Nelson, B.L. and Staum, J. (2010) 'Stochastic kriging for simulation metamodeling', Operations Research, 58(2), pp. 371–382. doi: 10.1287/opre.1090.0754.

Bajracharya, P., Toledo-Marín, J.Q., Fox, G., Jha, S. and Wang, L. (2024) 'Feasibility study on active learning of smart surrogates for scientific simulations', arXiv preprint arXiv:2407.07674.

Barber, R.F., Candès, E.J., Ramdas, A. and Tibshirani, R.J. (2021) 'Predictive inference with the jackknife+', Annals of Statistics, 49(1), pp. 486–507. doi: 10.1214/20-AOS1965.

Bıyık, E., Wang, K., Anari, N. and Sadigh, D. (2019) 'Batch active learning using determinantal point processes', arXiv preprint arXiv:1906.07975.

Boström, H., Johansson, U. and Löfström, T. (2021) 'Mondrian conformal predictive distributions', Proceedings of Machine Learning Research, 152 (COPA 2021), pp. 1–13.

Chen, X., Ankenman, B.E. and Nelson, B.L. (2012) 'The effects of common random numbers on stochastic kriging metamodels', ACM Transactions on Modeling and Computer Simulation, 22(2), Article 7. doi: 10.1145/2133390.2133391. [Volume/issue from standard citation records; not independently re-verified beyond the confirmed DOI this session — worth a quick check before submission.]

Duan, T., Avati, A., Ding, D.Y., Thai, K.K., Basu, S., Ng, A.Y. and Schuler, A. (2020) 'NGBoost: natural gradient boosting for probabilistic prediction', Proceedings of the 37th International Conference on Machine Learning, PMLR 119, pp. 2690–2700.

Lakshminarayanan, B., Pritzel, A. and Blundell, C. (2017) 'Simple and scalable predictive uncertainty estimation using deep ensembles', Advances in Neural Information Processing Systems 30 (NeurIPS 2017), pp. 6402–6413.

Lee, K., Lee, K., Lee, H. and Shin, J. (2018) 'A simple unified framework for detecting out-of-distribution samples and adversarial attacks', Advances in Neural Information Processing Systems 31 (NeurIPS 2018).

Liu, F.T., Ting, K.M. and Zhou, Z.-H. (2008) 'Isolation forest', Proceedings of the 8th IEEE International Conference on Data Mining (ICDM), pp. 413–422. doi: 10.1109/ICDM.2008.17.

Meinshausen, N. (2006) 'Quantile regression forests', Journal of Machine Learning Research, 7, pp. 983–999.

Papadopoulos, H., Gammerman, A. and Vovk, V. (2008) 'Normalized nonconformity measures for regression conformal prediction', Proceedings of the 26th IASTED International Conference on Artificial Intelligence and Applications, pp. 64–69.

Schölkopf, B., Platt, J.C., Shawe-Taylor, J., Smola, A.J. and Williamson, R.C. (2001) 'Estimating the support of a high-dimensional distribution', Neural Computation, 13(7), pp. 1443–1471. doi: 10.1162/089976601750264965.

Sener, O. and Savarese, S. (2018) 'Active learning for convolutional neural networks: a core-set approach', International Conference on Learning Representations (ICLR 2018).

Sürer, Ö. (2025) 'Batch sequential experimental design for calibration of stochastic simulation models', Technometrics, 68(1). doi: 10.1080/00401706.2025.2520860.

Wager, S., Hastie, T. and Efron, B. (2014) 'Confidence intervals for random forests: the jackknife and the infinitesimal jackknife', Journal of Machine Learning Research, 15(1), pp. 1625–1651.

Yang, S. and Yee, K. (2024) 'Towards reliable uncertainty quantification via deep ensemble in multi-output regression task', Engineering Applications of Artificial Intelligence, 133, 107871. doi: 10.1016/j.engappai.2024.107871.

Zimek, A., Schubert, E. and Kriegel, H.-P. (2012) 'A survey on unsupervised outlier detection in high-dimensional numerical data', Statistical Analysis and Data Mining, 5(5), pp. 363–387. doi: 10.1002/sam.11161.

---

*Confirm or edit before this feeds Task 2's UQ-estimator selection (spec §6, row 3).*
