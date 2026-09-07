"""
GPR uncertainty-method comparison experiment.

Compares 4 uncertainty-quantification approaches for Gaussian Process Regression
on the two KPIs the mentor flagged (TT_IB_LB, WT_IB_LB) — both are GPR-won in
production and both are the worst-performing KPIs among GPR's wins.

Methods:
  A. Analytic   — native closed-form GP posterior std (single MLE kernel fit).
  B. Bayesian   — hyperparameter-grid marginalisation over length-scale
                  (mixture-of-GPs, weighted by marginal likelihood) — a
                  lightweight stand-in for full HMC/VI fully-Bayesian GP
                  (Lalchand & Rasmussen, AABI 2020), since gpytorch/pymc are
                  not available in this environment.
  C. Ensemble   — bootstrap ensemble of GPs (Christiansen, Ronne & Hammer,
                  2024, use noisy-label ensembles; here we use bootstrap
                  resampling of the training rows, a standard ensemble
                  variant), uncertainty = law-of-total-variance across members.
  D. Conformal  — split-conformal, normalised nonconformity score
                  (|residual| / GP std) so interval width scales with the
                  GP's own local uncertainty, unlike the fixed marginal
                  half-width currently in conformal_predict.py.

Evaluated over 20 repeated random 80/20 train/test splits per KPI (129 points
total, so a single split is not reliable) and averaged.
"""
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

RNG_SEED = 42
N_REPEATS = 20
Z_90 = 1.6448536269514722  # two-sided 90% normal quantile
TARGET_COVERAGE = 0.90

X_raw = pd.read_csv("/tmp/build/X_129.csv").drop(columns=["factor name"])
Y = pd.read_csv("/tmp/build/Y_129.csv")

TARGETS = {
    "TT_IB_LB": "Routes | Landbridge | TT_IB_LB",
    "WT_IB_LB": "Routes | Landbridge | WT_IB_LB",
}


def make_kernel():
    return ConstantKernel(1.0, (1e-2, 1e3)) * Matern(length_scale=1.0, nu=1.5) + WhiteKernel(
        noise_level=1.0, noise_level_bounds=(1e-3, 1e1)
    )


def fit_gpr(Xtr, ytr, n_restarts=3, length_scale_init=None):
    kernel = make_kernel()
    if length_scale_init is not None:
        # override the Matern length_scale starting point for the hyperparameter-grid method
        kernel.k1.k2.length_scale = length_scale_init
    gpr = GaussianProcessRegressor(
        kernel=kernel, normalize_y=True, n_restarts_optimizer=n_restarts, random_state=RNG_SEED
    )
    gpr.fit(Xtr, ytr)
    return gpr


def method_analytic(Xtr, ytr, Xte):
    gpr = fit_gpr(Xtr, ytr, n_restarts=5)
    mean, std = gpr.predict(Xte, return_std=True)
    return mean, std


def method_bayesian_grid(Xtr, ytr, Xte, grid_multipliers=(0.5, 1.0, 2.0)):
    base = fit_gpr(Xtr, ytr, n_restarts=5)
    base_ls = base.kernel_.k1.k2.length_scale
    means, stds, llhs = [], [], []
    for m in grid_multipliers:
        g = fit_gpr(Xtr, ytr, n_restarts=1, length_scale_init=base_ls * m)
        mean, std = g.predict(Xte, return_std=True)
        means.append(mean)
        stds.append(std)
        llhs.append(g.log_marginal_likelihood_value_)
    means = np.array(means)          # (K, n_test)
    stds = np.array(stds)
    llhs = np.array(llhs)
    w = np.exp(llhs - llhs.max())
    w = w / w.sum()
    mix_mean = np.average(means, axis=0, weights=w)
    within_var = np.average(stds ** 2, axis=0, weights=w)
    between_var = np.average((means - mix_mean) ** 2, axis=0, weights=w)
    mix_std = np.sqrt(within_var + between_var)
    return mix_mean, mix_std


def method_ensemble_bootstrap(Xtr, ytr, Xte, n_members=12, rng=None):
    rng = rng or np.random.default_rng(RNG_SEED)
    n = len(Xtr)
    means, stds = [], []
    for _ in range(n_members):
        idx = rng.integers(0, n, size=n)
        g = fit_gpr(Xtr[idx], ytr[idx], n_restarts=1)
        mean, std = g.predict(Xte, return_std=True)
        means.append(mean)
        stds.append(std)
    means = np.array(means)
    stds = np.array(stds)
    ens_mean = means.mean(axis=0)
    within_var = (stds ** 2).mean(axis=0)
    between_var = means.var(axis=0)
    ens_std = np.sqrt(within_var + between_var)
    return ens_mean, ens_std


def method_conformal_normalized(Xtr, ytr, Xte, coverage=TARGET_COVERAGE, rng=None):
    rng = rng or np.random.default_rng(RNG_SEED)
    Xtr2, Xcal, ytr2, ycal = train_test_split(Xtr, ytr, test_size=0.2, random_state=RNG_SEED)
    gpr = fit_gpr(Xtr2, ytr2, n_restarts=5)
    mean_cal, std_cal = gpr.predict(Xcal, return_std=True)
    std_cal = np.maximum(std_cal, 1e-6)
    scores = np.abs(ycal - mean_cal) / std_cal
    n = len(scores)
    q_level = min(1.0, np.ceil((n + 1) * coverage) / n)
    q = np.quantile(scores, q_level)
    mean_te, std_te = gpr.predict(Xte, return_std=True)
    half_width = q * std_te
    return mean_te, half_width  # note: this is already the half-width, not a std


def evaluate(y_true, mean, spread, z=Z_90, spread_is_half_width=False):
    half = spread if spread_is_half_width else z * spread
    lower, upper = mean - half, mean + half
    coverage = float(np.mean((y_true >= lower) & (y_true <= upper)))
    width = float(np.mean(2 * half))
    return coverage, width


results = []
scaler_cache = {}

for kpi_label, col in TARGETS.items():
    y = Y[col].values.astype(float)
    X = X_raw.values.astype(float)

    method_cov = {"Analytic": [], "Bayesian (grid)": [], "Ensemble (bootstrap)": [], "Conformal (normalized)": []}
    method_wid = {"Analytic": [], "Bayesian (grid)": [], "Ensemble (bootstrap)": [], "Conformal (normalized)": []}

    for rep in range(N_REPEATS):
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=rep)
        scaler = StandardScaler().fit(Xtr)
        Xtr_s = scaler.transform(Xtr)
        Xte_s = scaler.transform(Xte)
        rng = np.random.default_rng(rep)

        mean, std = method_analytic(Xtr_s, ytr, Xte_s)
        c, w = evaluate(yte, mean, std)
        method_cov["Analytic"].append(c)
        method_wid["Analytic"].append(w)

        mean, std = method_bayesian_grid(Xtr_s, ytr, Xte_s)
        c, w = evaluate(yte, mean, std)
        method_cov["Bayesian (grid)"].append(c)
        method_wid["Bayesian (grid)"].append(w)

        mean, std = method_ensemble_bootstrap(Xtr_s, ytr, Xte_s, rng=rng)
        c, w = evaluate(yte, mean, std)
        method_cov["Ensemble (bootstrap)"].append(c)
        method_wid["Ensemble (bootstrap)"].append(w)

        mean, half = method_conformal_normalized(Xtr_s, ytr, Xte_s, rng=rng)
        c, w = evaluate(yte, mean, half, spread_is_half_width=True)
        method_cov["Conformal (normalized)"].append(c)
        method_wid["Conformal (normalized)"].append(w)

        print(f"{kpi_label} rep {rep+1}/{N_REPEATS} done", flush=True)

    for m in method_cov:
        results.append({
            "KPI": kpi_label,
            "Method": m,
            "Mean coverage (target 90%)": np.mean(method_cov[m]),
            "Std coverage across repeats": np.std(method_cov[m]),
            "Mean interval width": np.mean(method_wid[m]),
        })

res_df = pd.DataFrame(results)
res_df.to_csv("/tmp/build/gpr_uq_experiment_results.csv", index=False)
print(res_df.to_string(index=False))
