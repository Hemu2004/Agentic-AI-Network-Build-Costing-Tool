"""
Interactive CLI for FTTP estimation with runtime cost parameter entry.

This avoids blocking the FastAPI server (which would hang waiting for stdin).
Use this script when you want to type the cost parameters like:
  Enter cost for fiber per km (default 200):
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from config.currency import apply_currency_to_result, convert_to_usd
from graph import run_estimation_graph, run_budget_graph, run_upgrade_graph, run_maps_graph


def _prompt_str(msg: str, default: str = "") -> str:
    raw = input(msg).strip()
    return raw if raw != "" else default


def _prompt_int(msg: str, default: int) -> int:
    raw = input(msg).strip()
    if raw == "":
        return default
    return max(0, int(raw))


def _prompt_float(msg: str, default: float) -> float:
    raw = input(msg).strip()
    if raw == "":
        return default
    return float(raw)


def _prompt_optional_float(msg: str) -> Optional[float]:
    raw = input(msg).strip()
    if raw == "":
        return None
    return float(raw)


def _run_cost_estimation(currency: str) -> Dict[str, Any]:
    area_name = _prompt_str("Enter area name (default Area): ", "Area")
    area_type = _prompt_str("Enter area type [Urban/Semi-Urban/Rural] (default Urban): ", "Urban")
    architecture_type = _prompt_str("Enter architecture [PON/P2P/PCP] (default PON): ", "PON")
    total_premises = _prompt_int("Enter total premises (default 100): ", 100)
    distance_km = _prompt_float("Enter distance km from CO (default 2.0): ", 2.0)

    inputs: Dict[str, Any] = {
        "area_name": area_name,
        "area_type": area_type,
        "architecture_type": architecture_type,
        "total_premises": total_premises,
        "distance_km": distance_km,
        # Trigger runtime prompts for all cost parameters.
        "prompt_costs": True,
        # Ask the engine/crew to keep annual OPEX default unless you want to override it here.
        "annual_opex_pct": _prompt_optional_float("Enter annual_opex_pct (optional, default 0.015): "),
    }

    # Graph runs USD internally; API normally handles conversion. Reuse it here too.
    result = run_estimation_graph(inputs)
    return apply_currency_to_result(result, currency)


def _run_budget_planning(currency: str) -> Dict[str, Any]:
    budget = _prompt_float("Enter budget (default 1000000): ", 1000000.0)
    area_type = _prompt_str("Enter area type [Urban/Semi-Urban/Rural] (default Urban): ", "Urban")
    architecture_type = _prompt_str("Enter architecture [PON/P2P/PCP] (default PON): ", "PON")
    distance_km = _prompt_float("Enter distance km from CO (default 2.0): ", 2.0)

    # Graph runs in USD internally (API normally converts). Convert here too.
    budget_usd = convert_to_usd(budget, currency)

    inputs: Dict[str, Any] = {
        "budget": budget_usd,
        "area_type": area_type,
        "architecture_type": architecture_type,
        "distance_km": distance_km,
        "target_premises": None,
        "prompt_costs": True,
    }
    result = run_budget_graph(inputs)
    return apply_currency_to_result(result, currency)


def _run_upgrade_planner(currency: str) -> Dict[str, Any]:
    existing_network_type = _prompt_str("Enter existing network type [PON/P2P/PCP] (default PON): ", "PON")
    current_capacity = _prompt_int("Enter current capacity (default 500): ", 500)
    target_capacity = _prompt_int("Enter target capacity (default 2000): ", 2000)
    area_type = _prompt_str("Enter area type [Urban/Semi-Urban/Rural] (default Urban): ", "Urban")
    distance_km = _prompt_float("Enter distance km from CO (default 2.0): ", 2.0)

    inputs: Dict[str, Any] = {
        "existing_network_type": existing_network_type,
        "current_capacity": current_capacity,
        "target_capacity": target_capacity,
        "area_type": area_type,
        "distance_km": distance_km,
        "prompt_costs": True,
    }
    result = run_upgrade_graph(inputs)
    return apply_currency_to_result(result, currency)


def _run_maps_estimation(currency: str) -> Dict[str, Any]:
    target_location = _prompt_str("Enter target location (default Area): ", "Area")
    total_premises = _prompt_int("Enter total premises (default 51): ", 51)

    # Optional overrides to keep behavior consistent with the Maps flow.
    area_type = _prompt_optional_str("Enter area type override (optional, e.g. Urban): ")
    architecture_type = _prompt_optional_str("Enter architecture override (optional, e.g. PON): ")
    distance_km = _prompt_optional_float("Enter distance km override (optional): ")

    inputs: Dict[str, Any] = {
        "target_location": target_location,
        "total_premises": total_premises,
        "prompt_costs": True,
    }
    if area_type is not None:
        inputs["area_type"] = area_type
    if architecture_type is not None:
        inputs["architecture_type"] = architecture_type
    if distance_km is not None:
        inputs["distance_km"] = distance_km

    result = run_maps_graph(inputs)
    return apply_currency_to_result(result, currency)


def _prompt_optional_str(msg: str) -> Optional[str]:
    raw = input(msg).strip()
    return raw if raw != "" else None


def main() -> None:
    mode = _prompt_str(
        "Choose mode: 1=cost estimate, 2=budget planning, 3=upgrade planner, 4=maps estimate (default 1): ",
        "1",
    )
    currency = _prompt_str("Output currency [USD/INR/GBP/EUR] (default INR): ", "INR")
    print("\nNote: cost parameters you enter will be treated as USD for calculations (conversion is applied only to the final output).")

    if mode == "1":
        result = _run_cost_estimation(currency)
    elif mode == "2":
        result = _run_budget_planning(currency)
    elif mode == "3":
        result = _run_upgrade_planner(currency)
    elif mode == "4":
        result = _run_maps_estimation(currency)
    else:
        print("Invalid mode. Exiting.")
        return

    print("\n=== Result ===")
    print(f"Total cost: {result.get('currency_symbol', '')}{result.get('total_cost', 0):,.2f}")
    print(f"ROI: {result.get('roi', 0)}%")
    print(f"Payback (months): {result.get('payback_period_months', 0)}")


if __name__ == "__main__":
    main()

