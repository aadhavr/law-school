"""Test D, step 1: parse govinfo BILLSTATUS (Congresses 108–117, hr and hjres).

PREREG.md Amendments 1 and 1a. No LES data is read here.

Reads the 20 ZIPs in data/raw/15_govinfo/billstatus/ without extracting them to disk.
The files are untrusted: any XML with a DOCTYPE or ENTITY declaration is refused and
counted, and nothing inside the files is executed.

Writes:
  data/derived/billstatus_sponsors.csv     one row per bill and sponsor
  data/derived/billstatus_cosponsors.csv   one row per bill and cosponsor (withdrawn flag kept)
  output/testD/billstatus_parse.csv        files, bills parsed, refusals per Congress and type
  output/testD/billstatus_match.csv        share of sponsor/cosponsor entries matching a
                                           Voteview bioguide ID, per Congress

Usage: python -I testD_billstatus.py
"""
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import ROOT

SRC = ROOT / "data/raw/15_govinfo/billstatus"
VOTEVIEW = ROOT / "data/raw/02_voteview/HSall_members.csv"
DERIVED = ROOT / "data/derived"
OUT = ROOT / "output/testD"
CONGRESSES = range(108, 118)
TYPES = ["hr", "hjres"]


def text(el, tag):
    x = el.find(tag)
    return None if x is None or x.text is None else x.text.strip()


def parse_zip(path, congress, btype):
    spons, cospons = [], []
    stats = {"congress": congress, "type": btype, "n_files": 0, "n_bills": 0, "n_refused": 0,
             "n_wrong_congress_or_type": 0, "n_no_sponsor": 0}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".xml"):
                continue
            stats["n_files"] += 1
            raw = z.read(name)
            if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
                stats["n_refused"] += 1
                continue
            bill = ET.fromstring(raw).find("bill")
            # 13 files use the older tag names billType / billNumber.
            cong = text(bill, "congress")
            typ = text(bill, "type") or text(bill, "billType")
            num = text(bill, "number") or text(bill, "billNumber")
            if cong != str(congress) or (typ or "").lower() != btype:
                stats["n_wrong_congress_or_type"] += 1
                continue
            stats["n_bills"] += 1
            key = {"congress": congress, "type": btype, "number": int(num)}
            s_items = [] if bill.find("sponsors") is None else bill.find("sponsors").findall("item")
            if not s_items:
                stats["n_no_sponsor"] += 1
            for it in s_items:
                spons.append({**key, "sponsor": text(it, "bioguideId")})
            c_el = bill.find("cosponsors")
            for it in ([] if c_el is None else c_el.findall("item")):
                cospons.append({**key, "cosponsor": text(it, "bioguideId"),
                                "withdrawn": int(text(it, "sponsorshipWithdrawnDate") is not None)})
    return spons, cospons, stats


def main():
    DERIVED.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    spons, cospons, stats = [], [], []
    for c in CONGRESSES:
        for t in TYPES:
            s, co, st = parse_zip(SRC / f"BILLSTATUS-{c}-{t}.zip", c, t)
            spons += s
            cospons += co
            st["n_cosponsorships"] = len(co)
            st["n_withdrawn"] = sum(x["withdrawn"] for x in co)
            stats.append(st)
            print(c, t, st, flush=True)
    sp = pd.DataFrame(spons)
    co = pd.DataFrame(cospons)
    sp.to_csv(DERIVED / "billstatus_sponsors.csv", index=False)
    co.to_csv(DERIVED / "billstatus_cosponsors.csv", index=False)
    pd.DataFrame(stats).to_csv(OUT / "billstatus_parse.csv", index=False)

    # Match to Voteview bioguide IDs: (1) any Voteview record; (2) a House member in that Congress.
    vv = pd.read_csv(VOTEVIEW, usecols=["congress", "chamber", "bioguide_id"])
    any_ids = set(vv["bioguide_id"].dropna())
    house = vv[vv["chamber"] == "House"].dropna(subset=["bioguide_id"])
    house_ids = {c: set(g["bioguide_id"]) for c, g in house.groupby("congress")}
    rows = []
    for role, df, col in [("sponsor", sp, "sponsor"), ("cosponsor_not_withdrawn", co[co["withdrawn"] == 0], "cosponsor"),
                          ("cosponsor_all", co, "cosponsor")]:
        for c in CONGRESSES:
            ids = df.loc[df["congress"] == c, col]
            u = pd.Series(ids.dropna().unique())
            rows.append({"congress": c, "role": role, "n_entries": len(ids), "n_missing_id": int(ids.isna().sum()),
                         "share_entries_any_voteview": ids.isin(any_ids).mean(),
                         "share_entries_house_same_congress": ids.isin(house_ids[c]).mean(),
                         "n_distinct_ids": len(u),
                         "share_distinct_any_voteview": u.isin(any_ids).mean(),
                         "share_distinct_house_same_congress": u.isin(house_ids[c]).mean(),
                         "unmatched_house_same_congress": ";".join(sorted(set(u) - house_ids[c]))})
        ids = df[col]
        hs = pd.concat([df.loc[df["congress"] == c, col].isin(house_ids[c]) for c in CONGRESSES])
        rows.append({"congress": "all", "role": role, "n_entries": len(ids), "n_missing_id": int(ids.isna().sum()),
                     "share_entries_any_voteview": ids.isin(any_ids).mean(),
                     "share_entries_house_same_congress": hs.mean()})
    pd.DataFrame(rows).to_csv(OUT / "billstatus_match.csv", index=False)


if __name__ == "__main__":
    main()
