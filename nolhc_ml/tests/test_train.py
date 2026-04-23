"""Training artifact tests after a full ``train.py`` run (spec §16 Phase 1e)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from training_columns import OUTPUT_COLUMN_ORDER, col_to_slug  # noqa: E402

V1 = ROOT / "models" / "v1"


def _v1_training_matches_current_output_count() -> bool:
    """True when registry reports the same output count as code and last-output artifacts exist."""
    reg_path = V1 / "registry.json"
    if not reg_path.is_file():
        return False
    with open(reg_path, encoding="utf-8") as f:
        reg = json.load(f)
    if int(reg.get("output_targets", 0)) != len(OUTPUT_COLUMN_ORDER):
        return False
    last_slug = col_to_slug(OUTPUT_COLUMN_ORDER[-1])
    return (V1 / f"stack_{last_slug}.pkl").is_file()


@pytest.mark.skipif(
    not _v1_training_matches_current_output_count(),
    reason="Run train.py after code/xlsx match (20 outputs in OUTPUT_COLUMN_ORDER + SimResults).",
)
def test_stack_pkl_exists_for_all_outputs() -> None:
    for raw in OUTPUT_COLUMN_ORDER:
        slug = col_to_slug(raw)
        assert (V1 / f"stack_{slug}.pkl").is_file(), f"missing stack_{slug}.pkl"


@pytest.mark.skipif(
    not _v1_training_matches_current_output_count(),
    reason="Run train.py after code/xlsx match (20 outputs in OUTPUT_COLUMN_ORDER + SimResults).",
)
def test_benchmark_winner_and_registry_stacking_count() -> None:
    reg_path = V1 / "registry.json"
    with open(reg_path, encoding="utf-8") as f:
        reg = json.load(f)
    sw = int(reg["stacking_won_count"])
    assert 0 <= sw <= 20

    valid_winners = None
    for raw in OUTPUT_COLUMN_ORDER:
        slug = col_to_slug(raw)
        bench_path = V1 / f"benchmark_{slug}.json"
        assert bench_path.is_file()
        with open(bench_path, encoding="utf-8") as f:
            bench = json.load(f)
        w = bench["winner"]
        if valid_winners is None:
            valid_winners = set(bench["results"].keys()) | {"stacking"}
        assert w in valid_winners, f"{slug} winner {w!r} not in models+stacking"
