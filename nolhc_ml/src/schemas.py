"""Pydantic models (nolhc_ml_engine_spec.md §13)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PredictionResult(BaseModel):
    value: float
    unit: str
    status: str
    r2: float
    registered_as: str
    mae: float


class PredictSelectiveBody(BaseModel):
    outputs: List[str] = Field(default_factory=list)
    model_config = {"extra": "allow"}
