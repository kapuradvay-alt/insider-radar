"""Backtest of the insider cluster signals. Design: docs/backtest_design.md.

Run from the project folder, after make_signals.py and get_price_history.py:
    python src/backtest.py

By default only signals dated BEFORE 2025 are used (the main test). The 2025 signals are the
held-out set and are locked. They are used only when you add both --holdout and --confirm-final,
and that is meant to be done once, at the very end.

Entry: close of the first trading day after the signal date. Exit: close N trading days later
(N = 63 for the 3-month primary horizon; 21 and 252 are secondary). Prices are split- and
dividend-adjusted. Benchmarks: SPY and IWM over the same dates.
"""
import sys

import numpy as np
import pandas as pd

SIGNALS = "data/signals_2022_2025.csv"
PRICES = "data/price_history_adj.csv"
HORIZONS = {"1 month": 21, "3 months (primary)": 63, "12 months": 252}
PRIMARY = "3 months (primary)"
COST = 0.01                 # round-trip cost, a placeholder assumption (docs/backtest_design.md)
MAX_STALE_DAYS = 7          # a price older than this counts as "stopped trading"
SPLIT_DATE = pd.Timestamp("2025-01-01")


class Prices:
    def __init__(self, px):
        self.px = px
        self.series = {c: px[c].dropna() for c in px.columns}
        self.cal = self.series["SPY"].index           # trading days

    def at(self, ticker, date):
        """Last price on or before `date`, or None if there is none within MAX_STALE_DAYS."""
        s = self.series.get(ticker.replace(".", "-"))
        if s is None or len(s) == 0:
            return None
        pos = s.index.searchsorted(date, side="right") - 1
        if pos < 0:
            return None
        d = s.index[pos]
        if (date - d).days > MAX_STALE_DAYS:
            return None
        return float(s.iloc[pos]), d

    def last_before(self, ticker, date):
        s = self.series.get(ticker.replace(".", "-"))
        pos = s.index.searchsorted(date, side="right") - 1
        return float(s.iloc[pos]) if pos >= 0 else np.nan


def returns_for(sig, prices, horizon):
    """One row per signal: status and returns for one horizon."""
    rows = []
    cal = prices.cal
    for r in sig.itertuples():
        i = cal.searchsorted(r.signal_date, side="right")        # first trading day after the signal date
        row = {"ticker": r.ticker, "signal_date": r.signal_date, "status": "ok",
               "ret": np.nan, "ret_last": np.nan, "spy": np.nan, "iwm": np.nan}
        if i + horizon >= len(cal):
            row["status"] = "horizon not reached"; rows.append(row); continue
        entry, exitd = cal[i], cal[i + horizon]
        e = prices.at(r.ticker, entry)
        if e is None:
            row["status"] = "no entry price"; rows.append(row); continue
        row["spy"] = prices.at("SPY", exitd)[0] / prices.at("SPY", entry)[0] - 1
        row["iwm"] = prices.at("IWM", exitd)[0] / prices.at("IWM", entry)[0] - 1
        x = prices.at(r.ticker, exitd)
        if x is None:                                            # stopped trading inside the horizon
            row["status"] = "stopped trading"
            row["ret_last"] = prices.last_before(r.ticker, exitd) / e[0] - 1
        else:
            row["ret"] = x[0] / e[0] - 1
            row["ret_last"] = row["ret"]
        rows.append(row)
    return pd.DataFrame(rows)


def summarise(d, scenario, cost=0.0):
    """Stats for one way of treating stocks that stopped trading."""
    d = d[d["status"].isin(["ok", "stopped trading"])].copy()
    if scenario == "dropped":
        d = d[d["status"] == "ok"]; ret = d["ret"]
    elif scenario == "last price":
        ret = d["ret_last"]
    else:                                                        # "-100%"
        ret = d["ret"].where(d["status"] == "ok", -1.0)
    ret = ret - cost
    out = {"n": len(d), "mean": ret.mean(), "median": ret.median()}
    for b in ["spy", "iwm"]:
        ex = ret - d[b]
        out[f"mean ex {b.upper()}"] = ex.mean()
        out[f"median ex {b.upper()}"] = ex.median()
        out[f"beat {b.upper()} %"] = (ex > 0).mean() * 100
    return out


def show(table):
    t = pd.DataFrame(table).T
    for c in t.columns:
        if c == "n":
            t[c] = t[c].astype(int)
        elif c.endswith("%"):
            t[c] = t[c].map(lambda v: f"{v:.0f}%")
        else:
            t[c] = t[c].map(lambda v: f"{v * 100:.1f}%")
    print(t.to_string())


def run_variant(title, sig, prices, horizons):
    print(f"\n=== {title}: {len(sig)} signals ===")
    for name, h in horizons.items():
        d = returns_for(sig, prices, h)
        print(f"\n{name} ({h} trading days). Status counts:", d["status"].value_counts().to_dict())
        table = {s: summarise(d, s) for s in ["dropped", "last price", "-100%"]}
        table["last price, after 1% cost"] = summarise(d, "last price", COST)
        show(table)
    return d


if __name__ == "__main__":
    holdout = "--holdout" in sys.argv
    if holdout and "--confirm-final" not in sys.argv:
        sys.exit("The 2025 held-out set is locked. Use it once, at the very end, with: "
                 "python src/backtest.py --holdout --confirm-final")
    sig = pd.read_csv(SIGNALS, parse_dates=["signal_date"])
    px = pd.read_csv(PRICES, index_col=0, parse_dates=True)
    for b in ["SPY", "IWM"]:
        if b not in px.columns or px[b].notna().sum() == 0:
            sys.exit(f"No prices for {b} in {PRICES}")
    prices = Prices(px)

    sig = sig[sig["signal_date"] >= SPLIT_DATE] if holdout else sig[sig["signal_date"] < SPLIT_DATE]
    print("HELD-OUT 2025 SET" if holdout else "MAIN TEST (signals before 2025)")
    v1 = sig[sig["rule"] == "v1"].sort_values("signal_date")
    v2 = sig[sig["rule"] == "v2"].sort_values("signal_date")

    run_variant("v1, all signals", v1, prices, HORIZONS)
    only = {PRIMARY: HORIZONS[PRIMARY]}
    run_variant("v1, first signal per company only", v1.drop_duplicates("ISSUERCIK"), prices, only)
    run_variant("v2 (2+ trade dates)", v2, prices, only)
    run_variant("v1 signals with all purchases on one trade date", v1[v1["trade_dates"] == 1], prices, only)
    run_variant("v1 signals with purchases on 2+ trade dates", v1[v1["trade_dates"] >= 2], prices, only)
