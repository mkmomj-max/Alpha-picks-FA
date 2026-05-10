"""High-level screening orchestrator."""

import pandas as pd

from data_fetcher import fetch_universe
from scorer import apply_filters, score


def load_universe(path: str = "universe.txt") -> list[str]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.append(line.upper())
    return sorted(set(out))


def run_screen(universe: list[str] | None = None, path: str = "universe.txt") -> pd.DataFrame:
    if universe is None:
        universe = load_universe(path)
    print(f"Fetching {len(universe)} tickers...")
    raw = fetch_universe(universe)
    print(f"  got {len(raw)} valid responses")
    filtered = apply_filters(raw)
    print(f"  {len(filtered)} pass filters")
    return score(filtered)
