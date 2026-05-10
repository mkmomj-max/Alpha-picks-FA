"""Bear / Base / Bull scenario valuation — เหมือน HTML report."""

import yfinance as yf

from fair_value import dcf_value, multiples_value
from assumptions import suggest_wacc, suggest_growth, suggest_pe_multiple


def scenario_valuation(symbol: str) -> dict:
    """3 scenarios with auto-suggested assumptions.

    Bear:  growth - 5pp, P/E -15%, WACC +1pp
    Base:  suggested values
    Bull:  growth + 5pp, P/E +15%, WACC -1pp
    """
    tk = yf.Ticker(symbol)
    info = tk.info or {}
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    eps_fwd = info.get("forwardEps") or info.get("trailingEps")

    wacc_data = suggest_wacc(symbol)
    growth_data = suggest_growth(symbol)
    pe_data = suggest_pe_multiple(symbol)

    base_wacc = wacc_data["wacc"]
    base_pe = pe_data["adjusted_pe"]

    scenarios = {}
    for name, params in [
        ("bear", {"g": growth_data["bear"], "pe_mult": 0.85, "wacc_adj": 0.01}),
        ("base", {"g": growth_data["base"], "pe_mult": 1.00, "wacc_adj": 0.00}),
        ("bull", {"g": growth_data["bull"], "pe_mult": 1.15, "wacc_adj": -0.01}),
    ]:
        wacc = max(min(base_wacc + params["wacc_adj"], 0.15), 0.06)
        pe = base_pe * params["pe_mult"]

        dcf = dcf_value(tk, discount_rate=wacc, growth_rate=params["g"])
        dcf_fv = dcf.get("fair_value") if not dcf.get("error") else None

        pe_fv = eps_fwd * pe if eps_fwd and eps_fwd > 0 else None

        values = [v for v in [dcf_fv, pe_fv] if v and v > 0]
        composite = sum(values) / len(values) if values else None

        scenarios[name] = {
            "fair_value":  composite,
            "dcf_value":   dcf_fv,
            "pe_value":    pe_fv,
            "growth_rate": params["g"],
            "discount_rate": wacc,
            "pe_multiple": pe,
            "upside_pct":  ((composite / current_price) - 1) * 100 if composite and current_price else None,
        }

    return {
        "symbol":        symbol,
        "current_price": current_price,
        "scenarios":     scenarios,
        "assumptions":   {
            "wacc":   wacc_data,
            "growth": growth_data,
            "pe":     pe_data,
        },
    }
