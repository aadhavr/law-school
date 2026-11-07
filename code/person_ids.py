"""One ID per person (bioguide), for the linkage-corrected and sensitivity analyses (D15, D16).

The LES panels and CLASS use ICPSR numbers. Voteview gives a party switcher (and some members
who return after a gap) a second ICPSR, so an ICPSR is not always one person. Every ICPSR in
Voteview `HSall_members.csv` has at most one bioguide ID (checked here).
"""
import pandas as pd

from load_data import ROOT

VOTEVIEW = ROOT / "data/raw/02_voteview/HSall_members.csv"


def bioguide_of_icpsr():
    vv = pd.read_csv(VOTEVIEW, usecols=["icpsr", "bioguide_id"]).dropna()
    assert (vv.groupby("icpsr")["bioguide_id"].nunique() <= 1).all()
    return vv.drop_duplicates("icpsr").set_index("icpsr")["bioguide_id"]


def to_person(panel, bio=None):
    """Return a copy with `icpsr` = the old id, `bioguide`, and `id` = an integer person code.

    Every row must have a bioguide ID, and (person, t) must be unique (both checked)."""
    bio = bioguide_of_icpsr() if bio is None else bio
    p = panel.copy()
    p["icpsr"] = p["id"]
    p["bioguide"] = p["id"].map(bio)
    assert p["bioguide"].notna().all(), "panel ICPSR without a bioguide ID"
    assert not p.duplicated(["bioguide", "t"]).any(), "a person has two rows in one t"
    codes = {b: k for k, b in enumerate(sorted(p["bioguide"].unique()))}
    p["id"] = p["bioguide"].map(codes).astype(int)
    return p.sort_values(["id", "t"]).reset_index(drop=True)


def multi_icpsr(panel, bio=None):
    """Persons with more than one ICPSR in the panel: one row per person."""
    bio = bioguide_of_icpsr() if bio is None else bio
    p = panel.assign(bioguide=panel["id"].map(bio))
    g = p.groupby("bioguide").agg(icpsrs=("id", lambda x: ";".join(str(i) for i in sorted(set(x)))),
                                  n_icpsr=("id", "nunique"), member_terms=("t", "size"))
    return g[g["n_icpsr"] > 1].reset_index()
