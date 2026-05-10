"""History of Alpha Picks (extracted from screenshots).
Used as: (1) reference profile for "next picks" similarity, (2) backtest comparison.
"""

ALPHA_PICKS = [
    # ticker, pick_date, return_pct, sector, status, weight_pct
    ("STRL", "2023-08-01", 1253.20, "Industrials",            "Hold",        12.36),
    ("APP",  "2023-11-15", 1004.03, "Information Technology", "Strong Buy",   5.48),
    ("CLS",  "2023-10-16", 1275.64, "Information Technology", "Strong Buy",   5.15),
    ("AGX",  "2024-10-15",  473.14, "Industrials",            "Hold",         5.14),
    ("POWL", "2023-05-15", 1598.39, "Industrials",            "Hold",         4.47),
    ("CLS",  "2024-11-15",  362.61, "Information Technology", "Strong Buy",   4.19),
    ("TWLO", "2024-02-01",  181.02, "Information Technology", "Strong Buy",   3.80),
    ("CRDO", "2025-02-03",  173.43, "Information Technology", "Strong Buy",   2.98),
    ("MFC",  "2023-11-01",  127.39, "Financials",             "Hold",         2.90),
    ("EAT",  "2024-04-01",  170.60, "Consumer Discretionary", "Buy",          2.66),
    ("CAAP", "2023-05-01",  123.08, "Industrials",            "Hold",         2.56),
    ("STRL", "2025-08-01",  224.50, "Industrials",            "Hold",         2.56),
    ("BLBD", "2024-05-15",   34.43, "Industrials",            "Buy",          2.45),
    ("MU",   "2025-10-15",  291.49, "Information Technology", "Strong Buy",   2.34),
    ("UBER", "2023-06-01",  101.20, "Industrials",            "Hold",         2.29),
    ("EZPW", "2025-04-01",  116.95, "Financials",             "Strong Buy",   2.18),
    ("TTMI", "2025-10-01",  166.67, "Information Technology", "Hold",         2.12),
    ("RCL",  "2024-03-15",  113.78, "Consumer Discretionary", "Hold",         2.03),
    ("CVSA", "2025-07-15",   73.88, "Consumer Discretionary", "Hold",         1.98),
    ("SSRM", "2025-06-16",  164.91, "Materials",              "Hold",         1.88),
    ("TMUS", "2023-09-15",   34.49, "Communication Services", "Hold",         1.87),
    ("SYF",  "2024-09-03",   48.06, "Financials",             "Buy",          1.85),
    ("BRK.B","2024-07-01",   16.63, "Financials",             "Hold",         1.68),
    ("CCL",  "2024-11-01",   20.24, "Consumer Discretionary", "Hold",         1.54),
    ("UNFI", "2024-05-15",   73.53, "Consumer Staples",       "Strong Buy",   1.54),
    ("SKYW", "2024-06-03",   10.28, "Industrials",            "Hold",         1.53),
    ("OKTA", "2025-02-15",   -6.11, "Information Technology", "Hold",         1.51),
    ("POWL", "2024-10-01",  312.43, "Industrials",            "Hold",         1.49),
    ("ALL",  "2025-01-02",   11.21, "Financials",             "Hold",         1.49),
    ("MFC",  "2025-05-01",   29.81, "Financials",             "Hold",         1.42),
    ("ARQT", "2025-03-17",   28.07, "Health Care",            "Hold",         1.28),
    ("EAT",  "2025-04-15",   -8.62, "Consumer Discretionary", "Buy",          1.19),
    ("KGC",  "2025-09-02",   47.93, "Materials",              "Buy",          1.16),
    ("CDE",  "2025-09-15",   12.51, "Materials",              "Buy",          0.94),
    ("TIGO", "2025-12-15",   50.11, "Communication Services", "Hold",         0.84),
    ("PARR", "2025-11-17",   40.39, "Energy",                 "Strong Buy",   0.78),
    ("VISN", "2025-08-15",  -23.85, "Industrials",            "Hold",         0.70),
    ("INCY", "2025-11-03",    0.63, "Health Care",            "Buy",          0.63),
    ("LITE", "2026-03-16",   40.03, "Information Technology", "Strong Buy",   0.61),
    ("DY",   "2026-02-02",   12.18, "Industrials",            "Buy",          0.60),
    ("NEM",  "2026-01-15",    2.30, "Materials",              "Strong Buy",   0.56),
    ("CSTM", "2026-04-01",   25.81, "Materials",              "Strong Buy",   0.55),
    ("B",    "2026-01-02",   -1.01, "Materials",              "Buy",          0.54),
    ("FN",   "2026-03-02",    9.13, "Information Technology", "Hold",         0.52),
    ("GM",   "2026-02-17",   -2.38, "Consumer Discretionary", "Strong Buy",   0.46),
    ("NEXA", "2026-04-15",    3.84, "Materials",              "Strong Buy",   0.43),
    ("CRDO", "2026-05-01",    4.71, "Information Technology", "Strong Buy",   0.43),
    ("W",    "2025-12-01",  -40.61, "Consumer Discretionary", "Hold",         0.36),
]


def get_unique_tickers():
    return sorted(set(p[0] for p in ALPHA_PICKS))


def sector_breakdown():
    from collections import Counter
    c = Counter(p[3] for p in ALPHA_PICKS)
    total = sum(c.values())
    return {s: (n, n / total * 100) for s, n in c.most_common()}


def winners(threshold=100.0):
    return [p for p in ALPHA_PICKS if p[2] >= threshold]


def losers(threshold=0.0):
    return [p for p in ALPHA_PICKS if p[2] < threshold]


def stats():
    rets = [p[2] for p in ALPHA_PICKS]
    n = len(rets)
    avg = sum(rets) / n
    win_rate = sum(1 for r in rets if r > 0) / n * 100
    median = sorted(rets)[n // 2]
    return {
        "count":      n,
        "avg_return": avg,
        "median":     median,
        "win_rate":   win_rate,
        "best":       max(rets),
        "worst":      min(rets),
    }


if __name__ == "__main__":
    s = stats()
    print(f"Total picks:  {s['count']}")
    print(f"Avg return:   {s['avg_return']:.1f}%")
    print(f"Median:       {s['median']:.1f}%")
    print(f"Win rate:     {s['win_rate']:.1f}%")
    print(f"Best:         {s['best']:.1f}%")
    print(f"Worst:        {s['worst']:.1f}%")
    print()
    print("Sector breakdown:")
    for sec, (n, pct) in sector_breakdown().items():
        bar = "█" * int(pct / 2)
        print(f"  {sec:28s} {n:3d}  {pct:5.1f}%  {bar}")
