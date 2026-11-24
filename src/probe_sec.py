"""One-day test of the SEC daily index, before we build the live updater.

Run from the project folder (your email is sent to the SEC, as they ask):
    python src/probe_sec.py you@example.com 2026-11-20

It downloads that day's Form 4 list, looks at up to 40 filings, and saves what it finds in
data/probe/ so that we can check the real file layout. It makes about 45 requests, slowly.
"""
import re
import sys
import time
from pathlib import Path

import requests

OUT = Path("data/probe")
BASE = "https://www.sec.gov/Archives/"
PAUSE = 0.25            # 4 requests a second, well under the SEC limit of 10


def get(url, headers):
    r = requests.get(url, headers=headers, timeout=60)
    time.sleep(PAUSE)
    return r


def quarter(month):
    return (month - 1) // 3 + 1


if __name__ == "__main__":
    if len(sys.argv) != 3 or "@" not in sys.argv[1]:
        sys.exit("Usage: python src/probe_sec.py you@example.com 2026-11-20")
    email, day = sys.argv[1], sys.argv[2]
    y, m, d = day.split("-")
    headers = {"User-Agent": f"insider-radar student project {email}"}
    OUT.mkdir(parents=True, exist_ok=True)

    idx_url = f"{BASE}edgar/daily-index/{y}/QTR{quarter(int(m))}/form.{y}{m}{d}.idx"
    r = get(idx_url, headers)
    print("index:", idx_url, "->", r.status_code, f"({len(r.content)} bytes)")
    if r.status_code != 200:
        print("The index file was not found at that address. Tell Claude this line.")
        sys.exit(1)
    text = r.text
    (OUT / f"form_{y}{m}{d}.idx").write_text(text)
    lines = text.splitlines()
    print("lines in file:", len(lines))
    print("first 12 lines:")
    for ln in lines[:12]:
        print("  |", ln[:150])

    # Form 4 entries: form type is the first word on the line, file name is the last
    entries = {}
    for ln in lines:
        parts = ln.split()
        if len(parts) >= 5 and parts[0] == "4" and parts[-1].startswith("edgar/data/"):
            entries.setdefault(parts[-1], ln)
    print("distinct Form 4 filings that day:", len(entries))
    print("lines starting with 4/A:", sum(1 for ln in lines if ln.split()[:1] == ["4/A"]))

    saved_p, saved_other = 0, 0
    for i, fname in enumerate(list(entries)[:40]):
        rr = get(BASE + fname, headers)
        if rr.status_code != 200:
            print("  filing", fname, "->", rr.status_code)
            continue
        body = rr.text
        has_p = "<transactionCode>P</transactionCode>" in body
        keep = (has_p and saved_p < 2) or (not has_p and saved_other < 3)
        if keep:
            (OUT / f"filing_{'P' if has_p else 'other'}_{i}.txt").write_text(body)
            saved_p += has_p
            saved_other += (not has_p)
    print(f"saved {saved_p} filings with a purchase and {saved_other} others to {OUT}")
    print("done")
