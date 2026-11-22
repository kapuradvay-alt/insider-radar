"""Sensitivity tests on the main test (signals before 2025). Grid: docs/sensitivity_tests.md.

Two steps, from the project folder:
    python src/sensitivity.py make                 (builds data/signals_sensitivity.csv)
    python src/get_price_history.py data/signals_sensitivity.csv --add
    python src/sensitivity.py run > results/sensitivity_main_2026-11-22.txt

Each variant changes ONE setting from the base rule and is measured the same way as the
headline result: 3-month horizon, stocks at last available price, 1% round-trip cost.
The 2025 held-out set is not used here.
"""
import sys
import warnings

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
import backtest as b                                  # noqa: E402
from clusters import load_people, find_clusters       # noqa: E402
from make_signals import add_ticker                   # noqa: E402

warnings.filterwarnings("ignore")
BASE = dict(n=3, window=14, min_value=10000, cooldown=90)
VARIANTS = {
    "base (3 insiders, 14 days, $10,000, cooldown 90)": {},
    "2 insiders": {"n": 2},
    "4 insiders": {"n": 4},
    "7-day window": {"window": 7},
    "30-day window": {"window": 30},
    "no minimum amount": {"min_value": 0},
    "$50,000 minimum": {"min_value": 50000},
    "cooldown 30 days": {"cooldown": 30},
    "cooldown 180 days": {"cooldown": 180},
}
PEOPLE = "data/people_2022_2025.csv"
OUT_SIGNALS = "data/signals_sensitivity.csv"
MAX_MISSING_SHARE = 0.03


def make():
    people = load_people(PEOPLE)
    parts = []
    for name, change in VARIANTS.items():
        params = {**BASE, **change}
        sig = find_clusters(people, params["n"], params["window"], params["min_value"],
                            cooldown=params["cooldown"])
        sig = add_ticker(sig, people, window=params["window"])
        sig.insert(0, "variant", name)
        parts.append(sig)
        print(f"{name}: {len(sig)} signals ({int((sig['signal_date'] < b.SPLIT_DATE).sum())} before 2025)")
    pd.concat(parts, ignore_index=True).to_csv(OUT_SIGNALS, index=False)
    print("saved", OUT_SIGNALS)


def month_range(d, col, rng, n=2000):
    groups = [g[col].values for _, g in d.groupby("month")]
    meds = [np.median(np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))]))
            for _ in range(n)]
    lo, hi = np.percentile(meds, [2.5, 97.5])
    return f"[{lo * 100:.1f}, {hi * 100:.1f}]"


def run():
    sig = pd.read_csv(OUT_SIGNALS, parse_dates=["signal_date"])
    sig = sig[sig["signal_date"] < b.SPLIT_DATE]
    px = pd.read_csv(b.PRICES, index_col=0, parse_dates=True)
    have = set(px.columns[px.notna().any()])
    miss = (~sig["ticker"].str.replace(".", "-", regex=False).isin(have)).mean()
    if miss > MAX_MISSING_SHARE:
        sys.exit(f"{miss:.0%} of the signals have no price history yet. First run: "
                 f"python src/get_price_history.py {OUT_SIGNALS} --add")
    prices = b.Prices(px)
    rng = np.random.default_rng(0)
    rows = []
    for name in VARIANTS:
        s = sig[sig["variant"] == name].sort_values("signal_date").reset_index(drop=True)
        d = b.returns_for(s, prices, 63)
        d["month"] = s["signal_date"].dt.to_period("M")
        stopped = int((d["status"] == "stopped trading").sum())
        d = d[d["status"].isin(["ok", "stopped trading"])].copy()
        r = {"variant": name, "signals": len(d), "stopped": stopped}
        for bench in ["spy", "iwm"]:
            d[f"ex_{bench}"] = d["ret_last"] - b.COST - d[bench]
            r[f"median ex {bench.upper()} %"] = f"{d[f'ex_{bench}'].median() * 100:.1f}"
            r[f"{bench}_range"] = month_range(d, f"ex_{bench}", rng)
            r[f"beat {bench.upper()} %"] = f"{(d[f'ex_{bench}'] > 0).mean() * 100:.0f}"
        rows.append(r)
    out = pd.DataFrame(rows).rename(columns={"spy_range": "range vs SPY", "iwm_range": "range vs IWM"})
    out = out[["variant", "signals", "stopped", "median ex SPY %", "range vs SPY", "beat SPY %",
               "median ex IWM %", "range vs IWM", "beat IWM %"]]
    print("MAIN TEST (signals before 2025), 3 months, last price, after 1% cost.")
    print("Medians and 95% ranges (resampling months) are in percentage points of excess return.\n")
    print(out.to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("make", "run"):
        sys.exit("Usage: python src/sensitivity.py make | run")
    make() if sys.argv[1] == "make" else run()
