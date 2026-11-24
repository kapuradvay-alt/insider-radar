"""Show how far the live download has got.   Run:  python src/live_status.py 2026-09-28 2026-11-20"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python src/live_status.py 2026-09-28 2026-11-20")
    d = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    last = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
    done, missing = 0, []
    while d <= last:
        if d.weekday() < 5:
            if (Path("data/live") / f"purchases_{d:%Y%m%d}.csv").exists():
                done += 1
            else:
                missing.append(str(d))
        d += timedelta(days=1)
    print(f"weekdays saved: {done} | still missing: {len(missing)}")
    for m in missing:
        print("   ", m)
    print("ALL DAYS DONE" if not missing else "Not finished: run the download command again.")
