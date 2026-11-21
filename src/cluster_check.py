"""Quality check on clusters (no stock returns are used).

Run from the project folder:
    python src/cluster_check.py data/people_2026q3_form345.csv

For each cluster under the agreed rule it shows how many different trade dates the
purchases fell on and how far apart the prices were. A cluster where everyone bought
on one date at one price may be an offering or a plan, not independent buying.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from clusters import load_people, find_clusters   # noqa: E402

N, WINDOW, MIN_VALUE = 3, 14, 10000


def cluster_details(people, clusters):
    x = people[people["is_exec"]].copy()
    day = x.groupby(["ISSUERCIK", "RPTOWNERCIK", "filing_date"])["value"].transform("sum")
    x = x[day >= MIN_VALUE]

    rows = []
    for _, c in clusters.iterrows():
        end = c["signal_date"]
        start = end - pd.Timedelta(days=WINDOW)
        w = x[(x["ISSUERCIK"] == c["ISSUERCIK"]) & (x["filing_date"] <= end) & (x["filing_date"] > start)]
        rows.append({
            "ISSUERCIK": c["ISSUERCIK"],
            "signal_date": end.date(),
            "insiders": w["RPTOWNERCIK"].nunique(),
            "trade_dates": w["trans_date"].nunique(),
            "price_spread": round(w["price"].max() / w["price"].min(), 3),
            "total_value": round(w["value"].sum()),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python src/cluster_check.py data/people_2026q3_form345.csv")
    people = load_people(sys.argv[1])
    clusters = find_clusters(people, N, WINDOW, MIN_VALUE)
    det = cluster_details(people, clusters)
    names = people.drop_duplicates("ISSUERCIK").set_index("ISSUERCIK")["ISSUERTRADINGSYMBOL"]
    det = det.join(names.rename("ticker"), on="ISSUERCIK")

    one_day = det["trade_dates"] == 1
    tight = det["price_spread"] <= 1.02
    print("clusters:", len(det))
    print("all purchases on ONE trade date:", int(one_day.sum()))
    print("all purchases on one date AND within 2% in price:", int((one_day & tight).sum()))
    print("spread over 3 or more trade dates:", int((det["trade_dates"] >= 3).sum()))
    print("\nBiggest by insiders:")
    cols = ["ticker", "signal_date", "insiders", "trade_dates", "price_spread", "total_value"]
    print(det.sort_values("insiders", ascending=False)[cols].head(12).to_string(index=False))
