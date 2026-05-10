"""Per-ticker manual overrides — stored as JSON.

Schema:
{
  "WAB": {
    "adj_eps_ttm": 8.97,
    "adj_eps_fwd": 10.45,
    "revenue_growth": 0.10,
    "eps_growth": 0.14,
    "custom_pe": 25,
    "custom_wacc": 0.09,
    "bear_fv": 207,
    "base_fv": 270,
    "bull_fv": 335,
    "notes": "Backlog $30.8B (+38%), raised guidance, $1.2B buyback",
    "source": "Analyst report May 2026",
    "updated_at": "2026-05-10",
  },
  ...
}
"""

import json
import os
from datetime import date

OVERRIDES_PATH = "ticker_overrides.json"


SCHEMA = {
    "adj_eps_ttm":     {"label": "Adjusted EPS (TTM)", "unit": "$"},
    "adj_eps_fwd":     {"label": "Adjusted EPS (Forward 1Y)", "unit": "$"},
    "adj_eps_2y":      {"label": "Adjusted EPS (Forward 2Y)", "unit": "$"},
    "revenue_growth":  {"label": "Revenue Growth (decimal, e.g. 0.10 = 10%)", "unit": "%"},
    "eps_growth":      {"label": "EPS Growth (decimal)", "unit": "%"},
    "custom_pe":       {"label": "Custom P/E Multiple", "unit": "×"},
    "custom_ev_ebitda":{"label": "Custom EV/EBITDA", "unit": "×"},
    "custom_wacc":     {"label": "Custom WACC (decimal, 0.09 = 9%)", "unit": "%"},
    "fcf_override":    {"label": "FCF Override (USD)", "unit": "$"},
    "bear_fv":         {"label": "Bear Case Fair Value", "unit": "$"},
    "base_fv":         {"label": "Base Case Fair Value", "unit": "$"},
    "bull_fv":         {"label": "Bull Case Fair Value", "unit": "$"},
    "notes":           {"label": "Notes / Catalysts", "unit": ""},
    "source":          {"label": "Source", "unit": ""},
}


def load_overrides() -> dict:
    if not os.path.exists(OVERRIDES_PATH):
        return {}
    try:
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_overrides(data: dict) -> None:
    with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_override(symbol: str) -> dict:
    return load_overrides().get(symbol.upper(), {})


def set_override(symbol: str, fields: dict) -> dict:
    data = load_overrides()
    sym = symbol.upper()
    existing = data.get(sym, {})
    cleaned = {k: v for k, v in fields.items() if v not in (None, "", 0) or k in ("notes", "source")}
    existing.update(cleaned)
    existing["updated_at"] = str(date.today())
    data[sym] = existing
    save_overrides(data)
    return existing


def delete_override(symbol: str) -> bool:
    data = load_overrides()
    sym = symbol.upper()
    if sym in data:
        del data[sym]
        save_overrides(data)
        return True
    return False


def list_overrides() -> list[dict]:
    data = load_overrides()
    rows = []
    for sym, fields in data.items():
        row = {"Ticker": sym, "Updated": fields.get("updated_at", "")}
        for k in ["adj_eps_fwd", "custom_pe", "custom_wacc",
                  "base_fv", "source"]:
            if k in fields:
                row[k] = fields[k]
        rows.append(row)
    return rows
