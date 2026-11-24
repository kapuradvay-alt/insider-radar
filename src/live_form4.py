"""Stage 2: fetch fresh Form 4 purchases straight from the SEC, one filing day at a time.

Run from the project folder (your email is sent to the SEC, as they ask):
    python src/live_form4.py you@example.com 2026-10-01 2026-11-20

What it does, for each weekday in the range:
  1. downloads the SEC's list of that day's filings (the "daily index"),
  2. opens every Form 4 on the list (about 500 a day), slowly (4 requests a second),
  3. keeps only the open-market purchases (transaction code P),
  4. saves them to data/live/purchases_YYYYMMDD.csv.

A day that already has a file is skipped, so you can stop with Ctrl+C and run the same
command again: it carries on where it stopped. Only original Form 4s are read (not 4/A
amendments), the same as the historical data (docs/cluster_rule.md).
"""
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

OUT = Path("data/live")
BASE = "https://www.sec.gov/Archives/"
PAUSE = 0.25            # 4 requests a second, well under the SEC limit of 10
TRUE = {"1", "true", "TRUE", "True"}

COLUMNS = ["ACCESSION_NUMBER", "NONDERIV_TRANS_SK", "RPTOWNERCIK", "RPTOWNERNAME",
           "RPTOWNER_RELATIONSHIP", "ISSUERCIK", "ISSUERNAME", "ISSUERTRADINGSYMBOL",
           "DOCUMENT_TYPE", "TRANS_CODE", "trans_date", "filing_date",
           "shares", "price", "value", "is_exec"]


def _text(node, path):
    """Text of the first element at `path` under `node`, or None."""
    found = node.find(path) if node is not None else None
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


def _number(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return float("nan")


def parse_filing(raw):
    """Turn one SEC filing (the full .txt) into a list of purchase rows (code P only).

    Returns (rows, status). status is "ok", "no xml" or "bad xml".
    Every insider named in the filing gets one row per purchase, like the SEC data sets.
    """
    acc = re.search(r"ACCESSION NUMBER:\s*(\S+)", raw)
    filed = re.search(r"FILED AS OF DATE:\s*(\d{8})", raw)
    start, end = raw.find("<ownershipDocument"), raw.find("</ownershipDocument>")
    if not acc or not filed or start < 0 or end < 0:
        return [], "no xml"
    xml = raw[start:end + len("</ownershipDocument>")]
    if "<!DOCTYPE" in xml or "<!ENTITY" in xml:       # the SEC never sends these; refuse them
        return [], "bad xml"
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return [], "bad xml"

    doc_type = _text(root, "documentType")
    issuer = root.find("issuer")
    issuer_cik = _text(issuer, "issuerCik")
    issuer_name = _text(issuer, "issuerName")
    ticker = _text(issuer, "issuerTradingSymbol")

    owners = []
    for o in root.findall("reportingOwner"):
        rel = o.find("reportingOwnerRelationship")
        labels = []
        for tag, label in [("isDirector", "Director"), ("isOfficer", "Officer"),
                           ("isTenPercentOwner", "TenPercentOwner"), ("isOther", "Other")]:
            if _text(rel, tag) in TRUE:
                labels.append(label)
        owners.append((_text(o, "reportingOwnerId/rptOwnerCik"),
                       _text(o, "reportingOwnerId/rptOwnerName"), ",".join(labels)))

    rows = []
    table = root.find("nonDerivativeTable")
    trades = table.findall("nonDerivativeTransaction") if table is not None else []
    for seq, t in enumerate(trades, start=1):
        if _text(t, "transactionCoding/transactionCode") != "P":
            continue
        shares = _number(_text(t, "transactionAmounts/transactionShares/value"))
        price = _number(_text(t, "transactionAmounts/transactionPricePerShare/value"))
        for cik, name, rel in owners:
            rows.append({
                "ACCESSION_NUMBER": acc.group(1), "NONDERIV_TRANS_SK": seq,
                "RPTOWNERCIK": cik, "RPTOWNERNAME": name, "RPTOWNER_RELATIONSHIP": rel,
                "ISSUERCIK": issuer_cik, "ISSUERNAME": issuer_name,
                "ISSUERTRADINGSYMBOL": ticker, "DOCUMENT_TYPE": doc_type,
                "TRANS_CODE": "P",
                "trans_date": _text(t, "transactionDate/value"),
                "filing_date": f"{filed.group(1)[:4]}-{filed.group(1)[4:6]}-{filed.group(1)[6:]}",
                "shares": shares, "price": price, "value": shares * price,
                "is_exec": ("Officer" in rel) or ("Director" in rel),
            })
    return rows, "ok"


# ---- talking to the SEC ---------------------------------------------------------------

def get(session, url, tries=3):
    """Download with a pause and a few retries. Returns the response (any status)."""
    r = None
    for attempt in range(tries):
        try:
            r = session.get(url, timeout=60)
        except Exception:
            r = None
        time.sleep(PAUSE * (attempt + 1))
        if r is not None and r.status_code not in (429, 500, 502, 503, 504):
            return r
        time.sleep(5 * (attempt + 1))
    return r


def day_filings(session, day):
    """Form 4 filings listed in the SEC daily index for `day`: {accession file name: [addresses]}.

    The same filing is listed under the company and under each insider, with different
    addresses but the same accession number (the file name). We read it once, but keep all
    its addresses in case the first one does not work. (None, status) if there is no index.
    """
    q = (day.month - 1) // 3 + 1
    url = f"{BASE}edgar/daily-index/{day.year}/QTR{q}/form.{day:%Y%m%d}.idx"
    r = get(session, url)
    if r is None or r.status_code != 200:
        return None, (r.status_code if r is not None else "no answer")
    files = {}
    for ln in r.text.splitlines():
        parts = ln.split()
        if len(parts) >= 5 and parts[0] == "4" and parts[-1].startswith("edgar/data/"):
            paths = files.setdefault(parts[-1].split("/")[-1], [])
            if parts[-1] not in paths:
                paths.append(parts[-1])
    return files, 200


def get_filing(session, paths):
    """Try each address of one filing until one works. Returns (response or None, last status)."""
    status = "no answer"
    for path in paths:
        r = get(session, BASE + path)
        if r is not None and r.status_code == 200:
            return r, 200
        status = r.status_code if r is not None else "no answer"
    return None, status


def fetch_day(session, day):
    """Returns ((DataFrame of purchases, filings opened, failed, unreadable), 200), or (None, status)."""
    files, status = day_filings(session, day)
    if files is None:
        return None, status
    rows, failed, bad = [], [], 0
    for i, (acc, paths) in enumerate(files.items(), start=1):
        r, st = get_filing(session, paths)
        if r is None:
            failed.append((paths[0], st))
            continue
        got, st = parse_filing(r.text)
        if st != "ok":
            bad += 1
        rows.extend(got)
        if i % 100 == 0:
            print(f"    {i} of {len(files)} filings read", flush=True)
    df = pd.DataFrame(rows, columns=COLUMNS)
    df = df.drop_duplicates(["ACCESSION_NUMBER", "NONDERIV_TRANS_SK", "RPTOWNERCIK"])
    return (df, len(files), failed, bad), 200


def main(email, first, last):
    import requests
    session = requests.Session()
    session.headers["User-Agent"] = f"insider-radar student project {email}"
    OUT.mkdir(parents=True, exist_ok=True)
    today = date.today()

    day, todo = first, []
    while day <= last:
        if day.weekday() < 5 and not (OUT / f"purchases_{day:%Y%m%d}.csv").exists():
            todo.append(day)
        day += timedelta(days=1)
    print(f"{len(todo)} weekdays to fetch (already done days are skipped)")

    problems = []
    for n, day in enumerate(todo, start=1):
        print(f"[{n}/{len(todo)}] {day} ...", flush=True)
        if day >= today:
            print("    today's list is not published yet (the SEC posts it in the evening, US time); skipped")
            continue
        res, status = fetch_day(session, day)
        if res is None:
            if (today - day).days >= 4:           # old weekday with no list = a market holiday
                pd.DataFrame(columns=COLUMNS).to_csv(OUT / f"purchases_{day:%Y%m%d}.csv", index=False)
                print(f"    no list from the SEC (status {status}); treated as a holiday")
            else:
                print(f"    no list yet (status {status}); will retry next run")
                problems.append((day, f"no list, status {status}"))
            continue
        df, n_files, failed, bad = res
        for f, st in failed:
            print(f"    could not download {BASE}{f} (status {st})")
        # 403/404/410 = the SEC lists the file but will not serve it. Retrying cannot help, so we
        # save the day, write the filing to skipped.txt, and look at it by hand afterwards.
        permanent = {403, 404, 410}
        if failed and not all(st in permanent for _, st in failed):
            print(f"    {len(failed)} of {n_files} filings failed (temporary problem); day NOT saved, rerun later")
            problems.append((day, f"{len(failed)} failed downloads"))
            continue
        with open(OUT / "skipped.txt", "a") as fh:
            for f, st in failed:
                fh.write(f"{day}\t{st}\t{BASE}{f}\n")
        df.to_csv(OUT / f"purchases_{day:%Y%m%d}.csv", index=False)
        with open(OUT / "log.txt", "a") as fh:
            fh.write(f"{day}\tfilings={n_files}\tunreadable={bad}\tskipped={len(failed)}\tpurchase_rows={len(df)}\n")
        print(f"    {n_files} filings, {len(df)} purchase rows saved, {bad} unreadable")

    print("\nDone." if not problems else "\nFinished, but these days need another run:")
    for d, why in problems:
        print("  ", d, why)


if __name__ == "__main__":
    if len(sys.argv) != 4 or "@" not in sys.argv[1]:
        sys.exit("Usage: python src/live_form4.py you@example.com 2026-10-01 2026-11-20")
    main(sys.argv[1],
         datetime.strptime(sys.argv[2], "%Y-%m-%d").date(),
         datetime.strptime(sys.argv[3], "%Y-%m-%d").date())
