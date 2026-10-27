"""Load the three CEL files into one harmonized member-term panel per body.

Columns returned: body, id, t, les, seniority, party (D/R/Other), majority, chair, chamber.
t is an integer that orders terms in time (Congress number; state term start year).
Rows with a missing member ID or a missing covariate are dropped (complete cases).
"""
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
HOUSE = ROOT / "CELHouse93to118-REVISED-06.26.2025.xlsx"
SENATE = ROOT / "CELSenate93to118.xls"
STATES = ROOT / "sles_all_50_states_202609.csv"

COLS = ["body", "id", "t", "les", "seniority", "party", "majority", "chair", "chamber"]


def _party_from_code(code):
    return np.select([code == 100, code == 200], ["D", "R"], "Other")


def load_house():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        d = pd.read_excel(HOUSE)
    out = pd.DataFrame({
        "body": "House",
        "id": d["ICPSR number, according to Poole and Rosenthal"],
        "t": d["Congress number"],
        "les": d["LES 1.0"],
        "seniority": d["Seniority, number of terms served counting current"],
        "party": _party_from_code(d["100=Dem, 200=Rep, Other"]),
        "majority": d["1 = majority party member"],
        "chair": d["1 = committee chair, according to Almanac of American Politics"],
        "chamber": "lower",
    })
    return out


def load_senate():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        d = pd.read_excel(SENATE)
    out = pd.DataFrame({
        "body": "Senate",
        "id": d["icpsr number"],
        "t": d["congress number"],
        "les": d["LES Classic, not including incorporation in other legislative vehicles"],
        "seniority": d["seniority"],
        "party": _party_from_code(d["100=Dem, 200=Rep, Others"]),
        "majority": d["1 if senator is in majority party"],
        "chair": d["1 if senator is a committee chair"],
        "chamber": "upper",
    })
    return out


def load_states():
    d = pd.read_csv(STATES, low_memory=False)
    party = np.select([d["party"] == "D", d["party"] == "R"], ["D", "R"], "Other")
    out = pd.DataFrame({
        "body": "States",
        "id": d["sles_id"],
        "t": d["term"].str.slice(0, 4).astype(int),
        "les": d["SLES"],
        "seniority": d["seniority"],
        "party": party,
        "majority": d["in_majority"],
        # "." has no documented meaning without the codebook; treated as missing.
        "chair": pd.to_numeric(d["comm_chair"], errors="coerce"),
        "chamber": d["chamber"],
        "state": d["state"],
    })
    return out


def clean(df):
    n0 = len(df)
    df = df.dropna(subset=["id", "t", "les", "seniority", "majority", "chair"]).copy()
    df["id"] = df["id"].astype(int)
    df["t"] = df["t"].astype(int)
    for c in ["seniority", "majority", "chair"]:
        df[c] = df[c].astype(float)
    df.attrs["dropped"] = n0 - len(df)
    return df.reset_index(drop=True)


def load_all():
    return {"House": clean(load_house()), "Senate": clean(load_senate()), "States": clean(load_states())}


if __name__ == "__main__":
    for k, v in load_all().items():
        print(k, len(v), "rows;", v["id"].nunique(), "members; dropped", v.attrs["dropped"],
              "; t", v.t.min(), "-", v.t.max(), "; parties", v.party.value_counts().to_dict())
