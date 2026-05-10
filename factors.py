"""Factor calculations: Valuation, Growth, Profitability, Momentum, Revisions, Quality."""

import numpy as np
import pandas as pd


def _z(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    mu, sd = s.mean(), s.std()
    if sd == 0 or pd.isna(sd):
        return pd.Series(0.0, index=series.index)
    return (s - mu) / sd


def _winsorize(s: pd.Series, lo: float = 0.02, hi: float = 0.98) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    ql, qh = s.quantile(lo), s.quantile(hi)
    return s.clip(ql, qh)


def valuation_score(df: pd.DataFrame) -> pd.Series:
    """Lower P/E, P/S, EV/EBITDA, PEG = better. Returns 0-100."""
    pe   = -_z(_winsorize(df["pe_forward"].where(df["pe_forward"] > 0)))
    ps   = -_z(_winsorize(df["ps"].where(df["ps"] > 0)))
    ev   = -_z(_winsorize(df["ev_ebitda"].where(df["ev_ebitda"] > 0)))
    peg  = -_z(_winsorize(df["peg"].where((df["peg"] > 0) & (df["peg"] < 5))))
    composite = pd.concat([pe, ps, ev, peg], axis=1).mean(axis=1, skipna=True)
    return _to_pct(composite)


def growth_score(df: pd.DataFrame) -> pd.Series:
    rev = _z(_winsorize(df["rev_growth"]))
    eps = _z(_winsorize(df["earnings_growth"]))
    composite = pd.concat([rev, eps], axis=1).mean(axis=1, skipna=True)
    return _to_pct(composite)


def profitability_score(df: pd.DataFrame) -> pd.Series:
    gm  = _z(_winsorize(df["gross_margin"]))
    op  = _z(_winsorize(df["op_margin"]))
    pm  = _z(_winsorize(df["profit_margin"]))
    roe = _z(_winsorize(df["roe"]))
    roa = _z(_winsorize(df["roa"]))
    composite = pd.concat([gm, op, pm, roe, roa], axis=1).mean(axis=1, skipna=True)
    return _to_pct(composite)


def momentum_score(df: pd.DataFrame) -> pd.Series:
    r3  = _z(_winsorize(df["return_3m"]))
    r6  = _z(_winsorize(df["return_6m"]))
    r12 = _z(_winsorize(df["return_12m"]))
    composite = (r3 * 0.2 + r6 * 0.4 + r12 * 0.4)
    return _to_pct(composite)


def revisions_score(df: pd.DataFrame) -> pd.Series:
    """Proxy for EPS revisions: rec_mean (lower=stronger buy) + target upside."""
    rec = -_z(_winsorize(df["rec_mean"]))
    upside = (df["target_mean"] - df["price"]) / df["price"]
    ups = _z(_winsorize(upside))
    composite = pd.concat([rec, ups], axis=1).mean(axis=1, skipna=True)
    return _to_pct(composite)


def quality_score(df: pd.DataFrame) -> pd.Series:
    """Bonus: low debt, healthy current ratio, positive FCF."""
    de = -_z(_winsorize(df["debt_to_equity"].where(df["debt_to_equity"] > 0)))
    cr = _z(_winsorize(df["current_ratio"]))
    fcf_yield = df["fcf"] / df["market_cap"]
    fy = _z(_winsorize(fcf_yield))
    composite = pd.concat([de, cr, fy], axis=1).mean(axis=1, skipna=True)
    return _to_pct(composite)


def _to_pct(z_score: pd.Series) -> pd.Series:
    """Convert z-score to 0-100 percentile rank."""
    return z_score.rank(pct=True) * 100
