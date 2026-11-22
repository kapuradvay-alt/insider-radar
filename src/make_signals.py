"""Make the list of signals to test (no stock returns are used).

Run from the project folder:
    python src/make_signals.py data/people_2022_2025.csv

Rules: docs/cluster_rule.md (v1), docs/cluster_rule_v2.md (v2),
docs/cooldown_and_period.md (90-day cooldown). Output: data/signals_2022_2025.csv
with one row per signal and the column `rule` (v1 or v2).
"""
import sys

import pandas as pd

sys.path.insert(0, "src")
from clusters import load_people, find_clusters   # noqa: E402

N, WINDOW, MIN_VALUE, COOLDOWN = 3, 14, 10000, 90


def add_ticker(sig, people):
    """Ticker the company used in the filings that make up each signal."""
    p = people[["ISSUERCIK", "ISSUERTRADINGSYMBOL", "filing_date"]].copy()
    p["t"] = p["ISSUERTRADINGSYMBOL"].str.upper().str.strip()
    m = sig.reset_index().merge(p, on="ISSUERCIK")
    m = m[(m["filing_date"] <= m["signal_date"]) &
          (m["filing_date"] > m["signal_date"] - pd.Timedelta(days=WINDOW))]
    tick = m.groupby("index")["t"].agg(lambda s: s.value_counts().idxmax())
    out = sig.copy()
    out["ticker"] = tick
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python src/make_signals.py data/people_2022_2025.csv")
    people = load_people(sys.argv[1])
    parts = []
    for rule, mtd in [("v1", 1), ("v2", 2)]:
        sig = find_clusters(people, N, WINDOW, MIN_VALUE, cooldown=COOLDOWN, min_trade_dates=mtd)
        sig = add_ticker(sig, people)
        sig.insert(0, "rule", rule)
        parts.append(sig)
    allsig = pd.concat(parts, ignore_index=True).sort_values(["rule", "signal_date"])
    out_path = "data/signals_2022_2025.csv"
    allsig.to_csv(out_path, index=False)

    main = allsig["signal_date"] < "2025-01-01"
    print(allsig.groupby("rule").size().rename("signals").to_string())
    print("\nmain test (signal date before 2025):", int((main & (allsig["rule"] == "v1")).sum()), "v1 signals")
    print("held-out (2025):", int((~main & (allsig["rule"] == "v1")).sum()), "v1 signals")
    print("signals without a ticker:", int(allsig["ticker"].isna().sum()))
    print("different tickers:", allsig["ticker"].nunique())
    print("saved", out_path)
