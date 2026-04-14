"""Request/response schemas for API."""
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator

CURRENCY_CHOICES = ("USD", "INR", "GBP", "EUR")


# Optional unit-cost overrides: must be declared on each endpoint model or Pydantic strips them.

class CostEstimationInput(BaseModel):
    area_name: Optional[str] = None
    area_code: Optional[str] = None
    area_type: str = "Urban"
    total_premises: int = Field(ge=1, le=100000)
    distance_km: float = Field(ge=0, le=500)
    architecture_type: str = "PON"
    currency: str = "INR"
    fiber_per_km: Optional[float] = Field(default=None, ge=0)
    splitter_1_32: Optional[float] = Field(default=None, ge=0)
    splitter_1_64: Optional[float] = Field(default=None, ge=0)
    olt_port: Optional[float] = Field(default=None, ge=0)
    ont_unit: Optional[float] = Field(default=None, ge=0)
    cabinet: Optional[float] = Field(default=None, ge=0)
    civil_per_km: Optional[float] = Field(default=None, ge=0)
    labor_per_premise: Optional[float] = Field(default=None, ge=0)
    maintenance_year_pct: Optional[float] = Field(default=None, ge=0)


class BudgetPlanningInput(BaseModel):
    budget: float = Field(gt=0)
    area_name: Optional[str] = None
    area_type: str = "Urban"
    distance_km: float = Field(ge=0, le=500)
    target_premises: Optional[int] = None
    architecture_type: str = "PON"
    currency: str = "INR"
    fiber_per_km: Optional[float] = Field(default=None, ge=0)
    splitter_1_32: Optional[float] = Field(default=None, ge=0)
    splitter_1_64: Optional[float] = Field(default=None, ge=0)
    olt_port: Optional[float] = Field(default=None, ge=0)
    ont_unit: Optional[float] = Field(default=None, ge=0)
    cabinet: Optional[float] = Field(default=None, ge=0)
    civil_per_km: Optional[float] = Field(default=None, ge=0)
    labor_per_premise: Optional[float] = Field(default=None, ge=0)
    maintenance_year_pct: Optional[float] = Field(default=None, ge=0)


class UpgradePlannerInput(BaseModel):
    existing_network_type: str = "PON"
    current_capacity: int = Field(ge=1)
    target_capacity: int = Field(ge=1)
    area_type: str = "Urban"
    distance_km: float = Field(ge=0, le=500)
    currency: str = "INR"
    fiber_per_km: Optional[float] = Field(default=None, ge=0)
    splitter_1_32: Optional[float] = Field(default=None, ge=0)
    splitter_1_64: Optional[float] = Field(default=None, ge=0)
    olt_port: Optional[float] = Field(default=None, ge=0)
    ont_unit: Optional[float] = Field(default=None, ge=0)
    cabinet: Optional[float] = Field(default=None, ge=0)
    civil_per_km: Optional[float] = Field(default=None, ge=0)
    labor_per_premise: Optional[float] = Field(default=None, ge=0)
    maintenance_year_pct: Optional[float] = Field(default=None, ge=0)


class MapsPlannerInput(BaseModel):
    """Maps planner: only target_location and total_premises; backend infers area_type, architecture, distance."""
    target_location: Optional[str] = None
    total_premises: int = Field(default=51, ge=1, le=100000)
    currency: str = "INR"
    region: Optional[str] = None
    distance_km: Optional[float] = None
    area_type: Optional[str] = None
    architecture_type: Optional[str] = None
    fiber_per_km: Optional[float] = Field(default=None, ge=0)
    splitter_1_32: Optional[float] = Field(default=None, ge=0)
    splitter_1_64: Optional[float] = Field(default=None, ge=0)
    olt_port: Optional[float] = Field(default=None, ge=0)
    ont_unit: Optional[float] = Field(default=None, ge=0)
    cabinet: Optional[float] = Field(default=None, ge=0)
    civil_per_km: Optional[float] = Field(default=None, ge=0)
    labor_per_premise: Optional[float] = Field(default=None, ge=0)
    maintenance_year_pct: Optional[float] = Field(default=None, ge=0)

    @field_validator("total_premises", mode="before")
    @classmethod
    def coerce_total_premises(cls, v: Any) -> int:
        if v is None:
            return 51
        try:
            n = int(float(v))
            return max(1, min(100000, n))
        except (TypeError, ValueError):
            return 51
