"""MongoDB document models and schemas."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class EstimationResult(BaseModel):
    """Stored estimation result structure."""
    total_cost: float
    cost_breakdown: dict[str, float]  # hardware, civil, labor, ops
    quantities: dict[str, Any]  # fiber_km, splitters, olts, onts, cabinets, etc.
    roi: Optional[float] = None
    payback_period_months: Optional[float] = None
    annual_revenue: Optional[float] = None
    annual_opex: Optional[float] = None
    net_annual: Optional[float] = None
    roi_payback_explanation: Optional[str] = None
    llm_explanation: str = ""
    deployment_strategy: str = ""
    optimization_suggestions: list[str] = []
    architecture_type: Optional[str] = None
    error_margin: Optional[float] = None
    charts_data: Optional[dict[str, Any]] = None  # for frontend charts
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None


class ProjectDocument(BaseModel):
    """Project/estimation stored in MongoDB."""
    id: Optional[str] = None
    user_id: str = "default"
    type: str  # cost_estimation | budget_planning | upgrade_planner | maps_planner
    title: str = ""
    inputs: dict[str, Any]
    result: EstimationResult
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
