"""Buy/Sell Alert Engine — รวม signals จากทุกระบบ."""

import pandas as pd
import yfinance as yf

from fair_value import composite_fair_value
from financial_analysis import piotroski_f_score
from data_fetcher import fetch_ticker
from scorer import score, apply_filters


# ── Signal thresholds ─────────────────────────────────────────────
THRESHOLDS = {
    "STRONG_BUY": {"composite_min": 80, "mos_min": 25, "piotroski_min": 7, "momentum_min": 60},
    "BUY":        {"composite_min": 70, "mos_min": 10, "piotroski_min": 5, "momentum_min": 50},
    "HOLD":       {"composite_min": 50, "mos_min": -15},
    "SELL":       {"composite_max": 50, "mos_max": -15},
    "STRONG_SELL":{"composite_max": 40, "mos_max": -30},
}


def evaluate_single(symbol: str, peer_universe: pd.DataFrame | None = None) -> dict:
    """รวมทุก signal สำหรับ ticker เดียว → return ALERT.

    peer_universe: optional pre-scored DataFrame for relative scoring.
                   ถ้าไม่ส่งมา จะใช้ค่า raw fundamentals แทน.
    """
    out = {"symbol": symbol, "signals": {}, "warnings": [], "highlights": []}

    # 1. Fair Value
    try:
        fv = composite_fair_value(symbol)
        out["fair_value"] = fv.get("composite_fair_value")
        out["current_price"] = fv.get("current_price")
        out["margin_of_safety"] = fv.get("margin_of_safety_pct")
        out["verdict"] = fv.get("verdict")
    except Exception as e:
        out["warnings"].append(f"Fair value error: {e}")
        out["margin_of_safety"] = None

    # 2. Quant Composite Score (relative to peer universe if given)
    composite = None
    if peer_universe is not None and not peer_universe.empty:
        match = peer_universe[peer_universe["symbol"] == symbol.upper()]
        if not match.empty:
            composite = float(match.iloc[0]["composite"])
            out["momentum"] = float(match.iloc[0].get("momentum", 50))
        else:
            d = fetch_ticker(symbol)
            if d:
                d.pop("history", None)
                full = pd.concat([peer_universe, pd.DataFrame([d])], ignore_index=True)
                full = score(apply_filters(full))
                row = full[full["symbol"] == symbol.upper()]
                if not row.empty:
                    composite = float(row.iloc[0]["composite"])
                    out["momentum"] = float(row.iloc[0].get("momentum", 50))
    out["composite"] = composite

    # 3. Piotroski
    try:
        pf = piotroski_f_score(symbol)
        out["piotroski"] = pf["score"]
    except Exception as e:
        out["piotroski"] = None
        out["warnings"].append(f"Piotroski error: {e}")

    # 4. Determine Alert
    out["alert"] = _determine_alert(out)
    out["alert_reason"] = _build_reason(out)
    return out


def _determine_alert(d: dict) -> str:
    comp = d.get("composite") or 50
    mos  = d.get("margin_of_safety")
    piot = d.get("piotroski") or 5
    mom  = d.get("momentum") or 50

    if mos is None:
        if comp >= 75:  return "🟢 BUY"
        if comp <= 40:  return "🔴 SELL"
        return "⚪ HOLD"

    t = THRESHOLDS
    if (comp >= t["STRONG_BUY"]["composite_min"]
        and mos >= t["STRONG_BUY"]["mos_min"]
        and piot >= t["STRONG_BUY"]["piotroski_min"]
        and mom >= t["STRONG_BUY"]["momentum_min"]):
        return "🟢🟢 STRONG BUY"

    if (comp >= t["BUY"]["composite_min"]
        and mos >= t["BUY"]["mos_min"]
        and piot >= t["BUY"]["piotroski_min"]):
        return "🟢 BUY"

    if (comp <= t["STRONG_SELL"]["composite_max"]
        and mos <= t["STRONG_SELL"]["mos_max"]):
        return "🔴🔴 STRONG SELL"

    if (comp <= t["SELL"]["composite_max"]
        or mos <= t["SELL"]["mos_max"]):
        return "🔴 SELL"

    return "⚪ HOLD"


def _build_reason(d: dict) -> list[str]:
    reasons = []
    comp = d.get("composite")
    mos = d.get("margin_of_safety")
    piot = d.get("piotroski")
    mom = d.get("momentum")

    if comp is not None:
        if comp >= 80: reasons.append(f"✓ Composite สูง ({comp:.0f}/100)")
        elif comp <= 40: reasons.append(f"✗ Composite ต่ำ ({comp:.0f}/100)")

    if mos is not None:
        if mos >= 25: reasons.append(f"✓ Undervalued มาก ({mos:+.0f}%)")
        elif mos >= 10: reasons.append(f"✓ Undervalued ({mos:+.0f}%)")
        elif mos <= -25: reasons.append(f"✗ Overvalued มาก ({mos:+.0f}%)")
        elif mos <= -10: reasons.append(f"✗ Overvalued ({mos:+.0f}%)")
        else: reasons.append(f"= Fair Value ({mos:+.0f}%)")

    if piot is not None:
        if piot >= 7: reasons.append(f"✓ คุณภาพแกร่ง (F-Score {piot}/9)")
        elif piot <= 4: reasons.append(f"✗ คุณภาพอ่อน (F-Score {piot}/9)")

    if mom is not None:
        if mom >= 70: reasons.append(f"✓ Momentum ดี ({mom:.0f})")
        elif mom <= 30: reasons.append(f"✗ Momentum อ่อน ({mom:.0f})")

    return reasons


def evaluate_portfolio(tickers: list[str], peer_universe: pd.DataFrame | None = None) -> pd.DataFrame:
    """ตรวจหุ้นหลายตัว → return DataFrame เรียงตาม alert priority."""
    rows = []
    for tk in tickers:
        r = evaluate_single(tk, peer_universe=peer_universe)
        rows.append({
            "Ticker":   r["symbol"],
            "Alert":    r.get("alert", "⚪ HOLD"),
            "Price":    r.get("current_price"),
            "FairValue":r.get("fair_value"),
            "MoS %":    r.get("margin_of_safety"),
            "Composite":r.get("composite"),
            "F-Score":  r.get("piotroski"),
            "Momentum": r.get("momentum"),
            "Reasons":  " · ".join(r.get("alert_reason", [])),
        })
    df = pd.DataFrame(rows)

    priority = {"🟢🟢 STRONG BUY": 0, "🟢 BUY": 1, "⚪ HOLD": 2,
                "🔴 SELL": 3, "🔴🔴 STRONG SELL": 4}
    df["_p"] = df["Alert"].map(priority).fillna(2)
    df = df.sort_values("_p").drop(columns="_p")
    return df


def bulk_fair_value(tickers: list[str]) -> pd.DataFrame:
    """Compute fair value for many tickers at once. Light version (no FA tabs)."""
    rows = []
    for tk in tickers:
        try:
            fv = composite_fair_value(tk)
            rows.append({
                "Ticker": tk,
                "Price": fv.get("current_price"),
                "Fair Value": fv.get("composite_fair_value"),
                "MoS %": fv.get("margin_of_safety_pct"),
                "Verdict": fv.get("verdict"),
            })
        except Exception as e:
            rows.append({"Ticker": tk, "Verdict": f"Error: {e}"})
    df = pd.DataFrame(rows)
    if "MoS %" in df.columns:
        df = df.sort_values("MoS %", ascending=False, na_position="last")
    return df
