"""DCF Sensitivity Analysis — ดูว่า fair value เปลี่ยนยังไงเมื่อปรับ assumptions."""

import numpy as np
import pandas as pd
import yfinance as yf

from fair_value import dcf_value


def sensitivity_matrix(
    symbol: str,
    discount_rates: list[float] | None = None,
    growth_rates: list[float] | None = None,
) -> pd.DataFrame:
    """Build matrix: rows = discount rate, cols = growth rate, cells = fair value per share."""
    discount_rates = discount_rates or [0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13]
    growth_rates = growth_rates or [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20]

    tk = yf.Ticker(symbol)
    matrix = []
    for dr in discount_rates:
        row = []
        for gr in growth_rates:
            r = dcf_value(tk, discount_rate=dr, growth_rate=gr)
            row.append(r.get("fair_value") if r and not r.get("error") else None)
        matrix.append(row)

    df = pd.DataFrame(
        matrix,
        index=[f"{int(dr*100)}%" for dr in discount_rates],
        columns=[f"{int(gr*100)}%" for gr in growth_rates],
    )
    df.index.name = "Discount Rate"
    df.columns.name = "Growth Rate"
    return df


def implied_assumptions(symbol: str) -> dict:
    """Reverse-engineer: ที่ราคาปัจจุบัน ตลาดคิดว่า growth rate เท่าไหร่ ที่ discount=10%?"""
    tk = yf.Ticker(symbol)
    info = tk.info or {}
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    if not current_price:
        return {"error": "No price data"}

    growth_candidates = np.arange(0.0, 0.30, 0.005)
    best_g, best_diff = None, float("inf")
    for g in growth_candidates:
        r = dcf_value(tk, discount_rate=0.10, growth_rate=float(g))
        fv = r.get("fair_value") if r and not r.get("error") else None
        if fv is None:
            continue
        diff = abs(fv - current_price)
        if diff < best_diff:
            best_diff, best_g = diff, g

    return {
        "current_price": current_price,
        "implied_growth_at_10pct_discount": best_g * 100 if best_g is not None else None,
        "interpretation": _interpret_implied_growth(best_g),
    }


def _interpret_implied_growth(g: float | None) -> str:
    if g is None:
        return "ไม่สามารถคำนวณได้"
    g_pct = g * 100
    if g_pct < 3:    return "💚 ตลาดคาดหวังต่ำมาก — มี upside ถ้าโตปกติ"
    if g_pct < 7:    return "🟢 ตลาดคาดหวังพอสมควร — สมเหตุสมผล"
    if g_pct < 12:   return "🟡 ตลาดคาดหวังสูง — ต้องโตได้ตามคาด"
    if g_pct < 18:   return "🟠 ตลาดคาดหวังสูงมาก — เสี่ยงถ้าผิดเป้า"
    return "🔴 ตลาดคาดหวังสูงสุดขีด — ราคาเก็งกำไรหนัก"
