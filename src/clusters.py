"""Count insider clusters under different rules (no stock returns are used).

Run from the project folder:
    python src/clusters.py data/people_2026q3_form345.csv

The agreed rule is in docs/cluster_rule.md (3 insiders, $10,000 each, 14 days).
This script also shows nearby settings, so we can see how many clusters each rule finds.
"""
import sys

import numpy as np
import pandas as pd


def load_people(path):
    return pd.read_csv(path, parse_dates=["trans_date", "filing_date"],
                       dtype={"ISSUERCIK": str, "RPTOWNERCIK": str}, low_memory=False)


def find_clusters(people, n, window, min_value, cooldown=None, min_trade_dates=1):
    """Companies with at least n different executives buying within `window` days.

    Counts by filing date. Each insider's purchases filed on the same day are added
    together and must reach min_value.

    cooldown=None: one row per company, the first signal only (one file = one quarter).
    cooldown=90: a company can signal again, but not within 90 days of its last signal.
    min_trade_dates=2: the purchases in the cluster must fall on at least 2 different
    trade dates (rule v2 in docs/cluster_rule_v2.md).

    The signal date is the first filing date on which the cluster is complete.
    """
    x = people[people["is_exec"]]
    g = (x.groupby(["ISSUERCIK", "RPTOWNERCIK", "filing_date"])
          .agg(value=("value", "sum"),
               tdates=("trans_date", lambda s: frozenset(s.dropna())))
          .reset_index())
    g = g[g["value"] >= min_value]
    out = []
    for cik, grp in g.groupby("ISSUERCIK"):
        grp = grp.sort_values("filing_date")
        dates = grp["filing_date"].values
        owners = grp["RPTOWNERCIK"].values
        tdates = grp["tdates"].values
        last = None
        for i in range(len(grp)):
            end = dates[i]
            if last is not None and end < last + np.timedelta64(cooldown, "D"):
                continue
            start = end - np.timedelta64(window, "D")
            mask = (dates <= end) & (dates > start)
            insiders = len(set(owners[mask]))
            trade_dates = len(set().union(*tdates[mask]))
            if insiders >= n and trade_dates >= min_trade_dates:
                out.append({"ISSUERCIK": cik, "signal_date": pd.Timestamp(end),
                            "insiders": insiders, "trade_dates": trade_dates})
                if cooldown is None:
                    break
                last = end
    return pd.DataFrame(out, columns=["ISSUERCIK", "signal_date", "insiders", "trade_dates"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python src/clusters.py data/people_2026q3_form345.csv")
    people = load_people(sys.argv[1])

    rows = []
    for mv in [0, 10000]:
        for w in [7, 14, 30]:
            for n in [2, 3, 4]:
                rows.append((mv, w, n, len(find_clusters(people, n, w, mv))))
    res = pd.DataFrame(rows, columns=["min_value", "window_days", "insiders", "clusters"])
    print("Companies with a cluster (columns = number of insiders required):")
    print(res.pivot_table(index=["min_value", "window_days"], columns="insiders", values="clusters"))

    agreed = find_clusters(people, 3, 14, 10000)
    print("\nAgreed rule (3 insiders, 14 days, $10,000):", len(agreed), "clusters")
    names = people.drop_duplicates("ISSUERCIK").set_index("ISSUERCIK")[["ISSUERTRADINGSYMBOL", "ISSUERNAME"]]
    print(agreed.join(names, on="ISSUERCIK").sort_values("signal_date").to_string(index=False))
