"""Clean one quarter of SEC insider data (Form 3/4/5 data sets).

Run from the project folder:
    python src/clean.py data/2026q3_form345

What it does, in order (the same rules as the 01_explore notebook):
  1. keep open-market purchases (transaction code P)
  2. keep one row per transaction (a trade filed by two insiders counts once for money)
  3. drop rows with no real ticker, no price, or no shares
  4. drop trades filed more than MAX_LAG_DAYS after the trade date
  5. drop amended filings (Form 4/A)
  6. compare the reported price with the market close; keep only rows within 0.5x to 2x
Results are saved next to the input folder as CSV files.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

MAX_LAG_DAYS = 10
RATIO_MIN, RATIO_MAX = 0.5, 2.0       # reported price vs market close
CLOSE_LOW, CLOSE_HIGH = 0.9, 1.1      # "close" = within 10% of market
TRADE_KEY = ["ACCESSION_NUMBER", "NONDERIV_TRANS_SK"]


def read_table(folder, name):
    """Read one tab-separated table as plain text (no guessing of types)."""
    return pd.read_csv(Path(folder) / f"{name}.tsv", sep="\t", dtype=str)


def load_purchases(folder):
    """Purchases joined to insider and company info. One row per insider per trade."""
    sub = read_table(folder, "SUBMISSION")
    own = read_table(folder, "REPORTINGOWNER")
    trans = read_table(folder, "NONDERIV_TRANS")

    buys = trans[trans["TRANS_CODE"] == "P"]
    cols = ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE",
            "ISSUERCIK", "ISSUERNAME", "ISSUERTRADINGSYMBOL"]
    d = buys.merge(own, on="ACCESSION_NUMBER", how="left")
    d = d.merge(sub[cols], on="ACCESSION_NUMBER", how="left")

    d["trans_date"] = pd.to_datetime(d["TRANS_DATE"], format="%d-%b-%Y", errors="coerce")
    d["filing_date"] = pd.to_datetime(d["FILING_DATE"], format="%d-%b-%Y", errors="coerce")
    d["shares"] = pd.to_numeric(d["TRANS_SHARES"], errors="coerce")
    d["price"] = pd.to_numeric(d["TRANS_PRICEPERSHARE"], errors="coerce")
    d["value"] = d["shares"] * d["price"]
    d["is_exec"] = d["RPTOWNER_RELATIONSHIP"].str.contains("Officer|Director", na=False)
    return d


def apply_rules(d):
    """Rules 2 to 5. Returns one row per transaction, plus a table of rows left at each step."""
    step = d.drop_duplicates(TRADE_KEY)
    log = [("purchases (code P, one row per trade)", len(step))]

    tick = step["ISSUERTRADINGSYMBOL"].str.upper().str.strip()
    real = tick.notna() & tick.str.fullmatch(r"[A-Z][A-Z.\-]*", na=False) & (tick != "NONE")
    step = step[real]
    log.append(("has a real ticker", len(step)))

    step = step[step["price"].notna() & (step["shares"] > 0)]
    log.append(("has price and shares above 0", len(step)))

    lag = (step["filing_date"] - step["trans_date"]).dt.days
    step = step[(lag >= 0) & (lag <= MAX_LAG_DAYS)]    # a trade dated after its filing is impossible
    log.append((f"filed within {MAX_LAG_DAYS} days of the trade", len(step)))

    step = step[step["DOCUMENT_TYPE"] == "4"]
    log.append(("original Form 4 only (no amendments)", len(step)))
    return step.copy(), pd.DataFrame(log, columns=["step", "rows left"])


def _download(batch, start, end, auto_adjust=False):
    import yfinance as yf
    df = yf.download(batch, start=start, end=end, auto_adjust=auto_adjust, progress=False)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(batch[0])
    return df


def download_prices(tickers, start, end, cache_file):
    """Daily closing prices from Yahoo, saved to cache_file so we never download twice.

    Yahoo sometimes returns nothing for a ticker without raising an error (for example
    when it is busy). Tickers that come back empty are retried in smaller batches.
    """
    cache_file = Path(cache_file)
    if cache_file.exists():
        prices = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        return prices

    names = sorted({t.replace(".", "-") for t in tickers})   # Yahoo writes BRK.B as BRK-B
    frames = []
    for i in range(0, len(names), 100):
        try:
            frames.append(_download(names[i:i + 100], start, end))
        except Exception as e:
            print("batch failed at", i, e)
        time.sleep(2)
    prices = pd.concat(frames, axis=1)
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    prices = prices.loc[:, ~prices.columns.duplicated()]

    for attempt in range(2):
        have = set(prices.columns[prices.notna().any()])
        missing = [n for n in names if n not in have]
        if not missing:
            break
        print(f"retry {attempt + 1}: {len(missing)} tickers had no prices")
        time.sleep(10)
        extra = []
        for i in range(0, len(missing), 25):
            try:
                extra.append(_download(missing[i:i + 25], start, end))
            except Exception as e:
                print("retry batch failed at", i, e)
            time.sleep(3)
        if extra:
            new = pd.concat(extra, axis=1)
            new.index = pd.to_datetime(new.index).tz_localize(None)
            new = new.loc[:, ~new.columns.duplicated()]
            prices = prices.combine_first(new)

    have = prices.columns[prices.notna().any()]
    print(f"price coverage: {len(have)} of {len(names)} tickers have Yahoo prices")
    prices.to_csv(cache_file)
    return prices


def price_check(trades, prices):
    """Rule 6. Adds market close, ratio and a close/loose label; keeps rows within the ratio band."""
    px = prices.sort_index()
    px = px.loc[:, ~px.columns.duplicated()]

    def mkt_close(t, date):
        col = t.replace(".", "-")
        if col not in px.columns:
            return np.nan
        s = px[col].dropna()
        s = s[s.index <= date]
        return float(s.iloc[-1]) if len(s) else np.nan

    out = trades.copy()
    out["mkt"] = [mkt_close(t, dt) for t, dt in zip(out["ISSUERTRADINGSYMBOL"], out["trans_date"])]
    out["ratio"] = out["price"] / out["mkt"]
    keep = out["mkt"].notna() & (out["ratio"] >= RATIO_MIN) & (out["ratio"] <= RATIO_MAX)
    out = out[keep].copy()
    close = (out["ratio"] > CLOSE_LOW) & (out["ratio"] < CLOSE_HIGH)
    out["price_check"] = np.where(close, "close", "loose")
    return out


def clean_quarter(folder, prices=None):
    """Full pipeline for one quarter folder. Returns (transactions, people, funnel)."""
    folder = Path(folder)
    d = load_purchases(folder)
    trades, funnel = apply_rules(d)

    if prices is None:
        start = trades["trans_date"].min() - pd.Timedelta(days=5)
        end = trades["trans_date"].max() + pd.Timedelta(days=5)
        prices = download_prices(trades["ISSUERTRADINGSYMBOL"].unique(), start, end,
                                 folder.parent / f"prices_{folder.name}.csv")

    final = price_check(trades, prices)
    funnel.loc[len(funnel)] = ["market price within 0.5x to 2x", len(final)]

    people = d.merge(final[TRADE_KEY + ["price_check"]], on=TRADE_KEY, how="inner")
    return final, people, funnel


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python src/clean.py data/2026q3_form345")
    folder = Path(sys.argv[1])
    final, people, funnel = clean_quarter(folder)
    print(funnel.to_string(index=False))
    print("owner-level rows:", len(people))
    final.to_csv(folder.parent / f"purchases_{folder.name}.csv", index=False)
    people.to_csv(folder.parent / f"people_{folder.name}.csv", index=False)
    print("saved to", folder.parent)
