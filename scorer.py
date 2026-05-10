"""Composite scoring + filters."""

import pandas as pd

from config import FACTOR_WEIGHTS, FILTERS, QUALITY_BOOST
from factors import (
    valuation_score, growth_score, profitability_score,
    momentum_score, revisions_score, quality_score,
)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    f = FILTERS
    keep = (
        (df["market_cap"].fillna(0) >= f["min_market_cap"]) &
        (df["price"].fillna(0) >= f["min_price"]) &
        (df["avg_volume"].fillna(0) >= f["min_avg_volume"])
    )
    if f["require_pos_eps"]:
        keep &= (df["forward_eps"].fillna(-1) > 0)
    return df[keep].copy()


def score(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["valuation"]     = valuation_score(df)
    df["growth"]        = growth_score(df)
    df["profitability"] = profitability_score(df)
    df["momentum"]      = momentum_score(df)
    df["revisions"]     = revisions_score(df)

    w = FACTOR_WEIGHTS
    df["composite"] = (
        df["valuation"]     * w["valuation"]     +
        df["growth"]        * w["growth"]        +
        df["profitability"] * w["profitability"] +
        df["momentum"]      * w["momentum"]      +
        df["revisions"]     * w["revisions"]
    )

    if QUALITY_BOOST:
        df["quality"] = quality_score(df)
        df["composite"] = df["composite"] * 0.85 + df["quality"] * 0.15

    df["rating"] = df["composite"].apply(_label)
    return df.sort_values("composite", ascending=False)


def _label(score: float) -> str:
    if score >= 85: return "Strong Buy"
    if score >= 70: return "Buy"
    if score >= 50: return "Hold"
    if score >= 30: return "Sell"
    return "Strong Sell"
