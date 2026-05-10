"""Auto-suggest DCF assumptions — ไม่ต้องเดาเอง!

Sources:
1. Analyst consensus (yfinance: revenueGrowth, earningsGrowth, ROE)
2. Historical CAGR (from income statement 3-4 years)
3. Sector benchmarks (hard-coded medians)
4. CAPM-based WACC (risk-free + beta * equity risk premium)
"""

import math
import numpy as np
import pandas as pd
import yfinance as yf

from financial_analysis import get_statements, growth_rates
from overrides import get_override


RISK_FREE_RATE = 0.043
EQUITY_RISK_PREMIUM = 0.055
DEFAULT_BETA = 1.0

SECTOR_GROWTH = {
    "Technology":             0.12, "Information Technology": 0.12,
    "Healthcare":             0.08, "Health Care":            0.08,
    "Financial Services":     0.06, "Financials":             0.06,
    "Consumer Cyclical":      0.07, "Consumer Discretionary": 0.07,
    "Consumer Defensive":     0.05, "Consumer Staples":       0.05,
    "Communication Services": 0.08,
    "Industrials":            0.08,
    "Energy":                 0.04,
    "Basic Materials":        0.05, "Materials":              0.05,
    "Utilities":              0.04,
    "Real Estate":            0.05,
}


def suggest_wacc(symbol: str) -> dict:
    """CAPM: WACC = rf + beta * ERP (simplified, equity-only).
    Honor override if set."""
    ov = get_override(symbol)
    if ov.get("custom_wacc"):
        wacc = float(ov["custom_wacc"])
        return {
            "wacc": wacc, "beta": None, "rf": None, "erp": None,
            "explanation": f"📤 Manual override: WACC = {wacc*100:.1f}%",
            "is_override": True,
        }

    info = yf.Ticker(symbol).info or {}
    beta = info.get("beta") or DEFAULT_BETA

    if beta is None or (isinstance(beta, float) and math.isnan(beta)):
        beta = DEFAULT_BETA

    wacc = RISK_FREE_RATE + beta * EQUITY_RISK_PREMIUM
    wacc = max(min(wacc, 0.15), 0.07)

    return {
        "wacc":      wacc,
        "beta":      beta,
        "rf":        RISK_FREE_RATE,
        "erp":       EQUITY_RISK_PREMIUM,
        "explanation": f"WACC = {RISK_FREE_RATE*100:.1f}% (risk-free 10Y) + "
                       f"{beta:.2f} (beta) × {EQUITY_RISK_PREMIUM*100:.1f}% (ERP) "
                       f"= {wacc*100:.1f}%",
    }


def suggest_growth(symbol: str) -> dict:
    """Blend 4 sources to suggest growth rate.
    Honor override if set."""
    ov = get_override(symbol)
    info = yf.Ticker(symbol).info or {}
    sector = info.get("sector", "Unknown")

    sources = {}
    if ov.get("eps_growth"):
        sources["override_eps_growth"] = float(ov["eps_growth"])
    if ov.get("revenue_growth"):
        sources["override_revenue_growth"] = float(ov["revenue_growth"])

    rev_g = info.get("revenueGrowth")
    eps_g = info.get("earningsGrowth")
    if rev_g is not None and not math.isnan(rev_g):
        sources["analyst_revenue"] = float(rev_g)
    if eps_g is not None and not math.isnan(eps_g):
        sources["analyst_eps"] = float(eps_g)

    try:
        s = get_statements(symbol)
        gr = growth_rates(s["income"])
        if gr.get("revenue", {}).get("cagr") is not None:
            sources["historical_revenue_cagr"] = gr["revenue"]["cagr"] / 100
        if gr.get("net_income", {}).get("cagr") is not None:
            sources["historical_ni_cagr"] = gr["net_income"]["cagr"] / 100
        if gr.get("eps", {}).get("cagr") is not None:
            sources["historical_eps_cagr"] = gr["eps"]["cagr"] / 100
    except Exception:
        pass

    sector_g = SECTOR_GROWTH.get(sector, 0.07)
    sources["sector_avg"] = sector_g

    valid = [v for v in sources.values() if v is not None and -0.5 < v < 0.6]
    if not valid:
        base = sector_g
        confidence = "Low"
    else:
        weights = []
        for k in sources:
            if "override" in k:    weights.append(0.50)
            elif "analyst" in k:    weights.append(0.35)
            elif "historical" in k: weights.append(0.30)
            else:                  weights.append(0.20)
        total_w = sum(weights[:len(valid)])
        base = sum(v * w for v, w in zip(valid, weights[:len(valid)])) / total_w if total_w > 0 else sector_g
        confidence = "High" if len(valid) >= 4 else "Medium" if len(valid) >= 2 else "Low"

    base = max(min(base, 0.30), 0.02)
    bear = max(base - 0.05, 0.02)
    bull = min(base + 0.05, 0.30)

    return {
        "bear":   bear,
        "base":   base,
        "bull":   bull,
        "confidence": confidence,
        "sources": sources,
        "sector":  sector,
        "explanation": _explain_growth(sources, base, sector),
    }


def _explain_growth(sources: dict, base: float, sector: str) -> str:
    lines = [f"💡 Suggested base growth: **{base*100:.1f}%/year**", ""]
    if "analyst_revenue" in sources:
        lines.append(f"- 📊 Analyst revenue forecast: {sources['analyst_revenue']*100:.1f}%")
    if "analyst_eps" in sources:
        lines.append(f"- 📊 Analyst EPS forecast: {sources['analyst_eps']*100:.1f}%")
    if "historical_revenue_cagr" in sources:
        lines.append(f"- 📈 Historical revenue CAGR: {sources['historical_revenue_cagr']*100:.1f}%")
    if "historical_eps_cagr" in sources:
        lines.append(f"- 📈 Historical EPS CAGR: {sources['historical_eps_cagr']*100:.1f}%")
    if "sector_avg" in sources:
        lines.append(f"- 🏭 {sector} sector average: {sources['sector_avg']*100:.1f}%")
    return "\n".join(lines)


def suggest_pe_multiple(symbol: str) -> dict:
    """Suggest P/E multiple based on quality + sector base. Honor override."""
    ov = get_override(symbol)
    info = yf.Ticker(symbol).info or {}
    sector = info.get("sector", "Unknown")

    if ov.get("custom_pe"):
        pe = float(ov["custom_pe"])
        return {
            "base_pe": None, "adjusted_pe": pe,
            "quality_premium_pct": 0, "sector": sector,
            "notes": [f"📤 Manual override: P/E = {pe:.1f}×"],
            "is_override": True,
        }

    from fair_value import SECTOR_PE
    base_pe = SECTOR_PE.get(sector, 18)

    roe = info.get("returnOnEquity") or 0
    op_margin = info.get("operatingMargins") or 0

    quality_premium = 0.0
    quality_notes = []
    if roe > 0.20:
        quality_premium += 0.15; quality_notes.append(f"ROE {roe*100:.0f}% (excellent) → +15%")
    elif roe > 0.15:
        quality_premium += 0.08; quality_notes.append(f"ROE {roe*100:.0f}% (good) → +8%")
    elif roe < 0.05 and roe > 0:
        quality_premium -= 0.10; quality_notes.append(f"ROE {roe*100:.0f}% (weak) → -10%")

    if op_margin > 0.25:
        quality_premium += 0.10; quality_notes.append(f"Op margin {op_margin*100:.0f}% (excellent) → +10%")
    elif op_margin > 0.15:
        quality_premium += 0.05; quality_notes.append(f"Op margin {op_margin*100:.0f}% (good) → +5%")

    adjusted_pe = base_pe * (1 + quality_premium)
    adjusted_pe = max(min(adjusted_pe, 40), 8)

    return {
        "base_pe":    base_pe,
        "adjusted_pe": adjusted_pe,
        "quality_premium_pct": quality_premium * 100,
        "sector":     sector,
        "notes":      quality_notes,
    }


def full_auto_suggest(symbol: str) -> dict:
    """One-stop: ดึงทุก suggestion ในที่เดียว."""
    return {
        "wacc":   suggest_wacc(symbol),
        "growth": suggest_growth(symbol),
        "pe":     suggest_pe_multiple(symbol),
    }
