"""CLI entry point.

Usage:
    python run.py history
    python run.py screen [--top N]
    python run.py next-picks [--top N]
    python run.py analyze TICKER
"""

import argparse
import sys

import pandas as pd
from tabulate import tabulate

from alpha_picks_history import stats, sector_breakdown, ALPHA_PICKS
from screener import run_screen
from next_picks import rank_next_picks
from data_fetcher import fetch_ticker
from scorer import score
from factors import (
    valuation_score, growth_score, profitability_score,
    momentum_score, revisions_score,
)


COLUMNS_DISPLAY = [
    "symbol", "name", "sector", "price", "market_cap",
    "valuation", "growth", "profitability", "momentum", "revisions",
    "composite", "rating",
]


def cmd_history(_):
    s = stats()
    print(f"\n=== Alpha Picks History ===")
    print(f"Total picks:  {s['count']}")
    print(f"Avg return:   {s['avg_return']:.1f}%")
    print(f"Median:       {s['median']:.1f}%")
    print(f"Win rate:     {s['win_rate']:.1f}%")
    print(f"Best:         {s['best']:.1f}%")
    print(f"Worst:        {s['worst']:.1f}%")
    print("\nSector breakdown:")
    for sec, (n, pct) in sector_breakdown().items():
        bar = "#" * int(pct / 2)
        print(f"  {sec:28s} {n:3d}  {pct:5.1f}%  {bar}")


def cmd_screen(args):
    df = run_screen(path=args.universe)
    df = df.head(args.top)
    _print_table(df)
    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"\nSaved -> {args.csv}")


def cmd_next_picks(args):
    df = run_screen(path=args.universe)
    picks = rank_next_picks(df, top_n=args.top)
    cols = COLUMNS_DISPLAY + ["similarity", "alpha_score"]
    print("\n=== NEXT ALPHA-PICKS CANDIDATES ===")
    _print_table(picks, cols=cols)
    if args.csv:
        picks.to_csv(args.csv, index=False)
        print(f"\nSaved -> {args.csv}")


def cmd_analyze(args):
    sym = args.ticker.upper()
    print(f"Fetching {sym}...")
    d = fetch_ticker(sym)
    if d is None:
        print(f"No data for {sym}")
        return
    h = d.pop("history")
    if not h.empty:
        d["return_3m"]  = (h["Close"].iloc[-1] / h["Close"].iloc[-63]  - 1) * 100 if len(h) > 63  else None
        d["return_6m"]  = (h["Close"].iloc[-1] / h["Close"].iloc[-126] - 1) * 100 if len(h) > 126 else None
        d["return_12m"] = (h["Close"].iloc[-1] / h["Close"].iloc[-252] - 1) * 100 if len(h) > 252 else None
    df = pd.DataFrame([d])
    df = score(df)
    row = df.iloc[0]
    print(f"\n=== {row['symbol']} — {row['name']} ===")
    print(f"Sector:        {row['sector']}")
    print(f"Price:         ${row['price']}")
    print(f"Market cap:    ${row['market_cap']:,.0f}" if row['market_cap'] else "Market cap:    n/a")
    print(f"\n--- Factor Scores (0-100) ---")
    for f in ("valuation", "growth", "profitability", "momentum", "revisions"):
        bar = "#" * int(row[f] / 5)
        print(f"  {f:14s} {row[f]:5.1f}  {bar}")
    print(f"\nComposite:     {row['composite']:.1f}")
    print(f"Rating:        {row['rating']}")


def _print_table(df: pd.DataFrame, cols=None):
    cols = cols or COLUMNS_DISPLAY
    cols = [c for c in cols if c in df.columns]
    show = df[cols].copy()
    for c in show.select_dtypes(include="float").columns:
        show[c] = show[c].round(1)
    if "market_cap" in show.columns:
        show["market_cap"] = show["market_cap"].apply(
            lambda x: f"${x/1e9:.1f}B" if pd.notna(x) and x else "-"
        )
    print(tabulate(show, headers="keys", tablefmt="simple", showindex=False))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("history")

    sp = sub.add_parser("screen")
    sp.add_argument("--top", type=int, default=20)
    sp.add_argument("--csv", default=None)
    sp.add_argument("--universe", default="universe.txt")

    sp = sub.add_parser("next-picks")
    sp.add_argument("--top", type=int, default=15)
    sp.add_argument("--csv", default=None)
    sp.add_argument("--universe", default="universe.txt")

    sp = sub.add_parser("analyze")
    sp.add_argument("ticker")

    args = p.parse_args()
    {"history": cmd_history, "screen": cmd_screen,
     "next-picks": cmd_next_picks, "analyze": cmd_analyze}[args.cmd](args)


if __name__ == "__main__":
    main()
