"""Test B policy filter, coder 1 (Claude Code), PREREG.md Amendment 2. No adoption information used.

Rule (Amendment 2): the statement proposes or evaluates a specific US federal measure that
Congress, an agency or the president could enact, change or repeal, AND the favored direction is
clear. Excluded: claims about the past or about causes, forecasts, theory, other countries, and
state or local measures. Coder 1 reads "favored direction is clear" as: the statement itself
judges the measure (better off, more efficient, adverse, net costs), not only one effect of it.

Repeated policies are merged; the earliest statement is kept (ties: the first in pool order).

Reads data/derived/igm/test_b_pool.csv; writes data/derived/igm/test_b_policy_filter.csv.
Usage: python -I testB_policy_filter.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/derived/igm/test_b_pool.csv"
DST = ROOT / "data/derived/igm/test_b_policy_filter.csv"

PAST = "no: claim about the past or about causes"
THEORY = "no: theory or general claim, not a specific US federal measure"
OTHER = "no: other country"
STATE = "no: state or local measure"
FORECAST = "no: forecast or conditional prediction, not a measure"
NODIR = "no: names a federal measure but states only an effect of it, no favored direction"

# pool_no: (policy_flag, one line citing the rule, policy group for yes)
CODES = {
    1: ("no", NODIR + " (top-rate increase raises revenue)", ""),
    2: ("no", OTHER + " (China's exchange-rate policy)", ""),
    3: ("no", THEORY + " (stock-price predictability)", ""),
    4: ("yes", "yes: specific federal tax change (end non-investment personal interest deductions, budget- and distribution-neutral rate cuts); favored: more efficient", "end personal interest deduction"),
    5: ("yes", "yes: specific federal tax change (limit business interest deductibility, revenue-neutral rate cuts); favored: more efficient", "limit business interest deduction"),
    6: ("no", OTHER + " (Italy)", ""),
    7: ("no", THEORY + " (prohibition raises drug prices)", ""),
    8: ("yes", "yes: federal carbon tax evaluated against CAFE-type rules; favored: carbon tax (less expensive)", "federal carbon price"),
    9: ("no", STATE + " (general case for congestion charges; city tolls are state or local)", ""),
    10: ("no", THEORY + " (gold price)", ""),
    11: ("no", PAST + " (inequality)", ""),
    12: ("no", PAST + " (ARRA effect on 2010 unemployment)", ""),
    13: ("no", THEORY + " (short-sale bans in general)", ""),
    14: ("no", STATE + " (scope-of-practice licensing)", ""),
    15: ("no", PAST + " (2008 bank bailouts)", ""),
    16: ("no", THEORY + " (freer trade)", ""),
    17: ("no", PAST + " (effect of NAFTA so far)", ""),
    18: ("no", PAST + " (causes of gasoline prices)", ""),
    19: ("no", STATE + " (ticket-resale laws)", ""),
    20: ("no", OTHER + " (France)", ""),
    21: ("no", PAST + " (causes of Cuba's growth)", ""),
    22: ("no", FORECAST + " (2013 GDP under the fiscal cliff)", ""),
    23: ("no", THEORY + " (trade with China in general)", ""),
    24: ("no", THEORY + " (trade with China in general)", ""),
    25: ("no", OTHER + " (eurozone)", ""),
    26: ("no", FORECAST + " (what long-run sustainability requires; no specific measure)", ""),
    27: ("no", NODIR + " (a la carte cable rule: 'not necessarily better off')", ""),
    28: ("no", STATE + " (state sales taxes on out-of-state sellers)", ""),
    29: ("no", PAST + " (money market funds in 2008)", ""),
    30: ("yes", "yes: specific SEC rule (floating NAV for money market funds); favored: taxpayers better protected", "money market funds: floating NAV"),
    31: ("yes", "yes: specific SEC rule (capital buffer and redemption holdback for money market funds); favored: taxpayers better protected", "money market funds: capital buffer and holdback"),
    32: ("no", PAST + " (default rates at for-profit colleges)", ""),
    33: ("yes", "yes: specific federal rule (tie student-loan eligibility to graduation and employment outcomes); favored: better protects taxpayers", "student-loan eligibility tied to outcomes"),
    34: ("no", NODIR + " (sugar trade barriers: gains to producers and costs to consumers, no net judgment)", ""),
    35: ("yes", "yes: existing federal measures (ethanol mandate and ethanol import protection) evaluated; favored: against (raise food prices, little CO2 cut)", "repeal ethanol mandate and protection"),
    36: ("yes", "yes: federal carbon tax or permit market evaluated against the corn-ethanol mandate; favored: carbon price", "federal carbon price"),
    37: ("no", STATE + " (state and local pension accounting)", ""),
    38: ("no", STATE + " (state budgets; forecast)", ""),
    39: ("no", THEORY + " (drawback of a capital/labor rate gap)", ""),
    40: ("no", THEORY + " (why economists disagree)", ""),
    41: ("no", THEORY + " (campaign job claims)", ""),
    42: ("no", NODIR + " (Medicare premium support: names a risk, no net judgment)", ""),
    43: ("yes", "yes: federal tax measure (favor R&D in the tax code); favored: raises average well-being", "R&D tax credit"),
    44: ("no", THEORY + " (benefit of very large banks; no measure)", ""),
    45: ("no", PAST + " (auto bailout effect on 2010 unemployment)", ""),
    46: ("no", THEORY + " (a class of deficit plans, not a specific measure)", ""),
    47: ("yes", "yes: federal carbon tax ($20/ton rising 4%/yr) evaluated against higher labor taxes; favored: carbon tax", "federal carbon price"),
    48: ("yes", "yes: federal measure (the separate debt ceiling), which Congress could repeal; favored: against (uncertainty, worse outcomes)", "abolish the debt ceiling"),
    49: ("yes", "yes: federal immigration law (admit more highly educated immigrants); favored: average citizen better off", "more high-skilled immigration"),
    50: ("no", THEORY + " (debt feedback loops)", ""),
    51: ("no", THEORY + " (bitcoin)", ""),
    52: ("yes", "yes: federal spending measure (more on roads, rail, bridges, airports); favored: raises average incomes", "more federal infrastructure spending"),
    53: ("yes", "yes: federal measure (restrict LNG exports, DOE approvals); favored: against restriction (adverse effects)", "do not restrict LNG exports"),
    54: ("no", PAST + " (end of US slavery)", ""),
    55: ("no", THEORY + " (employer plan design; no government measure named)", ""),
    56: ("no", FORECAST + " (harm from a US debt default)", ""),
    57: ("no", THEORY + " (index funds)", ""),
    58: ("no", THEORY + " (surge pricing by private firms; no federal measure)", ""),
    59: ("no", PAST + " (Fed policy 2008-09)", ""),
    60: ("no", PAST + " (automation and employment)", ""),
    61: ("no", THEORY + " (NCAA rules; private body)", ""),
    62: ("no", THEORY + " (discrimination)", ""),
    63: ("no", THEORY + " (liquidity transformation)", ""),
    64: ("no", PAST + " (ARRA effect on 2010 unemployment; repeat vote)", ""),
    65: ("no", STATE + " (state and local pension accounting; repeat vote)", ""),
    66: ("no", STATE + " (state budgets; repeat vote)", ""),
    67: ("yes", "yes: federal spending measure (more on roads, rail, bridges, airports); favored: raises average incomes (repeat vote)", "more federal infrastructure spending"),
    68: ("no", STATE + " (taxi and ride-hailing rules)", ""),
    69: ("no", NODIR + " (fast-track authority makes deals more likely; no net judgment)", ""),
    70: ("no", PAST + " (past trade deals)", ""),
    71: ("no", THEORY + " (convention spending)", ""),
    72: ("no", FORECAST + " (oil prices and GDP)", ""),
    73: ("no", THEORY + " (textbook prices)", ""),
    74: ("no", THEORY + " (textbook prices)", ""),
    75: ("no", THEORY + " (behavioral response to tax rates)", ""),
    76: ("no", THEORY + " (vaccination externality)", ""),
    77: ("no", STATE + " (vaccine mandates are set by states)", ""),
    78: ("no", STATE + " (California water pricing)", ""),
    79: ("no", THEORY + " (Nash equilibrium)", ""),
    80: ("no", THEORY + " (teacher value-added)", ""),
    81: ("no", OTHER + " (China)", ""),
    82: ("no", OTHER + " (UK and EU)", ""),
    83: ("no", THEORY + " (voting systems)", ""),
    84: ("no", THEORY + " (voting systems)", ""),
    85: ("yes", "yes: federal budget measure (BLS funding); favored: keep it (benefits exceed cost)", "maintain BLS funding"),
    86: ("yes", "yes: federal budget measure (cuts in BLS spending); favored: against cuts (net social costs)", "maintain BLS funding"),
    87: ("yes", "yes: specific federal measure (ACA 'Cadillac tax'); favored: let it take effect (reduces distortions)", "Cadillac tax takes effect"),
    88: ("no", NODIR + " (wage effect of high-skilled immigration)", ""),
    89: ("yes", "yes: federal immigration law (let employers hire many more advanced-degree immigrants); favored: raises per capita income", "more high-skilled immigration"),
    90: ("no", FORECAST + " (what long-run sustainability requires; no specific measure)", ""),
}


def main():
    rows = list(csv.DictReader(open(SRC, newline="")))
    assert len(rows) == 90 and set(CODES) == {int(r["pool_no"]) for r in rows}
    first = {}
    out = []
    for r in sorted(rows, key=lambda r: (r["date"], int(r["pool_no"]))):
        flag, note, group = CODES[int(r["pool_no"])]
        assert flag in ("yes", "no") and note.startswith(flag) and (group != "") == (flag == "yes")
        if flag == "yes" and group not in first:
            first[group] = r["pool_no"]
        merged = flag == "yes" and first[group] != r["pool_no"]
        out.append({"pool_no": r["pool_no"], "date": r["date"], "id": r["id"], "part": r["part"],
                    "weighted_agree": r["weighted_agree"], "statement": r["statement"],
                    "policy_flag": flag, "rule_note": note, "policy_group": group,
                    "kept_as_policy": "yes" if flag == "yes" and not merged else "no",
                    "merged_into_pool_no": first[group] if merged else ""})
    out.sort(key=lambda r: int(r["pool_no"]))
    with open(DST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    n_yes = sum(r["policy_flag"] == "yes" for r in out)
    n_kept = sum(r["kept_as_policy"] == "yes" for r in out)
    print(f"pool {len(out)}; policy = yes {n_yes}; after merging repeats {n_kept}")
    for r in out:
        if r["kept_as_policy"] == "yes":
            m = [x["pool_no"] for x in out if x["merged_into_pool_no"] == r["pool_no"]]
            print(r["pool_no"], r["date"], r["policy_group"], "| merged:", ",".join(m) or "-")


if __name__ == "__main__":
    main()
