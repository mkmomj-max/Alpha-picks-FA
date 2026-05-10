"""Peer Comparison — เปรียบเทียบหุ้นกับคู่แข่งใน sector/industry."""

import pandas as pd
import yfinance as yf


SECTOR_PEERS = {
    "Technology": {
        "Semiconductors": ["NVDA", "AMD", "AVGO", "MRVL", "MU", "QCOM", "TSM", "INTC", "ON", "MCHP"],
        "Software": ["MSFT", "ORCL", "CRM", "ADBE", "NOW", "PANW", "CRWD", "ZS", "SNPS", "CDNS"],
        "Hardware": ["AAPL", "DELL", "HPQ", "STX", "WDC", "ANET", "CSCO", "JNPR"],
        "Networking": ["ANET", "CSCO", "JNPR", "CIEN", "EXTR"],
    },
    "Information Technology": {
        "Semiconductors": ["NVDA", "AMD", "AVGO", "MRVL", "MU", "QCOM", "TSM", "INTC"],
        "Software": ["MSFT", "ORCL", "CRM", "ADBE", "NOW"],
    },
    "Healthcare": {
        "Pharma": ["LLY", "PFE", "JNJ", "MRK", "ABBV", "BMY"],
        "Biotech": ["VRTX", "REGN", "GILD", "AMGN", "MRNA", "BIIB"],
    },
    "Health Care": {
        "Pharma": ["LLY", "PFE", "JNJ", "MRK", "ABBV"],
        "Biotech": ["VRTX", "REGN", "GILD", "AMGN"],
    },
    "Financial Services": {
        "Banks": ["JPM", "BAC", "WFC", "C", "GS", "MS"],
        "Insurance": ["BRK.B", "PGR", "ALL", "TRV", "AIG", "MET", "PRU"],
        "Asset Management": ["BLK", "BX", "KKR", "APO", "TROW"],
    },
    "Financials": {
        "Banks": ["JPM", "BAC", "WFC", "C", "GS"],
        "Insurance": ["BRK.B", "PGR", "ALL", "TRV"],
    },
    "Consumer Cyclical": {
        "Retail": ["AMZN", "WMT", "COST", "HD", "LOW", "TGT"],
        "Auto": ["TSLA", "GM", "F", "TM", "STLA"],
        "Hospitality": ["RCL", "CCL", "NCLH", "MAR", "HLT"],
    },
    "Consumer Discretionary": {
        "Retail": ["AMZN", "WMT", "COST", "HD"],
        "Auto": ["TSLA", "GM", "F", "TM"],
        "Hospitality": ["RCL", "CCL", "NCLH", "EAT", "DRI"],
    },
    "Industrials": {
        "Aerospace": ["BA", "LMT", "RTX", "GD", "NOC"],
        "Construction": ["CAT", "DE", "URI", "PWR", "FIX", "STRL"],
        "Power": ["GEV", "ETN", "POWL", "AGX", "VRT", "HUBB"],
    },
    "Energy": {
        "Oil & Gas": ["XOM", "CVX", "COP", "MPC", "VLO", "PSX", "PARR"],
    },
    "Materials": {
        "Mining/Metals": ["FCX", "SCCO", "RIO", "NEM", "GOLD", "AEM", "KGC", "B"],
    },
    "Basic Materials": {
        "Mining/Metals": ["FCX", "SCCO", "RIO", "NEM", "GOLD", "AEM", "KGC"],
    },
    "Utilities": {
        "Electric": ["NEE", "DUK", "SO", "AEP", "D"],
    },
    "Communication Services": {
        "Telecom": ["VZ", "T", "TMUS", "CMCSA", "TIGO"],
        "Media": ["GOOGL", "META", "NFLX", "DIS"],
    },
    "Real Estate": {
        "Data Center": ["EQIX", "DLR", "IRM"],
        "Retail REIT": ["O", "SPG", "REG"],
    },
}


def find_peers(symbol: str, max_peers: int = 8) -> list[str]:
    """Auto-detect sector and return list of peer tickers."""
    info = yf.Ticker(symbol).info or {}
    sector = info.get("sector", "")
    industry = info.get("industry", "")

    candidates = set()
    sector_dict = SECTOR_PEERS.get(sector, {})
    for sub, tickers in sector_dict.items():
        if industry and sub.lower() in industry.lower():
            candidates.update(tickers)
            break
    if not candidates:
        for tickers in sector_dict.values():
            candidates.update(tickers)

    candidates.discard(symbol.upper())
    return sorted(candidates)[:max_peers]


def compare_peers(symbol: str, peers: list[str] | None = None) -> pd.DataFrame:
    """Build comparison table with key metrics."""
    if peers is None:
        peers = find_peers(symbol)
    all_tickers = [symbol.upper()] + [p for p in peers if p != symbol.upper()]

    rows = []
    for tk in all_tickers:
        try:
            info = yf.Ticker(tk).info or {}
            if not info.get("currentPrice") and not info.get("regularMarketPrice"):
                continue
            rows.append({
                "Ticker":         tk,
                "Name":           (info.get("shortName") or "")[:25],
                "Price":          info.get("currentPrice") or info.get("regularMarketPrice"),
                "Mkt Cap (B)":    (info.get("marketCap") or 0) / 1e9,
                "P/E (fwd)":      info.get("forwardPE"),
                "P/S":            info.get("priceToSalesTrailing12Months"),
                "EV/EBITDA":      info.get("enterpriseToEbitda"),
                "PEG":            info.get("pegRatio"),
                "Rev Growth %":   (info.get("revenueGrowth") or 0) * 100,
                "Op Margin %":    (info.get("operatingMargins") or 0) * 100,
                "ROE %":          (info.get("returnOnEquity") or 0) * 100,
                "D/E":            info.get("debtToEquity"),
                "Div Yield %":    (info.get("dividendYield") or 0) * 100,
            })
        except Exception:
            continue

    df = pd.DataFrame(rows)
    return df


def relative_rank(df: pd.DataFrame, symbol: str) -> dict:
    """Rank target ticker among peers for each metric."""
    if df.empty or symbol.upper() not in df["Ticker"].values:
        return {}

    ranks = {}
    lower_better = ["P/E (fwd)", "P/S", "EV/EBITDA", "PEG", "D/E"]
    higher_better = ["Rev Growth %", "Op Margin %", "ROE %", "Div Yield %"]

    n = len(df)
    target_idx = df.index[df["Ticker"] == symbol.upper()][0]

    for metric in lower_better + higher_better:
        if metric not in df.columns:
            continue
        s = pd.to_numeric(df[metric], errors="coerce")
        if s.isna().all():
            continue
        ascending = metric in lower_better
        rk = s.rank(ascending=ascending, na_option="bottom")
        target_rank = rk.iloc[target_idx]
        if pd.notna(target_rank):
            ranks[metric] = {
                "rank":  int(target_rank),
                "of":    int(s.notna().sum()),
                "value": s.iloc[target_idx],
                "best":  s.min() if ascending else s.max(),
            }
    return ranks
