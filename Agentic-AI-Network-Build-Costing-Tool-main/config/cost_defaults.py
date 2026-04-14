"""
Default FTTP cost parameters (USD).

The estimator engine treats these as defaults only. If a user provides
`cost_parameters`, the user-provided values are used instead.
"""

from typing import Dict, Tuple


DEFAULT_COST_PARAMETERS: Dict[str, float] = {
    "fiber_per_km": 200.0,
    "splitter_1_32": 120.0,
    "splitter_1_64": 120.0,
    "olt_port": 350.0,
    "ont_unit": 35.0,
    "cabinet": 120.0,
    "civil_per_km": 100.0,
    "labor_per_premise": 75.0,
    "maintenance_year_pct": 0.015,
}

COST_PARAMETER_KEYS: Tuple[str, ...] = tuple(DEFAULT_COST_PARAMETERS.keys())

