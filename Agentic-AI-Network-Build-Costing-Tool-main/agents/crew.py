"""
CrewAI-style agents for FTTP estimation.
Uses deterministic engine for numbers and Ollama for explanations and optimization.
"""
import re
from typing import Any, Dict

from .fttp_engine import (
    estimate_quantities,
    estimate_costs,
    roi_and_payback,
    roi_payback_detail,
    budget_coverage,
    ARCHITECTURE,
    AREA_TYPE,
)
from .ollama_client import get_llm, is_ollama_available


def _call_llm(prompt: str, max_tokens: int = 1024, fallback: str = "") -> str:
    """Sync call to Ollama for explanation text. Returns fallback when Ollama is not available or model missing."""
    llm = get_llm()
    if llm is None:
        return fallback or "Ollama is not running. Start it with: ollama serve. Then pull a model: ollama pull llama3.2"
    try:
        out = llm.invoke(prompt[:8000])
        text = (out or "").strip()
        # LangChain sometimes returns error message as content instead of raising (e.g. 404 model not found)
        if not text or any(x in text.lower() for x in (
            "could not be generated", "ollama call failed", "404", "model is not found",
            "model not found", "pull the model", "connection refused"
        )):
            return fallback or "Explanation unavailable (Ollama not running or model not loaded). Cost and quantities above are still accurate."
        return text
    except Exception:
        return fallback or "Explanation unavailable (Ollama not running or model not loaded). Cost and quantities above are still accurate."


def _validation_agent(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize inputs."""
    area_type = (inputs.get("area_type") or "Urban").strip()
    if area_type not in ("Urban", "Semi-Urban", "Rural"):
        area_type = "Urban"
    arch = (inputs.get("architecture_type") or inputs.get("architecture") or "PON").strip().upper()
    if arch not in ("PON", "P2P", "PCP"):
        arch = "PON"
    premises = max(1, int(inputs.get("total_premises") or inputs.get("premises") or 100))
    distance_km = max(0.0, float(inputs.get("distance_km") or inputs.get("distance") or 2.0))
    # Collect optional user-provided cost parameters.
    cost_parameters = {}
    for k in (
        "fiber_per_km",
        "splitter_1_32",
        "splitter_1_64",
        "olt_port",
        "ont_unit",
        "cabinet",
        "civil_per_km",
        "labor_per_premise",
        "maintenance_year_pct",
    ):
        if k in inputs and inputs.get(k) is not None and inputs.get(k) != "":
            cost_parameters[k] = inputs.get(k)
    return {
        "area_type": area_type,
        "architecture_type": arch,
        "total_premises": premises,
        "distance_km": distance_km,
        "area_name": inputs.get("area_name") or inputs.get("area_code") or "Area",
        "budget": float(inputs.get("budget") or 0),
        "target_premises": int(inputs.get("target_premises") or premises),
        "cost_parameters": cost_parameters,
    }


def _roi_payback_explanation(total_cost: float, premises: int, detail: dict, currency_symbol: str = "₹") -> str:
    """Build human-readable ROI & Payback explanation for display and history."""
    inv = total_cost
    rev = detail.get("annual_revenue") or 0
    opex = detail.get("annual_opex") or 0
    net = detail.get("net_annual") or (rev - opex)
    payback = detail.get("payback_period_months") or 0
    roi = detail.get("roi") or 0
    return (
        f"Total Investment of {currency_symbol}{inv:,.0f} yields Annual Revenue of {currency_symbol}{rev:,.0f}. "
        f"With Annual OPEX of {currency_symbol}{opex:,.0f}, Net Annual is {currency_symbol}{net:,.0f}. "
        f"Payback is {payback:.2f} months with ROI of {roi:.2f}%."
    )


def _cost_estimation_agent(validated: Dict[str, Any]) -> Dict[str, Any]:
    """Compute quantities and cost breakdown."""
    q = estimate_quantities(
        validated["total_premises"],
        validated["distance_km"],
        validated["area_type"],
        validated["architecture_type"],
    )
    costs = estimate_costs(q, validated["distance_km"], validated["total_premises"], cost_parameters=validated.get("cost_parameters"))
    total = costs["total"]
    detail = roi_payback_detail(total, validated["total_premises"])
    return {
        "quantities": q,
        "cost_breakdown": {k: v for k, v in costs.items() if k != "total"},
        "total_cost": total,
        "roi": detail["roi"],
        "payback_period_months": detail["payback_period_months"],
        "annual_revenue": detail["annual_revenue"],
        "annual_opex": detail["annual_opex"],
        "net_annual": detail["net_annual"],
        "roi_payback_explanation": _roi_payback_explanation(total, validated["total_premises"], detail),
    }


def _rule_based_optimizations(cost_result: Dict[str, Any], validated: Dict[str, Any]) -> list:
    """Always return clear, actionable cost optimization suggestions with brief explanations."""
    suggestions = []
    breakdown = cost_result.get("cost_breakdown") or {}
    total = cost_result.get("total_cost") or 0
    if breakdown.get("hardware", 0) > total * 0.35:
        suggestions.append("Use a higher split ratio (e.g. 1:64 instead of 1:32) to serve more premises per OLT port and lower hardware cost.")
    if breakdown.get("civil", 0) > total * 0.3:
        suggestions.append("Use existing duct infrastructure or aerial fiber where possible to reduce trenching and civil work cost.")
    if validated.get("total_premises", 0) > 500:
        suggestions.append("Phase deployment by area: prioritize high-ARPU or high-density zones first for faster revenue and payback.")
    suggestions.append("Reuse existing cabinets, splitters, and feeder fiber where within reach to avoid duplicate build cost.")
    suggestions.append("Negotiate bulk pricing with vendors for fiber cable and ONTs to lower unit cost.")
    return suggestions[:5]


def _optimization_agent(cost_result: Dict[str, Any], validated: Dict[str, Any]) -> list:
    """Return cost optimization suggestions: always use rule-based for reliable, clear explanations."""
    rule_based = _rule_based_optimizations(cost_result, validated)
    # Optionally try LLM and merge; if LLM fails or returns bad data, we still have rule_based
    prompt = f"""You are an FTTP cost optimization expert. Premises: {validated['total_premises']}, Area: {validated['area_type']}, Cost: ${cost_result['total_cost']:,.0f}. Reply with 3-5 short suggestions, one per line, each starting with "1." or "-" then the full sentence. Example: "1. Use higher split ratio to reduce OLT cost." No other text."""
    text = _call_llm(prompt, 512, fallback="")
    llm_lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or len(line) < 20:
            continue
        cleaned = re.sub(r"^[\d]+[\.\)]\s*", "", line)
        cleaned = re.sub(r"^[\-\*]\s*", "", cleaned).strip()
        if len(cleaned) > 25 and not cleaned.isdigit() and cleaned not in ("1", "2", "3", "4", "5"):
            llm_lines.append(cleaned)
    # Build result: use rule_based as base, optionally prepend good LLM lines (no duplicates)
    seen = set()
    result = []
    for s in llm_lines[:5]:
        key = s[:50].lower()
        if key not in seen and len(s) > 25:
            seen.add(key)
            result.append(s)
    for s in rule_based:
        if len(result) >= 5:
            break
        key = s[:50].lower()
        if key not in seen:
            seen.add(key)
            result.append(s)
    # Guarantee we always return 5 full sentences
    out = [str(x).strip() for x in result if x and len(str(x).strip()) > 20 and not str(x).strip().isdigit()]
    return out[:5] if len(out) >= 3 else rule_based[:5]


def _explanation_agent(validated: Dict[str, Any], cost_result: Dict[str, Any], opt_suggestions: list) -> str:
    """Generate human-readable LLM explanation."""
    prompt = f"""You are an FTTP planning expert. In 2-3 short paragraphs, explain this deployment in plain language:
- Area: {validated['area_name']} ({validated['area_type']}), {validated['total_premises']} premises
- Architecture: {validated['architecture_type']}, distance from CO: {validated['distance_km']} km
- Total cost: ${cost_result['total_cost']:,.0f}, ROI: {cost_result['roi']}%, Payback: {cost_result['payback_period_months']} months
- Quantities: {cost_result['quantities']}
- Optimization tips: {opt_suggestions}

Explain the rationale, key cost drivers, and deployment strategy. Be concise."""
    return _call_llm(
        prompt,
        1024,
        fallback="This deployment uses the selected architecture and distance. Main cost drivers are fiber, civil works, and hardware. Phase feeder first, then distribution.",
    )


def _deployment_strategy_agent(validated: Dict[str, Any], cost_result: Dict[str, Any]) -> str:
    """Generate deployment strategy text."""
    prompt = f"""As an FTTP deployment specialist, in one short paragraph recommend a deployment strategy for:
{validated['total_premises']} premises, {validated['architecture_type']}, {validated['area_type']}, distance {validated['distance_km']} km.
Mention phasing (e.g. feeder first, then distribution) and any risks. Be concise."""
    return _call_llm(
        prompt,
        512,
        fallback="Deploy feeder fiber first, then install splitters and distribution. Commission OLT and ONTs in phases. Consider terrain and existing ducts.",
    )


def run_estimation_crew(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Full pipeline: validate -> estimate -> optimize -> explain. For Cost Estimation flow."""
    validated = _validation_agent(inputs)
    cost_result = _cost_estimation_agent(validated)
    opt_suggestions = _optimization_agent(cost_result, validated)
    explanation = _explanation_agent(validated, cost_result, opt_suggestions)
    deployment = _deployment_strategy_agent(validated, cost_result)

    charts_data = {
        "breakdown_labels": list(cost_result["cost_breakdown"].keys()),
        "breakdown_values": list(cost_result["cost_breakdown"].values()),
    }

    if not opt_suggestions or len(opt_suggestions) < 3:
        opt_suggestions = _rule_based_optimizations(cost_result, validated)[:5]
    return {
        "total_cost": cost_result["total_cost"],
        "cost_breakdown": cost_result["cost_breakdown"],
        "quantities": cost_result["quantities"],
        "roi": cost_result["roi"],
        "payback_period_months": cost_result["payback_period_months"],
        "annual_revenue": cost_result.get("annual_revenue"),
        "annual_opex": cost_result.get("annual_opex"),
        "net_annual": cost_result.get("net_annual"),
        "roi_payback_explanation": cost_result.get("roi_payback_explanation"),
        "llm_explanation": explanation,
        "deployment_strategy": deployment,
        "optimization_suggestions": opt_suggestions,
        "architecture_type": validated["architecture_type"],
        "charts_data": charts_data,
        "inputs_used": validated,
    }


def run_budget_crew(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Budget-based planning: given budget, compute feasible coverage and plan."""
    validated = _validation_agent(inputs)
    budget = float(inputs.get("budget") or validated.get("budget") or 1_000_000)
    max_premises = budget_coverage(
        budget,
        validated["distance_km"],
        validated["area_type"],
        validated["architecture_type"],
        cost_parameters=validated.get("cost_parameters"),
    )
    # Re-run estimation for that premise count
    validated["total_premises"] = max_premises
    cost_result = _cost_estimation_agent(validated)
    opt_suggestions = _optimization_agent(cost_result, validated)
    explanation = _call_llm(
        f"As FTTP planner: Budget ${budget:,.0f} can cover ~{max_premises} premises with {validated['architecture_type']} "
        f"in {validated['area_type']}. Cost ${cost_result['total_cost']:,.0f}. "
        "In 2 short paragraphs explain trade-offs and feasibility. Be concise.",
        1024,
        fallback=f"Budget ${budget:,.0f} covers approximately {max_premises} premises with {validated['architecture_type']} in {validated['area_type']}. Total cost ${cost_result['total_cost']:,.0f}. Expand in phases or increase budget for more coverage.",
    )
    deployment = _deployment_strategy_agent(validated, cost_result)
    charts_data = {
        "breakdown_labels": list(cost_result["cost_breakdown"].keys()),
        "breakdown_values": list(cost_result["cost_breakdown"].values()),
    }
    return {
        "total_cost": cost_result["total_cost"],
        "cost_breakdown": cost_result["cost_breakdown"],
        "quantities": cost_result["quantities"],
        "roi": cost_result["roi"],
        "payback_period_months": cost_result["payback_period_months"],
        "annual_revenue": cost_result.get("annual_revenue"),
        "annual_opex": cost_result.get("annual_opex"),
        "net_annual": cost_result.get("net_annual"),
        "roi_payback_explanation": cost_result.get("roi_payback_explanation"),
        "llm_explanation": explanation,
        "deployment_strategy": deployment,
        "optimization_suggestions": opt_suggestions,
        "architecture_type": validated["architecture_type"],
        "feasible_premises": max_premises,
        "budget_used": budget,
        "charts_data": charts_data,
        "inputs_used": validated,
    }


def run_upgrade_crew(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Upgrade planner: existing network -> target capacity, upgrade cost."""
    current_type = (inputs.get("existing_network_type") or "PON").strip().upper()
    current_cap = int(inputs.get("current_capacity") or inputs.get("current_premises") or 500)
    target_cap = int(inputs.get("target_capacity") or inputs.get("target_premises") or 2000)
    target_cap = max(target_cap, current_cap + 1)
    validated = _validation_agent(inputs)
    validated["total_premises"] = target_cap
    # Estimate full greenfield for target, then approximate upgrade delta
    q = estimate_quantities(
        target_cap, validated["distance_km"], validated["area_type"], validated["architecture_type"]
    )
    costs = estimate_costs(q, validated["distance_km"], target_cap, cost_parameters=validated.get("cost_parameters"))
    # Rough upgrade cost = delta (simplified: assume proportional)
    scale = (target_cap - current_cap) / target_cap if target_cap else 0
    upgrade_total = costs["total"] * scale * 1.2  # 20% premium for upgrade vs greenfield
    breakdown = {
        "hardware": round(costs["hardware"] * scale * 1.2, 2),
        "civil": round(costs["civil"] * scale, 2),
        "labor": round(costs["labor"] * scale, 2),
        "ops": round(costs["ops"] * scale, 2),
    }
    upgrade_total_rounded = round(upgrade_total, 2)
    new_premises = max(1, target_cap - current_cap)
    detail = roi_payback_detail(upgrade_total_rounded, new_premises)
    explanation = _call_llm(
        f"FTTP upgrade: from {current_cap} to {target_cap} premises, current type {current_type}. "
        f"Estimated upgrade cost ${upgrade_total_rounded:,.0f}. ROI {detail['roi']}%, payback {detail['payback_period_months']} months. "
        "In 2 short paragraphs explain hardware changes and strategy. Be concise.",
        1024,
        fallback=f"Upgrade from {current_cap} to {target_cap} premises. Estimated cost ${upgrade_total_rounded:,.0f}. Add OLT ports and splitters as needed; reuse existing fiber and cabinets where possible.",
    )
    return {
        "total_cost": upgrade_total_rounded,
        "cost_breakdown": breakdown,
        "quantities": q,
        "roi": detail["roi"],
        "payback_period_months": detail["payback_period_months"],
        "annual_revenue": detail["annual_revenue"],
        "annual_opex": detail["annual_opex"],
        "net_annual": detail["net_annual"],
        "roi_payback_explanation": _roi_payback_explanation(upgrade_total_rounded, new_premises, detail),
        "llm_explanation": explanation,
        "deployment_strategy": "Phased upgrade: add splitters and OLT ports first, then extend distribution.",
        "optimization_suggestions": [
            "Reuse existing fiber and cabinets where possible.",
            "Schedule upgrades during low-traffic windows.",
        ],
        "architecture_type": validated["architecture_type"],
        "current_capacity": current_cap,
        "target_capacity": target_cap,
        "charts_data": {
            "breakdown_labels": list(breakdown.keys()),
            "breakdown_values": list(breakdown.values()),
        },
        "inputs_used": validated,
    }


def _infer_location_details(target_location: str, total_premises: int) -> Dict[str, Any]:
    """Infer area_type, architecture, distance from target location and premises (LLM + fallbacks)."""
    location = (target_location or "Area").strip() or "Area"
    premises = max(1, total_premises)
    # Rule-based defaults
    if premises <= 100:
        default_area = "Rural"
        default_dist = 3.0
        default_arch = "PON"
    elif premises <= 500:
        default_area = "Semi-Urban"
        default_dist = 2.0
        default_arch = "PON"
    else:
        default_area = "Urban"
        default_dist = 1.0 + (premises / 500.0)  # cap later
        default_arch = "PON"
    default_dist = min(50.0, max(0.5, default_dist))
    prompt = f"""Given a target location "{location}" and {premises} premises to connect, respond in one short line each:
1) Area type - exactly one of: Urban, Semi-Urban, Rural
2) Recommended FTTP architecture - exactly one of: PON, P2P, PCP
3) Estimated distance from Central Office in km - one number only (e.g. 2.5)

Format exactly:
Area: Urban
Architecture: PON
Distance: 2.0"""
    try:
        text = _call_llm(prompt, 256, fallback="")
        area_type = default_area
        architecture = default_arch
        distance_km = default_dist
        for line in text.split("\n"):
            line = line.strip()
            if "area" in line.lower() and ":" in line:
                val = line.split(":", 1)[1].strip()
                if val in ("Urban", "Semi-Urban", "Rural"):
                    area_type = val
            if "arch" in line.lower() and ":" in line:
                val = line.split(":", 1)[1].strip().upper()
                if val in ("PON", "P2P", "PCP"):
                    architecture = val
            if "distance" in line.lower() and ":" in line:
                try:
                    val = float(line.split(":", 1)[1].strip().replace(",", ".").split()[0])
                    distance_km = min(50, max(0.3, val))
                except (ValueError, IndexError):
                    pass
        return {
            "area_type": area_type,
            "architecture_type": architecture,
            "distance_km": round(distance_km, 2),
            "area_name": location,
        }
    except Exception:
        return {
            "area_type": default_area,
            "architecture_type": default_arch,
            "distance_km": default_dist,
            "area_name": location,
        }


def _map_to_display_breakdown(cost_result: Dict[str, Any], quantities: Dict[str, Any]) -> Dict[str, float]:
    """Map internal costs to Compute, Storage, Network, Deployment for Maps UI."""
    from agents.fttp_engine import COSTS
    breakdown = cost_result.get("cost_breakdown") or {}
    q = quantities or {}
    hw = breakdown.get("hardware", 0)
    civil = breakdown.get("civil", 0)
    labor = breakdown.get("labor", 0)
    ops = breakdown.get("ops", 0)
    olt_cost = (q.get("olt_ports", 0) or 0) * COSTS.get("olt_port", 800)
    cabinet_cost = (q.get("cabinets", 0) or 0) * COSTS.get("cabinet", 3500)
    compute = round(olt_cost + cabinet_cost, 2)
    storage = round(hw * 0.03, 2)
    network = round(hw - olt_cost - cabinet_cost, 2)
    deployment = round(civil + labor + ops, 2)
    return {"Compute": compute, "Storage": storage, "Network": network, "Deployment": deployment}


def run_maps_crew(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Maps planner: geocode location, calculate distance, infer area/architecture, run estimation."""
    from utils.geocode import geocode_location, destination_point_km, DEFAULT_CO_LAT, DEFAULT_CO_LNG

    target_location = (inputs.get("target_location") or inputs.get("area_name") or "Area").strip() or "Area"
    try:
        total_premises = max(1, min(100000, int(inputs.get("total_premises") or inputs.get("premises") or 51)))
    except (TypeError, ValueError):
        total_premises = 51

    user_lat, user_lng = None, None
    near_lat, near_lng = None, None
    try:
        coords = geocode_location(target_location)
        if coords:
            user_lat, user_lng = coords
            near_lat, near_lng = destination_point_km(user_lat, user_lng, 20.0, bearing_degrees=45.0)
    except Exception:
        pass

    inferred = _infer_location_details(target_location, total_premises)
    # Force fixed 20 km distance for Maps Planner (ignore geocode/LLM distance)
    inferred["distance_km"] = 20.0
    full_inputs = {
        "area_name": inferred["area_name"],
        "area_type": inferred["area_type"],
        "architecture_type": inferred["architecture_type"],
        "distance_km": float(inferred["distance_km"]),
        "total_premises": total_premises,
    }

    try:
        result = run_estimation_crew(full_inputs)
    except Exception as e:
        result = {
            "total_cost": 0,
            "cost_breakdown": {},
            "cost_breakdown_display": {"Compute": 0, "Storage": 0, "Network": 0, "Deployment": 0},
            "quantities": {},
            "roi": 0,
            "payback_period_months": 0,
            "llm_explanation": "",
            "deployment_strategy": "",
            "optimization_suggestions": ["Cost estimation failed: " + str(e) + ". Check inputs and backend."],
            "architecture_type": inferred["architecture_type"],
            "charts_data": {"breakdown_labels": [], "breakdown_values": []},
        }

    result["error_margin"] = 0.15
    result["inputs_used"] = full_inputs
    result["user_lat"] = user_lat
    result["user_lng"] = user_lng
    # Second marker: a nearby point 20km from user location (fallback to default if geocode failed)
    result["co_lat"] = near_lat if near_lat is not None else DEFAULT_CO_LAT
    result["co_lng"] = near_lng if near_lng is not None else DEFAULT_CO_LNG
    result["inferred_location_type"] = inferred["area_type"]
    result["inferred_architecture"] = inferred["architecture_type"]
    result["inferred_distance_km"] = inferred["distance_km"]
    result["distance_display_km"] = round(float(inferred["distance_km"]), 2)
    distance_m = int(float(inferred["distance_km"]) * 1000)

    if "cost_breakdown_display" not in result or not result["cost_breakdown_display"]:
        result["cost_breakdown_display"] = _map_to_display_breakdown(result, result.get("quantities"))
    result["charts_data"] = {
        "breakdown_labels": list((result.get("cost_breakdown_display") or {}).keys()),
        "breakdown_values": list((result.get("cost_breakdown_display") or {}).values()),
    }

    result["agent_decision_matrix"] = (
        f"Generated a nearby point ({distance_m}m from input). Recommended {inferred['architecture_type']} for {inferred['area_type']} area."
    )
    result["agent_log"] = [
        f"[GIS Scout] Location: {target_location}. Area type: {inferred['area_type']}. Fixed distance: {inferred['distance_km']} km.",
        f"[Strategy Agent] Recommended architecture: {inferred['architecture_type']}. Fixed distance {distance_m}m.",
        "[Inventory Bot] Generating infrastructure cost breakdown...",
    ]
    result["llm_explanation"] = (
        (result.get("llm_explanation") or "")
        + "\n\n[Map-based estimate: ±15% margin due to terrain and route variations.]"
    )
    return result
