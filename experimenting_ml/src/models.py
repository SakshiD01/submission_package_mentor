"""
Regressors + optional baselines (ML_Pipeline_Specification.md §4.1).

Core set: 19 tuned models. Baselines ``Baseline_Mean`` / ``Baseline_OLS`` are for
sanity checks in paired comparisons (run ``run_baselines_cv.py`` and merge into
``cv_results.json`` if they are not already present from a full CV run).
"""

from __future__ import annotations

import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor
from sklearn.ensemble import (
    AdaBoostRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import (
    ConstantKernel,
    Matern,
    RBF,
    WhiteKernel,
)
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import BayesianRidge, ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.svm import SVR

NEEDS_SCALING = frozenset(
    {
        "GPR_RBF",
        "GPR_Matern",
        "SVR_RBF",
        "SVR_Poly",
        "PolynomialReg_deg2",
        "PolynomialReg_deg3",
        "Ridge",
        "Lasso",
        "ElasticNet",
        "BayesianRidge",
        "KNN",
        "MLP",
        "Baseline_OLS",
    }
)


def get_models() -> dict:
    return {
        "Baseline_Mean": {
            "model": DummyRegressor(strategy="mean"),
            "grid": [{}],
        },
        "Baseline_OLS": {
            "model": LinearRegression(),
            "grid": [{}],
        },
        "GPR_RBF": {
            "model": GaussianProcessRegressor(
                kernel=ConstantKernel(1.0) * RBF(1.0) + WhiteKernel(1e-3),
                normalize_y=True,
                n_restarts_optimizer=2,
                random_state=42,
            ),
            "grid": [{"alpha": [1e-10, 1e-6, 1e-3]}],
        },
        "GPR_Matern": {
            "model": GaussianProcessRegressor(
                kernel=ConstantKernel(1.0) * Matern(nu=1.5) + WhiteKernel(1e-3),
                normalize_y=True,
                n_restarts_optimizer=2,
                random_state=42,
            ),
            "grid": [{"alpha": [1e-10, 1e-6, 1e-3]}],
        },
        "RandomForest": {
            "model": RandomForestRegressor(random_state=42, n_jobs=-1),
            "grid": [
                {
                    "n_estimators": [50, 100, 200],
                    "max_depth": [None, 5, 10],
                    "min_samples_split": [2, 5],
                }
            ],
        },
        "ExtraTrees": {
            "model": ExtraTreesRegressor(random_state=42, n_jobs=-1),
            "grid": [
                {
                    "n_estimators": [50, 100, 200],
                    "max_depth": [None, 5, 10],
                    "min_samples_split": [2, 5],
                }
            ],
        },
        "GradientBoosting": {
            "model": GradientBoostingRegressor(random_state=42),
            "grid": [
                {
                    "n_estimators": [50, 100],
                    "learning_rate": [0.05, 0.1, 0.2],
                    "max_depth": [3, 5],
                }
            ],
        },
        "AdaBoost": {
            "model": AdaBoostRegressor(random_state=42),
            "grid": [{"n_estimators": [50, 100, 200], "learning_rate": [0.5, 1.0]}],
        },
        "XGBoost": {
            "model": xgb.XGBRegressor(
                random_state=42,
                verbosity=0,
                objective="reg:squarederror",
                n_jobs=-1,
            ),
            "grid": [
                {
                    "n_estimators": [50, 100],
                    "learning_rate": [0.05, 0.1],
                    "max_depth": [3, 5, 7],
                }
            ],
        },
        "LightGBM": {
            "model": lgb.LGBMRegressor(random_state=42, verbose=-1, n_jobs=-1),
            "grid": [
                {
                    "n_estimators": [50, 100],
                    "learning_rate": [0.05, 0.1],
                    "num_leaves": [15, 31],
                }
            ],
        },
        "CatBoost": {
            "model": CatBoostRegressor(random_seed=42, verbose=0),
            "grid": [
                {
                    "iterations": [50, 100],
                    "learning_rate": [0.05, 0.1],
                    "depth": [4, 6],
                }
            ],
        },
        "SVR_RBF": {
            "model": SVR(kernel="rbf"),
            "grid": [
                {
                    "C": [0.1, 1, 10, 100],
                    "epsilon": [0.01, 0.1, 0.5],
                    "gamma": ["scale", "auto"],
                }
            ],
        },
        "SVR_Poly": {
            "model": SVR(kernel="poly"),
            "grid": [{"C": [0.1, 1, 10], "degree": [2, 3], "epsilon": [0.01, 0.1]}],
        },
        "PolynomialReg_deg2": {
            "model": Pipeline(
                [("poly", PolynomialFeatures(degree=2)), ("ridge", Ridge())]
            ),
            "grid": [{"ridge__alpha": [0.001, 0.01, 0.1, 1, 10]}],
        },
        "PolynomialReg_deg3": {
            "model": Pipeline(
                [("poly", PolynomialFeatures(degree=3)), ("ridge", Ridge())]
            ),
            "grid": [{"ridge__alpha": [0.001, 0.01, 0.1, 1, 10]}],
        },
        "Ridge": {
            "model": Ridge(),
            "grid": [{"alpha": [0.001, 0.01, 0.1, 1, 10, 100]}],
        },
        "Lasso": {
            "model": Lasso(max_iter=5000),
            "grid": [{"alpha": [0.0001, 0.001, 0.01, 0.1, 1]}],
        },
        "ElasticNet": {
            "model": ElasticNet(max_iter=5000),
            "grid": [
                {"alpha": [0.001, 0.01, 0.1, 1], "l1_ratio": [0.2, 0.5, 0.8]}
            ],
        },
        "BayesianRidge": {
            "model": BayesianRidge(),
            "grid": [
                {
                    "alpha_1": [1e-6, 1e-5],
                    "alpha_2": [1e-6, 1e-5],
                    "lambda_1": [1e-6, 1e-5],
                }
            ],
        },
        "KNN": {
            "model": KNeighborsRegressor(),
            "grid": [
                {
                    "n_neighbors": [3, 5, 7, 10, 15],
                    "weights": ["uniform", "distance"],
                    "p": [1, 2],
                }
            ],
        },
        "MLP": {
            "model": MLPRegressor(random_state=42),
            "grid": [
                {
                    "hidden_layer_sizes": [(50,), (100,), (50, 50)],
                    "alpha": [0.0001, 0.001],
                    "max_iter": [500],
                }
            ],
        },
    }
