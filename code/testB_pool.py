"""Test B pool (PREREG.md Amendment 2): weighted agree ≥ 0.80 and statement date ≤ 2016-11-07.

Reads data/derived/igm/igm_all_questions.csv (code/igm_build.py). Writes
data/derived/igm/test_b_pool.csv, one row per statement (question part), sorted by date, id, part.
No adoption information is used.

Usage: python -I testB_pool.py
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/derived/igm/igm_all_questions.csv"
DST = ROOT / "data/derived/igm/test_b_pool.csv"
CONSENSUS = 0.80
WINDOW_END = "2016-11-07"
EXPECTED = 90


def main():
    rows = list(csv.DictReader(open(SRC, newline="")))
    pool = [r for r in rows if float(r["weighted_agree"]) >= CONSENSUS and r["date"] <= WINDOW_END]
    pool.sort(key=lambda r: (r["date"], r["id"], r["part"]))
    for k, r in enumerate(pool, 1):
        r["pool_no"] = k
    if len(pool) != EXPECTED:
        sys.exit(f"STOP: pool has {len(pool)} rows, expected {EXPECTED}")
    cols = ["pool_no"] + list(rows[0].keys())
    with open(DST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(pool)
    print(f"{len(pool)} statements; {len({r['id'] for r in pool})} questions; "
          f"dates {pool[0]['date']} to {pool[-1]['date']}")


if __name__ == "__main__":
    main()
