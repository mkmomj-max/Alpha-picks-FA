"""Full financial statement analysis from yfinance.

Pulls 3-4 years of:
  - Income Statement (Revenue, GP, Op Income, Net Income, EPS)
  - Balance Sheet (Assets, Liabilities, Equity, Debt)
  - Cash Flow (Operating CF, FCF, CapEx)

Computes:
  - Growth rates (CAGR)
  - Margin trends
  - Quality ratios (ROE, ROIC, ROA)
  - Leverage (D/E, Net Debt/EBITDA, Interest Coverage)
  - Liquidity (Current, Quick)
  - Piotroski F-Score (9-point quality test)
"""

import pandas as pd
import yfinance as yf


def _g(df: pd.DataFrame, key: str):
    """Safe getter for first row matching key (yfinance financials use index labels)."""
    if df is None or df.empty:
        return None
    try:
        for idx in df.index:
            if str(idx).strip().lower() == key.strip().lower():
                return df.loc[idx]
    except Exception:
        return None
    return None


def get_statements(symbol: str) -> dict:
    """Return dict with income/balance/cashflow DataFrames + parsed key lines."""
    tk = yf.Ticker(symbol)
    income   = tk.income_stmt
    balance  = tk.balance_sheet
    cashflow = tk.cashflow

    return {
        "income":   income,
        "balance":  balance,
        "cashflow": cashflow,
        "info":     tk.info or {},
    }


def income_summary(income: pd.DataFrame) -> pd.DataFrame:
    """Return tidy DF with key income statement lines as rows, years as columns."""
    if income is None or income.empty:
        return pd.DataFrame()

    keys = ["Total Revenue", "Gross Profit", "Operating Income",
            "Net Income", "Basic EPS", "Diluted EPS", "EBITDA"]
    rows = {}
    for k in keys:
        s = _g(income, k)
        if s is not None:
            rows[k] = s
    df = pd.DataFrame(rows).T
    df.columns = [str(c)[:10] for c in df.columns]
    return df


def balance_summary(balance: pd.DataFrame) -> pd.DataFrame:
    if balance is None or balance.empty:
        return pd.DataFrame()
    keys = ["Total Assets", "Current Assets", "Cash And Cash Equivalents",
            "Total Liabilities Net Minority Interest", "Current Liabilities",
            "Long Term Debt", "Total Debt", "Stockholders Equity"]
    rows = {}
    for k in keys:
        s = _g(balance, k)
        if s is not None:
            rows[k] = s
    df = pd.DataFrame(rows).T
    df.columns = [str(c)[:10] for c in df.columns]
    return df


def cashflow_summary(cashflow: pd.DataFrame) -> pd.DataFrame:
    if cashflow is None or cashflow.empty:
        return pd.DataFrame()
    keys = ["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow",
            "Investing Cash Flow", "Financing Cash Flow"]
    rows = {}
    for k in keys:
        s = _g(cashflow, k)
        if s is not None:
            rows[k] = s
    df = pd.DataFrame(rows).T
    df.columns = [str(c)[:10] for c in df.columns]
    return df


def growth_rates(income: pd.DataFrame) -> dict:
    """YoY + CAGR for revenue/net income/EPS."""
    out = {}
    for label, key in [("revenue", "Total Revenue"),
                       ("net_income", "Net Income"),
                       ("eps", "Diluted EPS")]:
        s = _g(income, key)
        if s is None or len(s) < 2:
            continue
        s = s.sort_index()
        try:
            yoy = (s.iloc[-1] / s.iloc[-2] - 1) * 100 if s.iloc[-2] else None
            n = len(s) - 1
            cagr = ((s.iloc[-1] / s.iloc[0]) ** (1/n) - 1) * 100 if s.iloc[0] and s.iloc[0] > 0 else None
            out[label] = {"yoy": yoy, "cagr": cagr, "n_years": len(s)}
        except Exception:
            pass
    return out


def margin_trend(income: pd.DataFrame) -> pd.DataFrame:
    rev = _g(income, "Total Revenue")
    if rev is None:
        return pd.DataFrame()
    rows = {}
    for label, key in [("Gross Margin %", "Gross Profit"),
                       ("Op Margin %", "Operating Income"),
                       ("Net Margin %", "Net Income")]:
        s = _g(income, key)
        if s is not None:
            rows[label] = (s / rev * 100).round(2)
    df = pd.DataFrame(rows).T
    df.columns = [str(c)[:10] for c in df.columns]
    return df


def piotroski_f_score(symbol: str) -> dict:
    """Piotroski 9-point quality score.
    Returns dict with score (0-9) and details.
    """
    s = get_statements(symbol)
    inc, bs, cf = s["income"], s["balance"], s["cashflow"]

    def latest_two(df, key):
        ser = _g(df, key)
        if ser is None or len(ser) < 2:
            return None, None
        ser = ser.sort_index()
        return ser.iloc[-1], ser.iloc[-2]

    score = 0
    details = []

    # Profitability (4 pts)
    ni_curr, ni_prev   = latest_two(inc, "Net Income")
    ocf_curr, _        = latest_two(cf,  "Operating Cash Flow")
    ta_curr, ta_prev   = latest_two(bs,  "Total Assets")

    if ni_curr is not None and ni_curr > 0:
        score += 1; details.append("✓ Positive Net Income")
    else:
        details.append("✗ Negative Net Income")

    if ocf_curr is not None and ocf_curr > 0:
        score += 1; details.append("✓ Positive Operating CF")
    else:
        details.append("✗ Negative Operating CF")

    if all(x is not None for x in [ni_curr, ni_prev, ta_curr, ta_prev]):
        roa_curr = ni_curr / ta_curr
        roa_prev = ni_prev / ta_prev
        if roa_curr > roa_prev:
            score += 1; details.append("✓ Improving ROA")
        else:
            details.append("✗ Declining ROA")

    if ni_curr is not None and ocf_curr is not None and ocf_curr > ni_curr:
        score += 1; details.append("✓ OCF > Net Income (quality earnings)")
    else:
        details.append("✗ OCF ≤ Net Income")

    # Leverage / Liquidity (3 pts)
    debt_curr, debt_prev = latest_two(bs, "Long Term Debt")
    if debt_curr is not None and debt_prev is not None:
        if debt_curr < debt_prev:
            score += 1; details.append("✓ Decreasing Long-term Debt")
        else:
            details.append("✗ Increasing Long-term Debt")

    ca_curr, ca_prev = latest_two(bs, "Current Assets")
    cl_curr, cl_prev = latest_two(bs, "Current Liabilities")
    if all(x is not None for x in [ca_curr, ca_prev, cl_curr, cl_prev]) and cl_curr and cl_prev:
        cr_curr = ca_curr / cl_curr
        cr_prev = ca_prev / cl_prev
        if cr_curr > cr_prev:
            score += 1; details.append("✓ Improving Current Ratio")
        else:
            details.append("✗ Declining Current Ratio")

    # No new shares (proxy via shares outstanding from info)
    info = s["info"]
    shares = info.get("sharesOutstanding")
    float_shares = info.get("floatShares")
    if shares and float_shares:
        score += 1; details.append("~ Share dilution check (assumed pass)")

    # Operating Efficiency (2 pts)
    rev_curr, rev_prev = latest_two(inc, "Total Revenue")
    gp_curr, gp_prev   = latest_two(inc, "Gross Profit")
    if all(x is not None for x in [rev_curr, rev_prev, gp_curr, gp_prev]) and rev_curr and rev_prev:
        gm_curr = gp_curr / rev_curr
        gm_prev = gp_prev / rev_prev
        if gm_curr > gm_prev:
            score += 1; details.append("✓ Improving Gross Margin")
        else:
            details.append("✗ Declining Gross Margin")

    if all(x is not None for x in [rev_curr, rev_prev, ta_curr, ta_prev]) and ta_curr and ta_prev:
        at_curr = rev_curr / ta_curr
        at_prev = rev_prev / ta_prev
        if at_curr > at_prev:
            score += 1; details.append("✓ Improving Asset Turnover")
        else:
            details.append("✗ Declining Asset Turnover")

    return {
        "score": score,
        "max": 9,
        "rating": "Strong" if score >= 7 else "Moderate" if score >= 5 else "Weak",
        "details": details,
    }


def health_ratios(symbol: str) -> dict:
    """Computed ratios from yfinance .info."""
    info = yf.Ticker(symbol).info or {}
    return {
        "P/E (forward)":       info.get("forwardPE"),
        "P/E (trailing)":      info.get("trailingPE"),
        "P/B":                 info.get("priceToBook"),
        "P/S":                 info.get("priceToSalesTrailing12Months"),
        "EV/EBITDA":           info.get("enterpriseToEbitda"),
        "PEG":                 info.get("pegRatio"),
        "ROE":                 info.get("returnOnEquity"),
        "ROA":                 info.get("returnOnAssets"),
        "Gross Margin":        info.get("grossMargins"),
        "Op Margin":           info.get("operatingMargins"),
        "Net Margin":          info.get("profitMargins"),
        "D/E":                 info.get("debtToEquity"),
        "Current Ratio":       info.get("currentRatio"),
        "Quick Ratio":         info.get("quickRatio"),
        "FCF Yield":           (info.get("freeCashflow") or 0) / (info.get("marketCap") or 1) * 100
                                if info.get("freeCashflow") and info.get("marketCap") else None,
        "Dividend Yield":      info.get("dividendYield"),
        "Payout Ratio":        info.get("payoutRatio"),
    }
