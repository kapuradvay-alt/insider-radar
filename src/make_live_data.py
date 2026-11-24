"""Stage 2: build the app's signal list from the SEC Q3 file plus the live daily downloads.

Run from the project folder, after live_form4.py has saved the days you want:
    python src/make_live_data.py

Steps (all rules are the same as for the historical data, see docs/cluster_rule.md):
  1. read the cleaned Q3 2026 file (filings 1 Jul - 30 Sep 2026, from the SEC quarterly data set;
     data/people_2026q3_slim.csv = data/people_2026q3_form345.csv without the address columns),
  2. read data/live/purchases_*.csv for filings from 1 Oct 2026 on,
  3. clean the live rows with the same rules (ticker, price, filing lag, original Form 4,
     price within 0.5x-2x of Yahoo's close),
  4. find clusters (3+ officers/directors, $10,000 each, 14 days) with the 90-day cooldown,
  5. write app_data/signals_latest.csv and app_data/meta.json.
No stock returns are used. Optional: --prices-file FILE uses a ready price file (for testing).
"""
import json
import sys
import warnings
from datetime import date
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from clean import TRADE_KEY, apply_rules, download_prices, price_check   # noqa: E402
from clusters import find_clusters                                      # noqa: E402
from cluster_check import cluster_details                               # noqa: E402
from make_signals import add_ticker                                     # noqa: E402

Q3_FILE = Path("data/people_2026q3_slim.csv")      # the cleaned Q3 file without street addresses
MIN_COVERAGE = 0.85
LIVE_FROM = pd.Timestamp("2026-10-01")          # the SEC Q3 file already covers everything before this
KEEP = ["ACCESSION_NUMBER", "ISSUERCIK", "ISSUERNAME", "ISSUERTRADINGSYMBOL", "RPTOWNERCIK",
        "RPTOWNERNAME", "trans_date", "filing_date", "shares", "price", "value", "is_exec",
        "price_check"]


def read_live():
    files = sorted(Path("data/live").glob("purchases_*.csv"))
    parts = [pd.read_csv(f, dtype={"ISSUERCIK": str, "RPTOWNERCIK": str, "DOCUMENT_TYPE": str}) for f in files]
    d = pd.concat(parts, ignore_index=True)
    d["trans_date"] = pd.to_datetime(d["trans_date"], errors="coerce")
    d["filing_date"] = pd.to_datetime(d["filing_date"], errors="coerce")
    d["is_exec"] = d["is_exec"].astype(str) == "True"
    d = d[d["filing_date"] >= LIVE_FROM]
    return d, len(files)


def main(prices_file=None):
    q3 = pd.read_csv(Q3_FILE, parse_dates=["trans_date", "filing_date"],
                     dtype={"ISSUERCIK": str, "RPTOWNERCIK": str}, low_memory=False)
    live, n_days = read_live()
    print(f"Q3 file: {len(q3):,} cleaned owner rows | live: {len(live):,} raw purchase rows "
          f"from {live['filing_date'].nunique()} filing days")

    trades, funnel = apply_rules(live)
    print(funnel.to_string(index=False))
    if prices_file:
        prices = pd.read_csv(prices_file, index_col=0, parse_dates=True)
    else:
        cache = Path("data/prices_live.csv")
        if cache.exists():
            cache.unlink()                           # always fresh: prices change every day
        prices = download_prices(trades["ISSUERTRADINGSYMBOL"].unique(),
                                 trades["trans_date"].min() - pd.Timedelta(days=5),
                                 trades["trans_date"].max() + pd.Timedelta(days=5), cache)
    # Safety guard: Yahoo sometimes returns nothing without an error. If too few tickers have prices,
    # stop BEFORE writing anything, so a bad Yahoo day cannot silently shrink the signal list.
    wanted = {t.replace(".", "-") for t in trades["ISSUERTRADINGSYMBOL"].str.upper().str.strip()}
    have = set(prices.columns[prices.notna().any()])
    coverage = len(wanted & have) / max(len(wanted), 1)
    print(f"price coverage: {len(wanted & have)} of {len(wanted)} tickers ({coverage:.0%})")
    if coverage < MIN_COVERAGE:
        sys.exit(f"STOPPED: only {coverage:.0%} of tickers have Yahoo prices (need {MIN_COVERAGE:.0%}). "
                 "Nothing was changed. Try again later.")
    final = price_check(trades, prices)
    print(f"after price check (0.5x-2x of Yahoo close): {len(final):,} trades")
    people_live = live.merge(final[TRADE_KEY + ["price_check"]], on=TRADE_KEY, how="inner")

    people = pd.concat([q3[KEEP], people_live[KEEP]], ignore_index=True)
    sig = find_clusters(people, 3, 14, 10000, cooldown=90)
    det = cluster_details(people, sig)
    det = add_ticker(det.assign(signal_date=pd.to_datetime(det["signal_date"])), people)
    names = people.sort_values("filing_date").drop_duplicates("ISSUERCIK", keep="last") \
                  .set_index("ISSUERCIK")["ISSUERNAME"]
    det["company"] = det["ISSUERCIK"].map(names)
    det["edgar_link"] = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK="
                         + det["ISSUERCIK"] + "&type=4&dateb=&owner=include&count=40")
    cols = ["ticker", "company", "signal_date", "insiders", "trade_dates", "price_spread",
            "total_value", "edgar_link"]
    det = det[cols].sort_values("signal_date", ascending=False)
    det.to_csv("app_data/signals_latest.csv", index=False)

    last_live = live["filing_date"].max()
    meta = {"source": "SEC quarterly file (1 Jul-30 Sep 2026) plus SEC daily filings (from 1 Oct 2026)",
            "filings_from": str(q3["filing_date"].min().date()),
            "filings_to": str(last_live.date()),
            "built_on": str(date.today()),
            "signals": len(det),
            "new_since_oct": int((det["signal_date"] >= LIVE_FROM).sum())}
    json.dump(meta, open("app_data/meta.json", "w"), indent=2)
    print(meta)
    print("\nNewest 10 signals:")
    print(det.head(10)[["ticker", "company", "signal_date", "insiders", "trade_dates",
                        "total_value"]].to_string(index=False))


if __name__ == "__main__":
    pf = sys.argv[sys.argv.index("--prices-file") + 1] if "--prices-file" in sys.argv else None
    main(pf)
