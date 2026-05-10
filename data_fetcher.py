"""Fetch fundamentals + price data via yfinance."""

import time
import warnings
import yfinance as yf
import pandas as pd

warnings.filterwarnings("ignore")


def fetch_ticker(symbol: str, retries: int = 2) -> dict | None:
    """Return dict of fundamentals + price history. None on failure."""
    for attempt in range(retries + 1):
        try:
            tk = yf.Ticker(symbol)
            info = tk.info or {}
            if not info.get("regularMarketPrice") and not info.get("currentPrice"):
                return None

            hist = tk.history(period="1y", auto_adjust=True)
            if hist.empty:
                return None

            price = info.get("currentPrice") or info.get("regularMarketPrice")
            return {
                "symbol":          symbol,
                "name":            info.get("longName") or info.get("shortName") or symbol,
                "sector":          info.get("sector", "Unknown"),
                "industry":        info.get("industry", "Unknown"),
                "market_cap":      info.get("marketCap"),
                "price":           price,
                "pe_forward":      info.get("forwardPE"),
                "pe_trailing":     info.get("trailingPE"),
                "ps":              info.get("priceToSalesTrailing12Months"),
                "ev_ebitda":       info.get("enterpriseToEbitda"),
                "peg":             info.get("pegRatio") or info.get("trailingPegRatio"),
                "rev_growth":      info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "gross_margin":    info.get("grossMargins"),
                "op_margin":       info.get("operatingMargins"),
                "profit_margin":   info.get("profitMargins"),
                "roe":             info.get("returnOnEquity"),
                "roa":             info.get("returnOnAssets"),
                "fcf":             info.get("freeCashflow"),
                "revenue":         info.get("totalRevenue"),
                "debt_to_equity":  info.get("debtToEquity"),
                "current_ratio":   info.get("currentRatio"),
                "forward_eps":     info.get("forwardEps"),
                "trailing_eps":    info.get("trailingEps"),
                "avg_volume":      info.get("averageVolume"),
                "beta":            info.get("beta"),
                "rec_mean":        info.get("recommendationMean"),
                "target_mean":     info.get("targetMeanPrice"),
                "history":         hist,
            }
        except Exception as e:
            if attempt == retries:
                print(f"  [skip] {symbol}: {e}")
                return None
            time.sleep(1)
    return None


def fetch_universe(symbols: list[str], sleep: float = 0.1) -> pd.DataFrame:
    """Fetch many tickers, return DataFrame. Drops history column for compactness."""
    rows = []
    for i, sym in enumerate(symbols, 1):
        if i % 25 == 0:
            print(f"  ...fetched {i}/{len(symbols)}")
        d = fetch_ticker(sym)
        if d is None:
            continue
        h = d.pop("history")
        if not h.empty:
            d["return_6m"]   = _pct_return(h, 126)
            d["return_12m"]  = _pct_return(h, 252)
            d["return_3m"]   = _pct_return(h, 63)
            d["volatility"]  = h["Close"].pct_change().std() * (252 ** 0.5)
            d["above_50ma"]  = float(h["Close"].iloc[-1]) > h["Close"].tail(50).mean()
            d["above_200ma"] = float(h["Close"].iloc[-1]) > h["Close"].tail(200).mean()
        rows.append(d)
        time.sleep(sleep)
    return pd.DataFrame(rows)


def _pct_return(hist: pd.DataFrame, days: int) -> float | None:
    if len(hist) < days + 1:
        return None
    end = float(hist["Close"].iloc[-1])
    start = float(hist["Close"].iloc[-days - 1])
    return (end / start - 1) * 100 if start > 0 else None
