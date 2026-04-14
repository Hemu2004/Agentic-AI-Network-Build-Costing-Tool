"""
Deterministic FTTP cost and quantity calculations.
Used by agents to produce consistent, auditable numbers.
"""
from typing import Any, Dict, Literal, Optional, Tuple


ARCHITECTURE = Literal["PON", "P2P", "PCP"]
AREA_TYPE = Literal["Urban", "Semi-Urban", "Rural"]

# Cost assumptions (USD) - realistic for FTTP deployment
COSTS = {
    "fiber_per_km": 200,
    "splitter_1_32": 120,
    "splitter_1_64": 120,
    "olt_port": 350,
    "ont_unit": 35,
    "cabinet": 120,
    "civil_per_km": 100,
    "labor_per_premise": 75,
    "maintenance_year_pct": 0.015,
}
PON_SPLIT_RATIO = 32  # GPON typical
PREMISES_PER_CABINET = 96  # typical FDH size


def estimate_quantities(
    premises: int,
    distance_km: float,
    area_type: AREA_TYPE,
    architecture: ARCHITECTURE,
) -> dict:
    """Compute fiber, splitters, OLTs, ONTs, cabinets."""
    # Fiber: feeder (CO to area) + distribution (shared runs, not full km per premise)
    feeder_km = distance_km
    dist_per_premise = 0.06 if area_type == "Urban" else 0.10 if area_type == "Semi-Urban" else 0.18
    distribution_km = premises * dist_per_premise
    total_fiber_km = feeder_km + distribution_km

    if architecture == "PON":
        splitters_1_32 = max(1, (premises + PON_SPLIT_RATIO - 1) // PON_SPLIT_RATIO)
        splitters_1_64 = 0
        olt_ports = splitters_1_32  # 1 port per splitter
    elif architecture == "P2P":
        splitters_1_32 = 0
        splitters_1_64 = 0
        olt_ports = premises
    else:  # PCP
        splitters_1_32 = max(1, (premises + 16 - 1) // 16)
        splitters_1_64 = 0
        olt_ports = splitters_1_32

    cabinets = max(1, (premises + PREMISES_PER_CABINET - 1) // PREMISES_PER_CABINET)
    onts = premises

    return {
        "fiber_km": round(total_fiber_km, 2),
        "splitters_1_32": splitters_1_32,
        "splitters_1_64": splitters_1_64,
        "olt_ports": olt_ports,
        "onts": onts,
        "cabinets": cabinets,
    }


def _resolve_cost_parameters(cost_parameters: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """Return cost parameters = defaults + validated user overrides."""
    resolved: Dict[str, float] = {k: float(v) for k, v in COSTS.items()}
    if not cost_parameters:
        return resolved
    for k in resolved.keys():
        if k not in cost_parameters:
            continue
        v = cost_parameters.get(k)
        if v is None or v == "":
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv < 0:
            continue
        resolved[k] = fv
    return resolved


def estimate_costs(
    quantities: dict,
    distance_km: float,
    premises: int,
    cost_parameters: Optional[Dict[str, Any]] = None,
) -> dict:
    """Compute cost breakdown from quantities using dynamic cost parameters."""
    cp = _resolve_cost_parameters(cost_parameters)
    hardware = (
        quantities["fiber_km"] * cp["fiber_per_km"]
        + (quantities["splitters_1_32"] * cp["splitter_1_32"] + quantities["splitters_1_64"] * cp["splitter_1_64"])
        + quantities["olt_ports"] * cp["olt_port"]
        + quantities["onts"] * cp["ont_unit"]
        + quantities["cabinets"] * cp["cabinet"]
    )
    civil = quantities["fiber_km"] * cp["civil_per_km"]
    labor = premises * cp["labor_per_premise"]
    year1_maintenance = (hardware + civil) * cp["maintenance_year_pct"]
    ops = year1_maintenance

    total = hardware + civil + labor + ops
    return {
        "hardware": round(hardware, 2),
        "civil": round(civil, 2),
        "labor": round(labor, 2),
        "ops": round(ops, 2),
        "total": round(total, 2),
    }


def roi_and_payback(total_cost: float, premises: int, arpu: float = 40.0) -> Tuple[float, float]:
    """ROI % and payback period in months. ARPU in USD/month."""
    annual_revenue = premises * arpu * 12
    if total_cost <= 0:
        return 0.0, 0.0
    roi = (annual_revenue / total_cost) * 100
    payback_months = (total_cost / (premises * arpu)) if (premises * arpu) > 0 else 0
    return round(roi, 2), round(payback_months, 2)


# Annual OPEX as fraction of total capex (maintenance, power, support)
ANNUAL_OPEX_PCT = 0.015


def roi_payback_detail(total_cost: float, premises: int, arpu: float = 40.0) -> dict:
    """Return ROI & payback metrics plus annual revenue/OPEX for display and explanation."""
    annual_revenue = premises * arpu * 12
    annual_opex = round(total_cost * ANNUAL_OPEX_PCT, 2)
    net_annual = round(annual_revenue - annual_opex, 2)
    roi, payback_months = roi_and_payback(total_cost, premises, arpu)
    return {
        "annual_revenue": round(annual_revenue, 2),
        "annual_opex": annual_opex,
        "net_annual": net_annual,
        "roi": roi,
        "payback_period_months": payback_months,
    }


def budget_coverage(
    budget: float,
    distance_km: float,
    area_type: AREA_TYPE,
    architecture: ARCHITECTURE,
    cost_parameters: Optional[Dict[str, Any]] = None,
) -> int:
    """Estimate max premises achievable for a given budget (iterative)."""
    low, high = 1, 50000
    while low < high - 1:
        mid = (low + high) // 2
        q = estimate_quantities(mid, distance_km, area_type, architecture)
        costs = estimate_costs(q, distance_km, mid, cost_parameters=cost_parameters)
        if costs["total"] <= budget:
            low = mid
        else:
            high = mid
    return low
