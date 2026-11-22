"""Download split- and dividend-adjusted daily prices for every signal company, plus SPY
(S&P 500) and IWM (small caps). This is a separate download from the cleaning step,
because the cleaning files hold prices for only about 70 days around each trade.

Run from the project folder:
    python src/get_price_history.py data/signals_2022_2025.csv

Output: data/price_history_adj.csv (one column per ticker). If the file exists it is
reused. Delete it to download again.
"""
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")
from clean import _download   # noqa: E402

OUT = Path("data/price_history_adj.csv")
BENCHMARKS = ["SPY", "IWM"]


def fetch_all(names, start, end):
    frames = []
    for i in range(0, len(names), 100):
        try:
            frames.append(_download(names[i:i + 100], start, end, auto_adjust=True))
        except Exception as e:
            print("batch failed at", i, e)
        time.sleep(2)
    px = pd.concat(frames, axis=1)
    px.index = pd.to_datetime(px.index).tz_localize(None)
    px = px.loc[:, ~px.columns.duplicated()]

    for attempt in range(2):                      # Yahoo sometimes returns nothing without an error
        have = set(px.columns[px.notna().any()])
        missing = [n for n in names if n not in have]
        if not missing:
            break
        print(f"retry {attempt + 1}: {len(missing)} tickers had no prices", flush=True)
        time.sleep(10)
        extra = []
        for i in range(0, len(missing), 25):
            try:
                extra.append(_download(missing[i:i + 25], start, end, auto_adjust=True))
            except Exception as e:
                print("retry batch failed at", i, e)
            time.sleep(3)
        if extra:
            new = pd.concat(extra, axis=1)
            new.index = pd.to_datetime(new.index).tz_localize(None)
            new = new.loc[:, ~new.columns.duplicated()]
            px = px.combine_first(new)
    return px


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python src/get_price_history.py data/signals_2022_2025.csv")
    if OUT.exists():
        sys.exit(f"{OUT} already exists. Delete it first if you want to download again.")
    sig = pd.read_csv(sys.argv[1], parse_dates=["signal_date"])
    names = sorted({t.replace(".", "-") for t in sig["ticker"].dropna()} | set(BENCHMARKS))
    start = sig["signal_date"].min() - pd.Timedelta(days=7)
    end = min(pd.Timestamp.today().normalize() + pd.Timedelta(days=1),
              sig["signal_date"].max() + pd.Timedelta(days=400))
    print(f"{len(names)} tickers, {start.date()} to {end.date()}", flush=True)

    px = fetch_all(names, start, end)
    have = px.columns[px.notna().any()]
    print(f"price coverage: {len(have)} of {len(names)} tickers have Yahoo prices")
    for b in BENCHMARKS:
        if b not in have:
            sys.exit(f"No prices for benchmark {b}. Stopping, nothing saved.")
    px.to_csv(OUT)
    print("rows (days):", len(px), "| first day:", px.index.min().date(), "| last day:", px.index.max().date())
    print("saved", OUT)
