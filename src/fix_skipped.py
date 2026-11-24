"""Second try for filings listed in data/live/skipped.txt, using their other SEC addresses.

Run from the project folder:   python src/fix_skipped.py you@example.com
Any filing that works now is added to its day file; the rest stay in skipped.txt.
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, "src")
from live_form4 import COLUMNS, OUT, day_filings, get_filing, parse_filing   # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 2 or "@" not in sys.argv[1]:
        sys.exit("Usage: python src/fix_skipped.py you@example.com")
    sess = requests.Session()
    sess.headers["User-Agent"] = f"insider-radar student project {sys.argv[1]}"
    lines = [l.split("\t") for l in (OUT / "skipped.txt").read_text().splitlines() if l.strip()]
    left = []
    for day_s, status, url in lines:
        day = datetime.strptime(day_s, "%Y-%m-%d").date()
        acc = url.split("/")[-1]
        files, _ = day_filings(sess, day)
        paths = (files or {}).get(acc, [url.replace("https://www.sec.gov/Archives/", "")])
        print(f"{day_s} {acc}: {len(paths)} address(es) listed")
        r, st = get_filing(sess, paths)
        if r is None:
            print(f"   still not available (status {st})")
            left.append("\t".join([day_s, str(st), url]))
            continue
        rows, state = parse_filing(r.text)
        print(f"   downloaded; {len(rows)} purchase row(s), parse status: {state}")
        f = OUT / f"purchases_{day:%Y%m%d}.csv"
        old = pd.read_csv(f, dtype={"ISSUERCIK": str, "RPTOWNERCIK": str})
        new = pd.concat([old, pd.DataFrame(rows, columns=COLUMNS)])
        new = new.drop_duplicates(["ACCESSION_NUMBER", "NONDERIV_TRANS_SK", "RPTOWNERCIK"])
        new.to_csv(f, index=False)
    (OUT / "skipped.txt").write_text("".join(l + "\n" for l in left))
    print("filings still skipped:", len(left))
