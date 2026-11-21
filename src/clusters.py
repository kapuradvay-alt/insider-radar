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
                       dtype={"ISSUERCIK": str, "RPTOWNERCIK": str})


def find_clusters(people, n, window, min_value):
    """Companies with at least n different executives buying within `window` days.

    Counts by filing date. Each insider's purchases filed on the same day are added
    together and must reach min_value. Returns one row per company: the signal date
    is the first filing date on which the cluster is complete.
    """
    x = people[people["is_exec"]]
    g = x.groupby(["ISSUERCIK", "RPTOWNERCIK", "filing_date"], as_index=False)["value"].sum()
    g = g[g["value"] >= min_value]
    out = []
    for cik, grp in g.groupby("ISSUERCIK"):
        grp = grp.sort_values("filing_date")
        dates = grp["filing_date"].values
        owners = grp["RPTOWNERCIK"].values
        for i in range(len(grp)):
            end = dates[i]
            start = end - np.timedelta64(window, "D")
            mask = (dates <= end) & (dates > start)
            if len(set(owners[mask])) >= n:
                out.append({"ISSUERCIK": cik, "signal_date": pd.Timestamp(end),
                            "insiders": len(set(owners[mask]))})
                break
    return pd.DataFrame(out, columns=["ISSUERCIK", "signal_date", "insiders"])


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
