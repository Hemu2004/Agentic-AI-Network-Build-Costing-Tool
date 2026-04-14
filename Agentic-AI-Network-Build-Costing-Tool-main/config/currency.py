"""Currency conversion from USD base. Rates are approximate for display."""
# Base: all internal calculations in USD
CURRENCY_RATES = {
    "USD": 1.0,
    "INR": 83.0,
    "GBP": 0.79,
    "EUR": 0.92,
}

CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "₹",
    "GBP": "£",
    "EUR": "€",
}

SUPPORTED_CURRENCIES = list(CURRENCY_RATES.keys())


def convert_from_usd(amount_usd: float, currency: str) -> float:
    """Convert USD amount to target currency."""
    rate = CURRENCY_RATES.get((currency or "USD").upper(), 1.0)
    return round(amount_usd * rate, 2)


def convert_to_usd(amount_in_currency: float, currency: str) -> float:
    """Convert an amount from the given currency to USD base."""
    curr = (currency or "USD").upper()
    rate = CURRENCY_RATES.get(curr, 1.0)
    if not rate:
        return round(float(amount_in_currency), 2)
    return round(float(amount_in_currency) / rate, 2)


def convert_cost_breakdown(breakdown: dict, currency: str) -> dict:
    """Convert cost breakdown dict from USD to target currency."""
    if not breakdown or (currency or "INR").upper() == "USD":
        return breakdown
    return {k: convert_from_usd(float(v), currency) for k, v in breakdown.items()}


def apply_currency_to_result(result: dict, currency: str) -> dict:
    """Apply currency conversion to full estimation result. Mutates and returns result."""
    curr = (currency or "INR").upper()
    if curr not in CURRENCY_RATES:
        curr = "INR"
    result["currency"] = curr
    result["currency_symbol"] = CURRENCY_SYMBOLS.get(curr, "₹")
    if result.get("total_cost") is not None:
        result["total_cost"] = convert_from_usd(float(result["total_cost"]), curr)
    if result.get("cost_breakdown"):
        result["cost_breakdown"] = convert_cost_breakdown(result["cost_breakdown"], curr)
    if result.get("cost_breakdown_display"):
        result["cost_breakdown_display"] = convert_cost_breakdown(result["cost_breakdown_display"], curr)
    if result.get("charts_data") and result["charts_data"].get("breakdown_values"):
        result["charts_data"] = {
            **result["charts_data"],
            "breakdown_values": [convert_from_usd(float(v), curr) for v in result["charts_data"]["breakdown_values"]],
        }
    sym = result.get("currency_symbol") or CURRENCY_SYMBOLS.get(curr, "₹")
    if result.get("annual_revenue") is not None:
        result["annual_revenue"] = convert_from_usd(float(result["annual_revenue"]), curr)
    if result.get("annual_opex") is not None:
        result["annual_opex"] = convert_from_usd(float(result["annual_opex"]), curr)
    if result.get("net_annual") is not None:
        result["net_annual"] = convert_from_usd(float(result["net_annual"]), curr)
    inv = result.get("total_cost") or 0
    rev = result.get("annual_revenue") or 0
    opex = result.get("annual_opex") or 0
    net = result.get("net_annual") or (rev - opex)
    payback = result.get("payback_period_months") or 0
    roi = result.get("roi") or 0
    if result.get("roi_payback_explanation") is not None or (inv and (rev or payback is not None)):
        result["roi_payback_explanation"] = (
            f"Total Investment of {sym}{inv:,.0f} yields Annual Revenue of {sym}{rev:,.0f}. "
            f"With Annual OPEX of {sym}{opex:,.0f}, Net Annual is {sym}{net:,.0f}. "
            f"Payback is {payback:.2f} months with ROI of {roi:.2f}%."
        )
    return result
