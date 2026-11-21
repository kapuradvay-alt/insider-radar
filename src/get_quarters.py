"""Download, unzip and clean several SEC insider-transaction quarters, then merge them.

Run from the project folder (your email goes in the command, it is not saved anywhere):
    python src/get_quarters.py you@example.com 2022 2025

Add --redo-low at the end to redo the price download and cleaning for any quarter where
Yahoo gave prices for under 80% of the tickers (the zip and unzipped files are kept):
    python src/get_quarters.py you@example.com 2022 2025 --redo-low

Add --redo-all instead to redo every quarter in the range with the current cleaning code,
so that all quarters are made with exactly the same rules.

The SEC asks anyone who downloads automatically to say who they are, so the email is
sent in the request header. Files that already exist are skipped, so it is safe to run
again if it stops half way.

Output for each quarter (same as src/clean.py): data/purchases_<quarter>.csv and
data/people_<quarter>.csv, plus data/funnel_<quarter>.txt with the cleaning funnel.
At the end: data/people_<first year>_<last year>.csv with all the quarters together.
"""
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

DATA = Path("data")
URLS = [
    "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{name}.zip",
    "https://www.sec.gov/files/datastandardsinnovation/data/insider-transactions-data-sets/{name}.zip",
]


def download(name, email):
    zip_path = DATA / f"{name}.zip"
    if zip_path.exists() and zip_path.stat().st_size > 0:
        return True
    headers = {"User-Agent": f"insider-radar student project {email}"}
    for url in URLS:
        r = requests.get(url.format(name=name), headers=headers, timeout=120)
        time.sleep(1)                       # stay far below the SEC limit of 10 requests a second
        if r.status_code == 200 and r.content[:2] == b"PK":
            zip_path.write_bytes(r.content)
            return True
        print(f"  not found at {url.format(name=name)} (status {r.status_code})")
    return False


def unzip(name):
    folder = DATA / name
    if (folder / "SUBMISSION.tsv").exists():
        return True
    with zipfile.ZipFile(DATA / f"{name}.zip") as z:
        z.extractall(folder)
    return (folder / "SUBMISSION.tsv").exists()


def clean(name):
    if (DATA / f"people_{name}.csv").exists():
        return True
    res = subprocess.run([sys.executable, "src/clean.py", str(DATA / name)],
                         capture_output=True, text=True)
    (DATA / f"funnel_{name}.txt").write_text(res.stdout)
    if res.returncode != 0:
        print(res.stderr[-1500:])
    return res.returncode == 0


def price_coverage(name):
    """Share of tickers that have Yahoo prices in the saved price file (None if no file)."""
    f = DATA / f"prices_{name}.csv"
    if not f.exists():
        return None
    px = pd.read_csv(f, index_col=0)
    return float(px.notna().any().mean())


def redo(name):
    """Delete the cleaning and price outputs of one quarter so they are made again."""
    for f in [f"purchases_{name}.csv", f"people_{name}.csv", f"funnel_{name}.txt", f"prices_{name}.csv"]:
        (DATA / f).unlink(missing_ok=True)


def merge(names, out_path):
    parts = [pd.read_csv(DATA / f"people_{n}.csv", parse_dates=["trans_date", "filing_date"],
                         dtype={"ISSUERCIK": str, "RPTOWNERCIK": str})
             for n in names if (DATA / f"people_{n}.csv").exists()]
    allp = pd.concat(parts, ignore_index=True).drop_duplicates().sort_values("filing_date")
    allp.to_csv(out_path, index=False)
    return len(allp)


if __name__ == "__main__":
    args = sys.argv[1:]
    redo_low = "--redo-low" in args
    redo_all = "--redo-all" in args
    args = [a for a in args if a not in ("--redo-low", "--redo-all")]
    if len(args) != 3 or "@" not in args[0]:
        sys.exit("Usage: python src/get_quarters.py you@example.com 2022 2025 [--redo-low | --redo-all]")
    email, y0, y1 = args[0], int(args[1]), int(args[2])
    DATA.mkdir(exist_ok=True)
    names = [f"{y}q{q}_form345" for y in range(y0, y1 + 1) for q in (1, 2, 3, 4)]
    if redo_all:
        for name in names:
            print(f"{name}: will redo")
            redo(name)
    elif redo_low:
        for name in names:
            cov = price_coverage(name)
            if cov is not None and cov < 0.8:
                print(f"{name}: Yahoo prices for {cov:.0%} of tickers, will redo")
                redo(name)
    done = []
    for name in names:
        print(name, flush=True)
        if not download(name, email):
            print("  could not download, skipping"); continue
        if not unzip(name):
            print("  unzip did not give the expected files, skipping"); continue
        if not clean(name):
            print("  cleaning failed, skipping"); continue
        done.append(name)
        cov = price_coverage(name)
        print(f"  ok (Yahoo prices for {cov:.0%} of tickers)" if cov is not None else "  ok", flush=True)
    if done:
        out = DATA / f"people_{y0}_{y1}.csv"
        print(f"\n{len(done)} of {len(names)} quarters done. Merged owner-level rows: {merge(done, out)}")
        print("saved", out)
    missing = [n for n in names if n not in done]
    if missing:
        print("not done:", ", ".join(missing))
