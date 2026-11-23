"""Build the small data file the Streamlit app shows (signals found in the latest SEC quarter).

Run from the project folder:
    python src/make_app_data.py data/people_2026q3_form345.csv

Output (small, safe to commit): app_data/signals_latest.csv and app_data/meta.json.
Rule: v1 with the 90-day cooldown (docs/cluster_rule.md, docs/cooldown_and_period.md).
No returns are used.
"""
import json
import sys
import warnings
from datetime import date

import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from clusters import load_people, find_clusters        # noqa: E402
from cluster_check import cluster_details              # noqa: E402
from make_signals import add_ticker                    # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python src/make_app_data.py data/people_2026q3_form345.csv")
    people = load_people(sys.argv[1])
    sig = find_clusters(people, 3, 14, 10000, cooldown=90)
    det = cluster_details(people, sig)
    det = add_ticker(det.assign(signal_date=pd.to_datetime(det["signal_date"])), people)
    names = people.drop_duplicates("ISSUERCIK").set_index("ISSUERCIK")["ISSUERNAME"]
    det["company"] = det["ISSUERCIK"].map(names)
    det["edgar_link"] = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK="
                         + det["ISSUERCIK"] + "&type=4&dateb=&owner=include&count=40")
    cols = ["ticker", "company", "signal_date", "insiders", "trade_dates", "price_spread",
            "total_value", "edgar_link"]
    det = det[cols].sort_values("signal_date", ascending=False)
    det.to_csv("app_data/signals_latest.csv", index=False)
    meta = {"source": sys.argv[1].split("/")[-1],
            "filings_from": str(people["filing_date"].min().date()),
            "filings_to": str(people["filing_date"].max().date()),
            "built_on": str(date.today()),
            "signals": len(det)}
    json.dump(meta, open("app_data/meta.json", "w"), indent=2)
    print(meta)
