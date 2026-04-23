"""
80/20 index split — must match run_step1_cv.py / spec Step 3.
"""

from __future__ import annotations

import numpy as np


def train_test_indices(
    n: int,
    *,
    seed: int = 42,
    train_frac: float = 0.8,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.RandomState(seed)
    idx = rng.permutation(n)
    n_train = int(round(train_frac * n))
    return idx[:n_train], idx[n_train:]
