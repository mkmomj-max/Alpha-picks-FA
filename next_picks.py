"""Find candidates that match the 'Alpha Picks profile'.

Strategy:
1. Compute centroid feature vector of past Alpha Picks (especially WINNERS).
2. Score new candidates by:
   (a) Composite quant score (from scorer.py)
   (b) Cosine similarity to winner-centroid
   (c) Sector-theme bonus (Industrials/IT/Materials)
3. Combine and rank.
"""

import numpy as np
import pandas as pd

from alpha_picks_history import ALPHA_PICKS, get_unique_tickers


SIMILARITY_FEATURES = [
    "valuation", "growth", "profitability", "momentum", "revisions",
]

THEME_SECTORS = {
    "Industrials":            1.20,
    "Information Technology": 1.20,
    "Technology":             1.20,
    "Materials":              1.10,
    "Basic Materials":        1.10,
    "Financials":             1.05,
    "Financial Services":     1.05,
    "Consumer Discretionary": 1.00,
    "Consumer Cyclical":      1.00,
    "Health Care":            0.95,
    "Healthcare":             0.95,
    "Energy":                 0.95,
    "Utilities":              0.85,
    "Consumer Staples":       0.90,
    "Real Estate":            0.85,
    "Communication Services": 1.00,
}


def build_winner_profile(scored_universe: pd.DataFrame) -> pd.Series | None:
    """Take historical winners (return >= 100%) that exist in the scored universe,
    and average their factor scores. Returns None if no overlap."""
    winners = [p[0] for p in ALPHA_PICKS if p[2] >= 100.0]
    sub = scored_universe[scored_universe["symbol"].isin(winners)]
    if sub.empty:
        return None
    return sub[SIMILARITY_FEATURES].mean()


def cosine_similarity(row: pd.Series, centroid: pd.Series) -> float:
    a = row[SIMILARITY_FEATURES].fillna(50).values.astype(float)
    b = centroid.fillna(50).values.astype(float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def rank_next_picks(scored: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Add similarity + theme adjustments, return top N candidates."""
    df = scored.copy()
    centroid = build_winner_profile(df)

    if centroid is not None:
        df["similarity"] = df.apply(lambda r: cosine_similarity(r, centroid), axis=1) * 100
    else:
        df["similarity"] = 50.0

    df["theme_mult"] = df["sector"].map(THEME_SECTORS).fillna(1.0)

    df["alpha_score"] = (
        df["composite"] * 0.55 +
        df["similarity"] * 0.30 +
        df["momentum"] * 0.15
    ) * df["theme_mult"]

    held = set(get_unique_tickers())
    df["already_picked"] = df["symbol"].isin(held)
    df = df[~df["already_picked"]]

    return df.sort_values("alpha_score", ascending=False).head(top_n)
