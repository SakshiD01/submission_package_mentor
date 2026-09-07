"""Unit tests for training helpers (Task 5)."""

import pytest

import train as train_mod
from train import col_to_slug, infer_output_unit, run_training
from training_columns import (
    OUTPUT_COLUMN_ORDER,
    PHASE_1_OUTPUT_COUNT,
    output_phase_index,
)


def test_col_to_slug_examples():
    assert col_to_slug("Transportation time agri exportto GB") == "transportation_time_agri_exportto_gb"
    assert col_to_slug("DDAFM insp bay utilisation") == "ddafm_insp_bay_utilisation"
    assert col_to_slug("AP avg WT on im at D") == "ap_avg_wt_on_im_at_d"
    assert len(col_to_slug("a" * 200)) <= 80


def test_infer_output_unit():
    assert infer_output_unit("Total doc check cost ex trucks from IR to GBW") == "EUR"
    assert infer_output_unit("Trucks vessel queue length liv to D") == "trucks"
    assert infer_output_unit("DDAFM insp bay utilisation") == "fraction"
    assert infer_output_unit("Remaining shelflife cat import from GB") == "fraction"
    assert infer_output_unit("Transportation time agri import from GB") == "hours"


def test_output_phase_indices():
    assert output_phase_index(0) == 1
    assert output_phase_index(PHASE_1_OUTPUT_COUNT - 1) == 1
    assert output_phase_index(PHASE_1_OUTPUT_COUNT) == 2
    assert output_phase_index(len(OUTPUT_COLUMN_ORDER) - 1) == 2
    assert OUTPUT_COLUMN_ORDER[PHASE_1_OUTPUT_COUNT].startswith("Transportation time exportto EULB")


def test_run_training_synthetic(tmp_path, monkeypatch):
    """End-to-end train on tiny synthetic data (not representative of real accuracy)."""
    try:
        import xgboost  # noqa: F401
    except Exception as exc:
        pytest.skip(f"xgboost not loadable ({exc}); on macOS try: brew install libomp")

    import numpy as np
    import pandas as pd

    from training_columns import OUTPUT_COLUMN_ORDER, TRAINING_COLUMN_ORDER

    monkeypatch.setattr(
        train_mod,
        "XGB_PARAMS",
        {**train_mod.XGB_PARAMS, "n_estimators": 40, "max_depth": 3},
    )
    monkeypatch.setattr(
        train_mod,
        "XGB_CLF_PARAMS",
        {**train_mod.XGB_CLF_PARAMS, "n_estimators": 40, "max_depth": 3},
    )

    rng = np.random.default_rng(42)
    n = 45
    X = rng.normal(size=(n, 153))
    Y = rng.normal(size=(n, 136))
    Y[:, 50:] = 0.0

    X_df = pd.DataFrame(X, columns=TRAINING_COLUMN_ORDER)
    Y_df = pd.DataFrame(Y, columns=OUTPUT_COLUMN_ORDER)

    processed = tmp_path / "processed"
    models = tmp_path / "models" / "v1"
    processed.mkdir(parents=True)
    X_df.to_parquet(processed / "X_train.parquet", index=False)
    Y_df.to_parquet(processed / "Y_train.parquet", index=False)

    reg = run_training(
        xlsx_path=tmp_path / "no_xlsx_here.xlsx",
        processed_dir=processed,
        models_dir=models,
        prefer_parquet=True,
    )
    assert reg["training_runs"] == n
    assert (models / "registry.json").is_file()
    assert (models / "scaler_X.pkl").is_file()
    assert len(reg["outputs"]) == 136
