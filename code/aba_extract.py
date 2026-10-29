"""Extract J.D. (or LL.B.) degrees awarded by academic year from the ABA PDF.

Source: data/raw/stats_1.authcheckdam.pdf ("Enrollment and Degrees Awarded 1963 - 2010").
Reads the text layer only (pypdf). Writes data/derived/aba_jd_awarded.csv with columns
year (the academic-year label exactly as printed, e.g. "2009 - 2010") and jd_awarded.

PDF note: degrees are "those awarded by approved schools for the academic year ending in
the first year stated". The label is kept as printed; no year is shifted here.

Checks (parsing only, no analysis): every data row has 9 numbers after the year label;
first-year male + female = first-year total and J.D. male + female = J.D. total in every
row; years are consecutive with no gaps or duplicates.

Usage: python -I aba_extract.py
"""
import re
import sys
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import ROOT

PDF = ROOT / "data/raw/stats_1.authcheckdam.pdf"
OUT = ROOT / "data/derived/aba_jd_awarded.csv"
ROW = re.compile(r"^(\d{4} - \d{4}) (.*)$")
COLS = ["schools", "fy_total", "fy_male", "fy_female", "jd_total", "jd_male", "jd_female", "total_enrollment", "jd_awarded"]


def main():
    rows = []
    for page, p in enumerate(PdfReader(PDF).pages, 1):
        for line in (p.extract_text() or "").splitlines():
            m = ROW.match(line.strip())
            if not m:
                continue
            rest = re.sub(r"\(\d\)", " ", m.group(2))  # footnote markers such as "178 (2)"
            nums = [int(x.replace(",", "")) for x in rest.split()]
            assert len(nums) == 9, line
            rows.append({"year": m.group(1), "page": page, **dict(zip(COLS, nums))})
    d = pd.DataFrame(rows)
    assert (d.fy_male + d.fy_female == d.fy_total).all()
    assert (d.jd_male + d.jd_female == d.jd_total).all()
    start = d["year"].str.slice(0, 4).astype(int)
    end = d["year"].str.slice(7, 11).astype(int)
    assert (end == start + 1).all()
    assert not d["year"].duplicated().any()
    assert sorted(start) == list(range(start.min(), start.max() + 1)), "gap in years"
    d = d.assign(_s=start).sort_values("_s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d[["year", "jd_awarded"]].to_csv(OUT, index=False)
    print(f"{len(d)} rows, {d['year'].iloc[0]} to {d['year'].iloc[-1]}; pages {sorted(d.page.unique())}")
    print(d[["year", "page", "jd_awarded"]].to_string(index=False))


if __name__ == "__main__":
    main()
