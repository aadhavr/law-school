"""Build DATA_SOURCES.md from data/raw/manifest.csv. Re-hashes every file on disk to confirm it is unchanged."""
import csv, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
rows = list(csv.DictReader(open(ROOT / "data/raw/manifest.csv")))
derived = [("data/raw/10_chronicle/the-colleges-that-shape-congress.txt",
            "derived: visible text of the saved HTML, made by code/page_text.py")]
out = ["# DATA_SOURCES.md", "",
       "One row per download attempt. Built by `code/write_data_sources.py` from `data/raw/manifest.csv`.",
       "Dates are UTC. Every sha256 below was recomputed from the file on disk when this table was built.", "",
       "| # | Source URL | Date (UTC) | File | Bytes | sha256 | Status | Note |", "|---|---|---|---|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    note = r["note"].replace("|", "/")
    if r["file"]:
        b = (ROOT / r["file"]).read_bytes()
        assert hashlib.sha256(b).hexdigest() == r["sha256"], r["file"]
    out.append(f"| {i} | {r['url']} | {r['date_utc']} | `{r['file']}` | {r['bytes']} | `{r['sha256']}` | {r['status']} | {note} |")
for f, note in derived:
    b = (ROOT / f).read_bytes()
    out.append(f"| d | (from row above for chronicle.com) | 2026-10-24 | `{f}` | {len(b)} | `{hashlib.sha256(b).hexdigest()}` | ok | {note} |")
(ROOT / "DATA_SOURCES.md").write_text("\n".join(out) + "\n")
print(len(rows), "manifest rows;", sum(r["status"] == "ok" for r in rows), "ok")
