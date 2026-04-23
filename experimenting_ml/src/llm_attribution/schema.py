"""
Fixed JSON schema for LLM attribution layer — only structured facts, no PDF scrape.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ShapFeature(BaseModel):
    name: str
    mean_abs_shap: float
    rank: int


class Interval90(BaseModel):
    """Symmetric band from conformal JSON for the selected model (nominal coverage ≈ 90%)."""

    nominal_coverage: float = Field(description="Requested nominal level (e.g. 0.9)")
    half_width: float = Field(description="± width in target units (matches quantile in pipeline JSON)")
    full_width: float = Field(description="interval_width in pipeline JSON")
    empirical_coverage: float = Field(description="Empirical coverage on the 26 test points")
    relative_rmse_to_best: float = Field(
        description="Test RMSE of this model vs best test RMSE on this target"
    )


class MetricsBlock(BaseModel):
    test_rmse: float
    test_mae: float
    test_r2: float
    cv_mean_rmse: Optional[float] = None
    cv_std_rmse: Optional[float] = None


class ResidualSummary(BaseModel):
    n_test: int
    mean_abs_residual: float
    max_abs_residual: float


class ModellingContext(BaseModel):
    """Optional block for analyst persona — all from repo artefacts, not free text."""

    n_train: int
    n_test: int
    selection_policy: Optional[str] = None
    shap_explain_split: Optional[str] = None
    note_composite_uses_test: bool = Field(
        default=True,
        description="Step 10 composite uses test RMSE; pre-test SHAP uses composite_pre_test",
    )


class AttributionSnapshot(BaseModel):
    """
    Single-target bundle passed to the LLM. All fields must be machine-generated from JSON/CSV.
    """

    schema_version: str = "1.0"
    target: str
    selected_model: str
    metrics: MetricsBlock
    interval_90: Interval90
    top_shap_features: List[ShapFeature]
    residual_summary: ResidualSummary
    caveats: List[str]
    modelling_context: Optional[ModellingContext] = None

    def to_llm_json(self) -> str:
        return self.model_dump_json(indent=2)
