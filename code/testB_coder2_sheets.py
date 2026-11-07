"""Test B coder-2 sheets (PREREG.md Amendments 2, 2a). No coder-1 label is written to the sheets.

One generator, numpy default_rng(20261029), used in this order:
  1. choose 6 of the statements coder 1 coded "no" that are not close calls (sorted by pool_no);
  2. shuffle sheet 1 (14 policies + 10 close calls + those 6);
  3. choose 10 of the 14 policies (sorted by pool_no) for sheet 2;
  4. shuffle sheet 2.

Writes output/coder2/sheet1_filter.csv, output/coder2/sheet2_adoption.csv, output/coder2/README.md,
and output/coder2_key/row_key.csv (row id → pool_no only; kept outside output/coder2/).
Usage: python -I testB_coder2_sheets.py
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from testB_policy_filter import CODES

ROOT = Path(__file__).resolve().parent.parent
POOL = ROOT / "data/derived/igm/test_b_pool.csv"
FILT = ROOT / "data/derived/igm/test_b_policy_filter.csv"
OUT = ROOT / "output/coder2"
KEY = ROOT / "output/coder2_key"
SEED = 20261029
CLOSE_CALLS = [1, 13, 27, 28, 34, 42, 55, 69, 77, 88]  # Amendment 2a
FILTER_RULE = ("The statement proposes or evaluates a specific US federal measure that Congress, an agency, "
               "or the president could enact, change, or repeal, and the favored direction is clear. Exclude "
               "claims about the past or causes, forecasts, theory, other countries, and state or local measures.")
ADOPTED_RULE = ("Adopted: a federal law, rule, regulation, or executive measure was in force at any time within "
                "10 years after the statement date, in substantially the form the statement describes. Each code "
                "needs a source URL and a date. If it is unclear, code \"unclear\".")
CAUSES = "knowledge gap; blocked by interests or veto players; no actor with the skill to act"


def main():
    pool = {int(r["pool_no"]): r for r in csv.DictReader(open(POOL, newline=""))}
    filt = {int(r["pool_no"]): r for r in csv.DictReader(open(FILT, newline=""))}
    assert len(pool) == 90 and len(filt) == 90
    policies = sorted(p for p, r in filt.items() if r["kept_as_policy"] == "yes")
    assert len(policies) == 14 and all(CODES[c][0] == "no" for c in CLOSE_CALLS)
    other_no = sorted(p for p in pool if CODES[p][0] == "no" and p not in CLOSE_CALLS)
    assert len(other_no) == 61
    rng = np.random.default_rng(SEED)
    six = sorted(int(x) for x in rng.choice(other_no, 6, replace=False))
    s1 = policies + CLOSE_CALLS + six
    s1 = [s1[i] for i in rng.permutation(len(s1))]
    ten = sorted(int(x) for x in rng.choice(policies, 10, replace=False))
    s2 = [ten[i] for i in rng.permutation(len(ten))]

    OUT.mkdir(parents=True, exist_ok=True)
    KEY.mkdir(parents=True, exist_ok=True)
    (OUT / "returned").mkdir(exist_ok=True)
    key = []
    with open(OUT / "sheet1_filter.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row_id", "date", "statement", "igm_page", "filter_rule", "policy_flag"])
        for k, p in enumerate(s1, 1):
            r = pool[p]
            rid = f"F{k:02d}"
            w.writerow([rid, r["date"], r["statement"], f"https://www.igmchicago.org/surveys/{r['id']}/", FILTER_RULE, ""])
            key.append({"row_id": rid, "sheet": "sheet1_filter", "pool_no": p})
    with open(OUT / "sheet2_adoption.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row_id", "date", "statement", "adopted_any_time", "adopted_still_in_force", "source_url",
                    "source_date", "cause_code"])
        for k, p in enumerate(s2, 1):
            r = pool[p]
            rid = f"A{k:02d}"
            w.writerow([rid, r["date"], r["statement"], "", "", "", "", ""])
            key.append({"row_id": rid, "sheet": "sheet2_adoption", "pool_no": p})
    with open(KEY / "row_key.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["row_id", "sheet", "pool_no"])
        w.writeheader()
        w.writerows(key)
    (OUT / "README.md").write_text(f"""# Coder 2 sheets (Test B, PREREG.md Amendments 2 and 2a)

Code each row on your own, without looking at coder 1's codes, the code in `code/testB_*.py`, or
`ANALYSIS_LOG.md` section F. **Finish sheet 1 before you open sheet 2.** Save the completed files,
with the same names and columns, in `output/coder2/returned/`.

## Sheet 1: `sheet1_filter.csv` ({len(s1)} rows)
Fill `policy_flag` with `yes` or `no`, using the rule (also in each row):

> {FILTER_RULE}

## Sheet 2: `sheet2_adoption.csv` ({len(s2)} rows)
Judge adoption as of 2026-11-07.

- `adopted_any_time`: `yes`, `no` or `unclear`. {ADOPTED_RULE}
- `adopted_still_in_force`: `yes`, `no` or `unclear`: whether that measure is still in force on 2026-11-07.
- `source_url` and `source_date`: the source for your code, and its date (YYYY-MM-DD).
- `cause_code` (only if `adopted_any_time` is `no`): one of: {CAUSES}.
""")
    print("sheet 1:", len(s1), "rows; sheet 2:", len(s2), "rows")


if __name__ == "__main__":
    main()
