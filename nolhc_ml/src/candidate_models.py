"""19 benchmark regressors (nolhc_ml_engine_spec.md §8.2)."""

from __future__ import annotations

from sklearn.ensemble import (
    AdaBoostRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel as C
from sklearn.gaussian_process.kernels import Matern, RBF
from sklearn.linear_model import BayesianRidge, ElasticNet, Lasso, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures
from sklearn.svm import SVR
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor

CANDIDATE_MODELS = {
    "gpr_rbf": GaussianProcessRegressor(
        kernel=C(1.0) * RBF(length_scale=1.0),
        n_restarts_optimizer=10,
        normalize_y=True,
        random_state=42,
    ),
    "gpr_matern": GaussianProcessRegressor(
        kernel=C(1.0) * Matern(length_scale=1.0, nu=1.5),
        n_restarts_optimizer=10,
        normalize_y=True,
        random_state=42,
    ),
    "xgboost": XGBRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
    ),
    "lightgbm": LGBMRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_samples=5,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    ),
    "catboost": CatBoostRegressor(
        iterations=300,
        depth=4,
        learning_rate=0.05,
        l2_leaf_reg=3.0,
        random_seed=42,
        verbose=0,
    ),
    "gradient_boosting": GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_split=5,
        random_state=42,
    ),
    "random_forest": RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    ),
    "extra_trees": ExtraTreesRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    ),
    "svr_rbf": SVR(kernel="rbf", C=10.0, epsilon=0.1, gamma="scale"),
    "svr_poly": SVR(kernel="poly", degree=3, C=5.0, epsilon=0.1, gamma="scale"),
    "poly_deg2": Pipeline(
        [
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("ridge", Ridge(alpha=10.0)),
        ]
    ),
    "poly_deg3": Pipeline(
        [
            ("poly", PolynomialFeatures(degree=3, include_bias=False)),
            ("ridge", Ridge(alpha=100.0)),
        ]
    ),
    "ridge": Ridge(alpha=1.0),
    "lasso": Lasso(alpha=0.01, max_iter=5000),
    "elastic_net": ElasticNet(alpha=0.01, l1_ratio=0.5, max_iter=5000),
    "bayesian_ridge": BayesianRidge(),
    "knn": KNeighborsRegressor(n_neighbors=7, weights="distance"),
    "mlp": MLPRegressor(
        hidden_layer_sizes=(128, 64),
        activation="relu",
        max_iter=500,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.15,
    ),
    "adaboost": AdaBoostRegressor(
        n_estimators=200,
        learning_rate=0.05,
        random_state=42,
    ),
}
