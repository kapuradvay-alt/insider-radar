"""How much could the main-test median excess return be noise? (docs/backtest_design.md)

Run from the project folder:
    python src/uncertainty.py > results/uncertainty_main_2026-11-22.txt

Uses the main test only (v1 signals before 2025), the 3-month horizon, stocks valued at the
last available price, 1% round-trip cost. It resamples the signals many times and shows the
range the median would plausibly fall in. Three ways of resampling are shown, because signals
at one company, or in one month, are not independent of each other.
"""
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
import backtest as b   # noqa: E402

warnings.filterwarnings("ignore")


def interval(df, col, rng, by=None, n=3000):
    meds = []
    if by is None:
        v = df[col].values
        for _ in range(n):
            meds.append(np.median(rng.choice(v, len(v))))
    else:
        groups = [g[col].values for _, g in df.groupby(by)]
        for _ in range(n):
            idx = rng.integers(0, len(groups), len(groups))
            meds.append(np.median(np.concatenate([groups[i] for i in idx])))
    lo, hi = np.percentile(meds, [2.5, 97.5])
    return f"[{lo * 100:.1f}%, {hi * 100:.1f}%]"


if __name__ == "__main__":
    sig = pd.read_csv(b.SIGNALS, parse_dates=["signal_date"])
    sig = sig[(sig["rule"] == "v1") & (sig["signal_date"] < b.SPLIT_DATE)].sort_values("signal_date")
    prices = b.Prices(pd.read_csv(b.PRICES, index_col=0, parse_dates=True))
    d = b.returns_for(sig, prices, 63)
    d["ISSUERCIK"] = sig["ISSUERCIK"].values
    d = d[d["status"] == "ok"].copy()
    d["month"] = d["signal_date"].dt.to_period("M")
    for bench in ["spy", "iwm"]:
        d[f"ex_{bench}"] = d["ret"] - b.COST - d[bench]
    rng = np.random.default_rng(0)
    print("MAIN TEST, v1, 3 months, last price, after 1% cost. Signals:", len(d))
    for bench in ["spy", "iwm"]:
        col = f"ex_{bench}"
        print(f"\nMedian excess return vs {bench.upper()}: {d[col].median() * 100:.1f}%")
        print("  95% range, resampling signals:  ", interval(d, col, rng))
        print("  95% range, resampling companies:", interval(d, col, rng, by="ISSUERCIK"))
        print("  95% range, resampling months:   ", interval(d, col, rng, by="month"))
    print(f"\n3-month stock returns: 25th percentile {d['ret'].quantile(.25) * 100:.1f}%, "
          f"75th percentile {d['ret'].quantile(.75) * 100:.1f}%, "
          f"worst {d['ret'].min() * 100:.1f}%, best {d['ret'].max() * 100:.1f}%")
    print(f"Share of signals with a 3-month loss: {(d['ret'] < 0).mean():.0%}")
