"""Check the live fetcher against the SEC's own quarterly data set, for one day we have both.

Run from the project folder, after fetching that day with live_form4.py:
    python src/check_live.py 2026-09-15

It compares the purchases (code P, original Form 4) the fetcher found with the ones in
data/2026q3_form345 for the same filing day, and lists any that differ.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")
from clean import load_purchases            # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python src/check_live.py 2026-09-15")
    day = pd.Timestamp(sys.argv[1])
    live = pd.read_csv(Path("data/live") / f"purchases_{day:%Y%m%d}.csv", dtype={"ISSUERCIK": str})
    ref = load_purchases(Path("data/2026q3_form345"))
    ref = ref[(ref["filing_date"] == day) & (ref["DOCUMENT_TYPE"] == "4")]

    def keys(df, acc, sh, px, who):
        return pd.Series(list(zip(df[acc], df[who].astype(str).str.lstrip("0"),
                                  df[sh].round(0))))
    a = keys(live, "ACCESSION_NUMBER", "shares", "price", "RPTOWNERCIK")
    b = keys(ref, "ACCESSION_NUMBER", "shares", "price", "RPTOWNERCIK")
    ca, cb = a.value_counts(), b.value_counts()
    only_live = (ca.sub(cb, fill_value=0)).loc[lambda s: s > 0]
    only_ref = (cb.sub(ca, fill_value=0)).loc[lambda s: s > 0]
    print(f"day {day.date()}: live fetcher {len(a)} purchase rows | SEC data set {len(b)} rows (matched on filing, insider and shares)")
    print("rows only in live fetcher:", int(only_live.sum()))
    for k in list(only_live.index)[:10]:
        print("   ", k)
    print("rows only in SEC data set:", int(only_ref.sum()))
    for k in list(only_ref.index)[:10]:
        print("   ", k)
    # prices: the SEC rounds to 2 decimals, we keep the exact figure, so allow a rounding gap
    m = live.assign(k=a.values).sort_values(["k", "price"]).reset_index(drop=True)
    r = ref.assign(k=b.values).sort_values(["k", "price"]).reset_index(drop=True)
    if len(m) == len(r) and (m["k"] == r["k"]).all():
        gap = (m["price"] - r["price"]).abs().max()
        print(f"largest price gap on matched rows: {gap:.4f}  (rounding only if under 0.01)")
    print("MATCH" if len(only_live) == 0 and len(only_ref) == 0 else "DIFFERENCES FOUND - tell Claude")
