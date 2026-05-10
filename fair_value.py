"""Fair Value valuation models.

Methods:
1. DCF (Discounted Cash Flow) — 2-stage FCF model
2. Multiples — P/E and EV/EBITDA based on sector medians
3. Graham Number — sqrt(22.5 * EPS * BVPS)
4. Earnings Power Value (EPV) — normalized earnings / cost of capital
5. Composite Fair Value — weighted blend
"""

import math
import numpy as np
import pandas as pd
import yfinance as yf

from overrides import get_override


DEFAULT_DISCOUNT_RATE = 0.10
DEFAULT_TERMINAL_GROWTH = 0.025
DEFAULT_PROJECTION_YEARS = 5
DEFAULT_HIGH_GROWTH_YEARS = 5

SECTOR_PE = {
    "Technology": 28, "Information Technology": 28,
    "Healthcare": 22, "Health Care": 22,
    "Financial Services": 13, "Financials": 13,
    "Consumer Cyclical": 18, "Consumer Discretionary": 18,
    "Consumer Defensive": 20, "Consumer Staples": 20,
    "Communication Services": 20,
    "Industrials": 20,
    "Energy": 12,
    "Basic Materials": 15, "Materials": 15,
    "Utilities": 17,
    "Real Estate": 25,
}

SECTOR_EV_EBITDA = {
    "Technology": 18, "Information Technology": 18,
    "Healthcare": 15, "Health Care": 15,
    "Financial Services": 10, "Financials": 10,
    "Consumer Cyclical": 12, "Consumer Discretionary": 12,
    "Consumer Defensive": 13, "Consumer Staples": 13,
    "Communication Services": 11,
    "Industrials": 13,
    "Energy": 7,
    "Basic Materials": 9, "Materials": 9,
    "Utilities": 11,
    "Real Estate": 18,
}


def _safe(x, default=None):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return default
    return x


# ── 1. DCF Model ──────────────────────────────────────────────────
def dcf_value(
    ticker_obj: yf.Ticker,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    terminal_growth: float = DEFAULT_TERMINAL_GROWTH,
    high_growth_years: int = DEFAULT_HIGH_GROWTH_YEARS,
    growth_rate: float | None = None,
) -> dict:
    """Two-stage DCF. Returns intrinsic value per share + assumptions."""
    info = ticker_obj.info or {}
    shares = _safe(info.get("sharesOutstanding")) or _safe(info.get("impliedSharesOutstanding"))
    fcf = _safe(info.get("freeCashflow"))
    total_debt = _safe(info.get("totalDebt"), 0)
    cash = _safe(info.get("totalCash"), 0)

    if not fcf or not shares or fcf <= 0:
        return {"error": "Insufficient FCF data (negative or missing)"}

    if growth_rate is None:
        growth_rate = _safe(info.get("earningsGrowth")) or _safe(info.get("revenueGrowth")) or 0.10
        growth_rate = max(min(growth_rate, 0.25), 0.03)

    cash_flows = []
    current_fcf = fcf
    for year in range(1, high_growth_years + 1):
        current_fcf *= (1 + growth_rate)
        pv = current_fcf / ((1 + discount_rate) ** year)
        cash_flows.append({"year": year, "fcf": current_fcf, "pv": pv})

    terminal_fcf = current_fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** high_growth_years)

    enterprise_value = sum(c["pv"] for c in cash_flows) + pv_terminal
    equity_value = enterprise_value - total_debt + cash
    fair_value_per_share = equity_value / shares

    return {
        "method": "DCF",
        "fair_value": fair_value_per_share,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "terminal_value_pv": pv_terminal,
        "assumptions": {
            "fcf_base": fcf,
            "growth_rate": growth_rate,
            "discount_rate": discount_rate,
            "terminal_growth": terminal_growth,
            "high_growth_years": high_growth_years,
        },
        "projections": cash_flows,
    }


# ── 2. Multiples Valuation ────────────────────────────────────────
def multiples_value(ticker_obj: yf.Ticker) -> dict:
    info = ticker_obj.info or {}
    symbol = info.get("symbol", "")
    ov = get_override(symbol) if symbol else {}

    sector = info.get("sector", "Unknown")

    eps = (ov.get("adj_eps_fwd") or ov.get("adj_eps_ttm")
           or _safe(info.get("forwardEps")) or _safe(info.get("trailingEps")))
    ebitda = _safe(info.get("ebitda"))
    shares = _safe(info.get("sharesOutstanding"))
    debt = _safe(info.get("totalDebt"), 0)
    cash = _safe(info.get("totalCash"), 0)

    pe_target = ov.get("custom_pe") or SECTOR_PE.get(sector, 18)
    ev_target = ov.get("custom_ev_ebitda") or SECTOR_EV_EBITDA.get(sector, 12)

    pe_value = eps * pe_target if eps and eps > 0 else None

    ev_value = None
    if ebitda and ebitda > 0 and shares:
        target_ev = ebitda * ev_target
        equity = target_ev - debt + cash
        ev_value = equity / shares

    values = [v for v in [pe_value, ev_value] if v is not None and v > 0]
    avg = sum(values) / len(values) if values else None

    return {
        "method": "Multiples",
        "fair_value": avg,
        "pe_value": pe_value,
        "ev_ebitda_value": ev_value,
        "sector": sector,
        "pe_multiple": pe_target,
        "ev_multiple": ev_target,
    }


# ── 3. Graham Number ──────────────────────────────────────────────
def graham_value(ticker_obj: yf.Ticker) -> dict:
    info = ticker_obj.info or {}
    symbol = info.get("symbol", "")
    ov = get_override(symbol) if symbol else {}
    eps = ov.get("adj_eps_ttm") or _safe(info.get("trailingEps"))
    bvps = _safe(info.get("bookValue"))

    if not eps or not bvps or eps <= 0 or bvps <= 0:
        return {"method": "Graham", "fair_value": None, "error": "Need positive EPS and book value"}

    graham = math.sqrt(22.5 * eps * bvps)
    return {
        "method": "Graham",
        "fair_value": graham,
        "eps": eps,
        "bvps": bvps,
        "formula": "sqrt(22.5 * EPS * BVPS)",
    }


# ── 4. Earnings Power Value ───────────────────────────────────────
def epv_value(ticker_obj: yf.Ticker, cost_of_capital: float = 0.09) -> dict:
    info = ticker_obj.info or {}
    eps = _safe(info.get("trailingEps"))
    shares = _safe(info.get("sharesOutstanding"))
    debt = _safe(info.get("totalDebt"), 0)
    cash = _safe(info.get("totalCash"), 0)

    if not eps or not shares or eps <= 0:
        return {"method": "EPV", "fair_value": None, "error": "Need positive EPS"}

    normalized_earnings = eps * shares
    epv_enterprise = normalized_earnings / cost_of_capital
    equity = epv_enterprise - debt + cash
    return {
        "method": "EPV",
        "fair_value": equity / shares,
        "cost_of_capital": cost_of_capital,
        "normalized_earnings": normalized_earnings,
    }


# ── 5. Composite Fair Value ───────────────────────────────────────
def composite_fair_value(
    symbol: str,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
    growth_rate: float | None = None,
    weights: dict | None = None,
) -> dict:
    weights = weights or {"dcf": 0.40, "multiples": 0.35, "graham": 0.15, "epv": 0.10}

    tk = yf.Ticker(symbol)
    info = tk.info or {}
    current_price = _safe(info.get("currentPrice")) or _safe(info.get("regularMarketPrice"))

    ov = get_override(symbol)
    if ov.get("base_fv"):
        composite = float(ov["base_fv"])
        margin_of_safety = ((composite - current_price) / current_price * 100) if current_price else None
        verdict = "N/A"
        if margin_of_safety is not None:
            if margin_of_safety >= 30:   verdict = "🟢 Strong Undervalued"
            elif margin_of_safety >= 10: verdict = "🟢 Undervalued"
            elif margin_of_safety >= -10: verdict = "🟡 Fair Value"
            elif margin_of_safety >= -30: verdict = "🔴 Overvalued"
            else:                         verdict = "🔴 Strong Overvalued"
        return {
            "symbol": symbol, "current_price": current_price,
            "composite_fair_value": composite,
            "margin_of_safety_pct": margin_of_safety,
            "verdict": verdict + " (📤 manual)",
            "is_override": True,
            "models": {"manual": {"method": "Manual Override", "fair_value": composite}},
            "weights": {"manual": 1.0},
        }

    results = {
        "dcf":       dcf_value(tk, discount_rate=discount_rate, growth_rate=growth_rate),
        "multiples": multiples_value(tk),
        "graham":    graham_value(tk),
        "epv":       epv_value(tk),
    }

    weighted_sum, weight_sum = 0.0, 0.0
    for key, w in weights.items():
        v = results[key].get("fair_value")
        if v and v > 0:
            weighted_sum += v * w
            weight_sum += w

    composite = weighted_sum / weight_sum if weight_sum > 0 else None

    margin_of_safety = None
    verdict = "N/A"
    if composite and current_price:
        margin_of_safety = (composite - current_price) / current_price * 100
        if margin_of_safety >= 30:   verdict = "🟢 Strong Undervalued"
        elif margin_of_safety >= 10: verdict = "🟢 Undervalued"
        elif margin_of_safety >= -10: verdict = "🟡 Fair Value"
        elif margin_of_safety >= -30: verdict = "🔴 Overvalued"
        else:                         verdict = "🔴 Strong Overvalued"

    return {
        "symbol": symbol,
        "current_price": current_price,
        "composite_fair_value": composite,
        "margin_of_safety_pct": margin_of_safety,
        "verdict": verdict,
        "models": results,
        "weights": weights,
    }
